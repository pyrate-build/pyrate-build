#!/usr/bin/env python
#-#  Copyright 2016 Fred Stober
#-#
#-#  Licensed under the Apache License, Version 2.0 (the "License");
#-#  you may not use this file except in compliance with the License.
#-#  You may obtain a copy of the License at
#-#
#-#      http://www.apache.org/licenses/LICENSE-2.0
#-#
#-#  Unless required by applicable law or agreed to in writing, software
#-#  distributed under the License is distributed on an "AS IS" BASIS,
#-#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#-#  See the License for the specific language governing permissions and
#-#  limitations under the License.

pyrate_version = (0, 1, 4)

import os, sys
try:
	import hashlib
	md5 = hashlib.md5
except ImportError:
	import md5
	md5 = md5.md5

class ProcessError(Exception):
	pass

def run_process(args):
	import subprocess
	try:
		p = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		ret = p.wait()
	except Exception:
		raise ProcessError('Unable to run process %s' % repr(args))
	if ret != 0:
		raise ProcessError('Process %r exit code %d' % (args, ret))
	return p.communicate()


def nice_repr(ref, keylen, delim = '   '):
	def indent_repr(value, prefix = delim):
		return str.join('\n', map(lambda x: prefix + x, repr(value).splitlines()))
	result = []
	for key in sorted(ref.__dict__, reverse = True):
		value = ref.__dict__[key]
		if isinstance(value, list) and value:
			result.append(delim + '%s = [\n' % key.ljust(keylen) + str.join(',\n', map(lambda entry: '%s' % indent_repr(entry, 2 * delim), value)) + ']')
		else:
			result.append(delim + '%s = %s' % (key.ljust(keylen), indent_repr(value, delim).lstrip()))
	return '%s(\n%s)' % (ref.__class__.__name__, str.join('\n', result))


class VersionError(Exception):
	pass


class VersionComparison(object):
	def __init__(self, value = None, op = None, cmpfun = None):
		if value:
			value = tuple(str(value).split('.'))
		(self.value, self.op, self.cmpfun) = (value, op, cmpfun)
	def __str__(self):
		return repr(self.__dict__)
	def check(self, other):
		other = tuple(str(other).split('.'))
		value = tuple(self.value)
		if len(other) > len(value):
			other = tuple(other[:len(value)])
		elif len(other) < len(value):
			other = tuple(list(other) + [0]*(len(value) - len(other)))
		return self.cmpfun(other, value)
	def __lt__(self, other):
		return VersionComparison(other, '<', tuple.__lt__)
	def __le__(self, other):
		return VersionComparison(other, '<=', tuple.__le__)
	def __eq__(self, other):
		return VersionComparison(other, '==', tuple.__eq__)
	def __ne__(self, other):
		return VersionComparison(other, '!=', tuple.__ne__)
	def __gt__(self, other):
		return VersionComparison(other, '>', tuple.__gt__)
	def __ge__(self, other):
		return VersionComparison(other, '>=', tuple.__ge__)


def match(value, dn = '.'):
	import fnmatch
	result = []
	for fn in os.listdir(dn):
		accept = False
		for token in value.split():
			negate = token.startswith('-')
			if negate:
				token = token[1:]
			if not fnmatch.fnmatch(fn, token):
				continue
			accept = not negate
		if accept:
			result.append(fn)
	return result


class Delayed(object):
	def __init__(self, cls, *args, **kwargs):
		(self._cls, self._args, self._kwargs) = (cls, args, kwargs)
		self._delayed_instance = None
	def __getattribute__(self, name):
		if name in ['_delayed_instance', '_cls', '_args', '_kwargs']:
			return object.__getattribute__(self, name)
		if not self._delayed_instance:
			self._delayed_instance = self._cls(*self._args, **self._kwargs)
		return self._delayed_instance.__getattribute__(name)


class NinjaBuildFileWriter(object):
	def __init__(self, fn = 'build.ninja'):
		self._fp = open(fn, 'w')
	def set_var(self, key, value):
		self._fp.write('%s = %s\n' % (key, value.strip()))
	def set_default(self, target_list):
		self._fp.write('default %s\n' % str.join(' ', map(str, target_list)))
	def write_rule(self, rule):
		for key, value in sorted(rule.defaults.items()):
			self.set_var(key, value)
		self._fp.write('rule %s\n' % rule.name)
		self._fp.write('  command = %s\n' % rule.cmd)
		self._fp.write('  description = %s\n' % rule.desc)
		for key_value in rule.params:
			self._fp.write('  %s = %s\n' % key_value)
		self._fp.write('\n')
	def write_target(self, target):
		inputs = str.join(' ', target.get_build_inputs())
		self._fp.write('build %s: %s %s' % (target.name, target.build_rule.name, inputs))
		if target.get_build_deps():
			self._fp.write(' | %s' % str.join(' ', map(lambda t: t.name, target.get_build_deps())))
		self._fp.write('\n')
		for key_value in target.get_build_flags().items():
			self._fp.write('  %s = %s\n' % key_value)


class SelfReference(object):
	def __init__(self, ref = None):
		self._ref = ref

	def __repr__(self):
		return 'self'

	def replace_ref(self, value):
		if isinstance(value, SelfReference):
			return self._ref
		return value


class Rule(object):
	def __init__(self, name, cmd, desc, defaults, **kwargs):
		(self.name, self.cmd, self.desc, self.defaults) = (name, cmd, desc, defaults)
		self.params = kwargs.items()

	def __repr__(self):
		return nice_repr(self, 8)


class BuildSource(object):
	def __init__(self, on_use_inputs = {}, on_use_deps = {}, on_use_flags = {}):
		(self.on_use_inputs, self.on_use_deps, self.on_use_flags) = \
			(self._resolve_self(on_use_inputs), self._resolve_self(on_use_deps), dict(on_use_flags))

	def _resolve_self(self, on_use_dict):
		result = {}
		for key, value_list in on_use_dict.items():
			for value in value_list:
				if isinstance(value, SelfReference):
					value = self
				result.setdefault(key, []).append(value)
		return result

	def __repr__(self):
		return nice_repr(self, 14)


class BuildTarget(BuildSource):
	def __init__(self, name, build_rule, build_src, on_use_inputs = {}, on_use_deps = {}, on_use_flags = {}):
		BuildSource.__init__(self, on_use_inputs, on_use_deps, on_use_flags)
		(self.name, self.build_rule, self.build_src) = (name, build_rule, build_src)
		self._drop_opt = False

	def get_key(self):
		build_deps = tuple(map(lambda t: t.name, self.get_build_deps()))
		build_flags = tuple(sorted(self.get_build_flags().items()))
		return (self.build_rule.name, tuple(self.get_build_inputs()), build_deps, build_flags)

	def _get_build_x(self, src_getter, default, combine):
		result = default()
		for entry in self.build_src:
			combine(result, src_getter(entry).get(self.build_rule.name, src_getter(entry).get(None, default())))
		return result

	def get_build_inputs(self):
		result = self._get_build_x(lambda e: e.on_use_inputs, list, list.extend)
		def get_build_input_name(value):
			if hasattr(value, 'name'):
				return value.name
			return value
		return map(get_build_input_name, result)

	def get_build_deps(self):
		return self._get_build_x(lambda e: e.on_use_deps, list, list.extend)

	def drop_build_opt(self):
		self._drop_opt = True

	def get_build_flags(self):
		def combine_flags(result, flags):
			for key, value in flags.items():
				if value:
					result[key] = ('%s %s' % (result.get(key, ''), value)).strip()
		result = self._get_build_x(lambda e: e.on_use_flags, dict, combine_flags)
		if self._drop_opt:
			result.pop('opts', None)
		return result


class InputFile(BuildSource):
	def __init__(self, name):
		BuildSource.__init__(self, on_use_inputs = {None: [name]})


class Environment(BuildSource):
	def __init__(self, **kwargs):
		BuildSource.__init__(self, on_use_flags = {None: kwargs})


def add_env(**kwargs):
	kwargs = filter(lambda key_value: key_value[1] != None, kwargs.items())
	if kwargs:
		return [Environment(**dict(kwargs))]
	return []


class External(BuildSource):
	def __init__(self, ctx, on_use_flags = {}, rules = [], handlers = {}):
		BuildSource.__init__(self, on_use_flags = on_use_flags)
		self.rules = rules
		self.handlers = handlers

	def _get_exec(self, template, version = None, fmt = '%s-%s'):
		if isinstance(version, VersionComparison):
			return template # TODO
		if not version:
			return template
		return fmt % (template, version)
External.available = {}


def construct_external(ctx, value, *args, **kwargs):
	value == value.lower()
	if value not in External.available:
		raise Exception('Unknown external %r' % value)
	try:
		return External.available[value](ctx, *args, **kwargs)
	except ProcessError:
		sys.stderr.write('Unable to find external %s\n' % value)
	except VersionError:
		sys.stderr.write('Unable to find correct version of %s\n' % value)


class External_pthread(External):
	def __init__(self, ctx):
		External.__init__(self, ctx, on_use_flags = {None: {'opts': '-pthread'}})
External.available['pthread'] = External_pthread


class External_CPP(External):
	def __init__(self, ctx, compiler, linker, compiler_flags, static_flags, shared_flags, exe_flags):
		External.__init__(self, ctx,
			rules = [
				Rule('compile_cpp', '$CXX $CXX_FLAGS ${opts} -MMD -MT $out -MF $out.d -c $in -o $out', 'compile(cpp) $out',
					{'CXX': compiler, 'CXX_FLAGS': compiler_flags}, depfile = '$out.d', deps = 'gcc'),
				Rule('link_static', 'rm -f $out && $LINKER_STATIC $LINKER_STATIC_FLAGS ${opts} $out $in', 'link(static) $out',
					{'LINKER_STATIC': linker, 'LINKER_STATIC_FLAGS': static_flags}),
				Rule('link_shared', '$LINKER_SHARED $LINKER_SHARED_FLAGS ${opts} -o $out $in', 'link(shared) $out',
					{'LINKER_SHARED': compiler, 'LINKER_SHARED_FLAGS': shared_flags}),
				Rule('link_exe', '$LINKER_EXE $LINKER_EXE_FLAGS ${opts} -o $out $in', 'link(exe) $out',
					{'LINKER_EXE': compiler, 'LINKER_EXE_FLAGS': exe_flags}),
			],
			handlers = {'cpp': 'compile_cpp', 'cxx': 'compile_cpp', 'cc': 'compile_cpp'}
		)


class External_GCC(External_CPP):
	def __init__(self, ctx, version = None, std = None,
			compiler_flags = '-fPIC -Wall -pedantic -pthread',
			static_flags = 'rcs',
			shared_flags = '-shared -g -Ofast',
			exe_flags = '-g -Ofast'):
		compiler = self._get_exec('g++', version)
		run_process([compiler, '-v'])
		if std:
			compiler_flags = '-std=%s %s' % (std, compiler_flags)
		External_CPP.__init__(self, ctx, compiler, 'gcc-ar', compiler_flags, static_flags, shared_flags, exe_flags)
External.available['gcc'] = External_GCC


class External_Clang(External_CPP):
	def __init__(self, ctx, version = None, std = None,
			compiler_flags = '-fPIC -Wall -pedantic -pthread',
			static_flags = 'rcs',
			shared_flags = '-shared -g -Ofast',
			exe_flags = '-g -Ofast'):
		compiler = 'clang++'
		installed_version = run_process([compiler, '-v'])[1].splitlines()[0].split()[2]
		if version and not version.check(installed_version):
			raise VersionError
		if std:
			compiler_flags = '-std=%s %s' % (std, compiler_flags)
		External_CPP.__init__(self, ctx, compiler, 'llvm-ar', compiler_flags, static_flags, shared_flags, exe_flags)
External.available['clang'] = External_Clang


class External_Python(External):
	def __init__(self, ctx, version = None):
		build_helper = self._get_exec('python-config', version, fmt = '%s%s')
		link_flags = run_process([build_helper, '--ldflags'])[0]
		External.__init__(self, ctx,
			on_use_flags = {
				'compile_cpp': {'opts': run_process([build_helper, '--cflags'])[0]},
				'link_static': {'opts': link_flags},
				'link_shared': {'opts': link_flags},
				'link_exe': {'opts': link_flags},
			})
External.available['python'] = External_Python


class External_SWIG(External):
	def __init__(self, ctx, version = None):
		run_process(['swig', '-version'])
		External.__init__(self, ctx)
		self._ctx = ctx

	def wrapper(self, lang, name, ifile, libs = [], swig_opts = None, **kwargs):
		wrapper_ext = self._ctx.find_external(lang)

		swig_rule = Rule('swig_cpp_%s' % lang, 'swig -c++ -%s -I. ${opts} -o $out $in' % lang, 'swig(C++ -> %s) $out' % lang, {})
		wrapper_create_target = BuildTarget(name + '.cpp', swig_rule,
			[InputFile(ifile)] + add_env(opts = swig_opts),
			on_use_inputs = {'compile_cpp': [name + '.cpp']})
		self._ctx.registry.register_target(wrapper_create_target)

		wrapper_compile_target = BuildTarget(name + '.o', self._ctx.get_rule('compile_cpp'),
			[wrapper_create_target, wrapper_ext],
			on_use_inputs = {'link_shared': [name + '.o']})
		self._ctx.registry.register_target(wrapper_compile_target)

		wrapper_lib_target = self._ctx.shared_library('_' + name, [wrapper_compile_target] + libs)
		return wrapper_lib_target
External.available['swig'] = External_SWIG


def get_normed_name(fn, forced_ext):
	(root, ext) = os.path.splitext(fn)
	return (root + forced_ext, ext.lstrip('.'))


class Registry(object):
	def __init__(self):
		self.target_key_dict = {}
		self.target_list = []

	def register_target(self, target):
		target_key = target.get_key()
		stored_target = self.target_key_dict.get(target_key)
		if not stored_target:
			self.target_list.append(target)
			stored_target = self.target_key_dict.setdefault(target_key, target)
		return stored_target

	def write(self):
		rules_used = {}
		target_collisions = {}
		# identify targets with the same name but different configuration and
		# find all used rules (and their parameters)
		for target in self.target_list:
			target_opts = target.get_build_flags().get('opts', '')
			rules_used.setdefault(target.build_rule.name, {}).setdefault(target_opts, []).append(target)
			target_collisions.setdefault(target.name, []).append(target.get_key())
		# rename colliding targets
		for target in self.target_list:
			if len(set(target_collisions.get(target.name, []))) != 1:
				(root, ext) = os.path.splitext(target.name)
				target.name = root + '_' + md5(repr(target.get_key())).hexdigest() + ext

		rules_unique = {}
		# identify rules with a fixed set of parameters to fold them into the rule definition
		for rule_name, opts_of_targets in rules_used.items():
			if len(opts_of_targets) == 1: # the rule 'rule_name' is always called with the same opts
				target_opts, targets = opts_of_targets.items()[0]
				if target_opts and (len(targets) > 1): # ignore if the rule is only called once anyway
					for target in targets:
						target.build_rule.name += '_' + md5(target_opts).hexdigest()
						target.build_rule.cmd = target.build_rule.cmd.replace('${opts}', target_opts)
						target.drop_build_opt()
			for target_opts, targets in opts_of_targets.items():
				for target in targets:
					target.build_rule = rules_unique.setdefault(target.build_rule.name, target.build_rule)

		return (list(sorted(rules_unique.values(), key = lambda r: r.name)), self.target_list)


class Context(object):
	def __init__(self, registry, platform, compiler,
			implicit_input = [],
			implicit_object_input = [],
			implicit_static_library_input = [],
			implicit_shared_library_input = [],
			implicit_executable_input = []):
		(self.registry, self.platform, self.compiler) = (registry, platform, compiler)
		self._implicit_object_input = implicit_object_input + implicit_input
		self._implicit_static_library_input = implicit_static_library_input + implicit_input
		self._implicit_shared_library_input = implicit_shared_library_input + implicit_input
		self._implicit_executable_input = implicit_executable_input + implicit_input

	def process_inputs(self, input_list, compiler_opts):
		if isinstance(input_list, str):
			input_list = input_list.split()
		result = []
		for entry in input_list:
			if isinstance(entry, str):
				entry = self.object_file(entry, [InputFile(entry)], compiler_opts)
			elif isinstance(entry, BuildTarget):
				entry = self.registry.register_target(entry)
			result.append(entry)
		return result

	def get_rule(self, name):
		for pn, p in self.compiler.items():
			for r in p.rules:
				if r.name == name:
					return Rule(r.name, r.cmd, r.desc, r.defaults, **dict(r.params))

	def find_external(self, *args, **kwargs):
		return construct_external(self, *args, **kwargs)

	def create_target(self, target_name, rule_name, inputs, target_opts, process_input_opts, **kwargs):
		target = BuildTarget(target_name, self.get_rule(rule_name),
			self.process_inputs(inputs, process_input_opts) + add_env(opts = target_opts), **kwargs)
		return self.registry.register_target(target)

	def object_file(self, obj_name, inputs, compiler_opts = None, **kwargs):
		(obj_name, ext) = get_normed_name(obj_name, self.platform.extensions['object'])
		for pn, p in self.compiler.items():
			if ext in p.handlers:
				rule_name = p.handlers[ext]
				target = self.create_target(obj_name, rule_name, self._implicit_object_input + inputs,
					target_opts = compiler_opts, process_input_opts = None,
					on_use_inputs = {None: [SelfReference()]}, **kwargs)
				return self.registry.register_target(target)
		raise Exception('Unable to create object file %s' % object_name)

	def static_library(self, lib_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['static'])
		return self.create_target(lib_name, 'link_static', self._implicit_static_library_input + inputs,
			linker_opts, compiler_opts, on_use_inputs = {None: [lib_name]}, **kwargs)

	def shared_library(self, lib_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['shared'])
		link_name = lib_name.replace(self.platform.extensions['shared'], '')
		if lib_name.startswith('lib'):
			link_name = link_name[3:]
		target = self.create_target(lib_name, 'link_shared', self._implicit_shared_library_input + inputs,
			linker_opts, compiler_opts, on_use_deps = {None: [SelfReference()]},
			on_use_flags = {None: {'opts': '-L. -l%s' % link_name}}, **kwargs)
		return target

	def executable(self, exe_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		if not exe_name.endswith(self.platform.extensions['exe']):
			exe_name += self.platform.extensions['exe']
		return self.create_target(exe_name, 'link_exe', self._implicit_executable_input + inputs,
			linker_opts, compiler_opts, **kwargs)


def generate_build_file(bfn, ofn):
	class Platform(object):
		def __init__(self):
			self.extensions = {'object': '.o', 'shared': '.so', 'static': '.a', 'exe': ''}
	platform = Platform()
	compiler = {}
	registry = Registry()
	ctx = Context(registry, platform, compiler)
	compiler['C++'] = Delayed(External_GCC, ctx)
	def default_ctx_call(fun, keyword_only = False):
		if keyword_only:
			return lambda **kwargs: fun(exec_globals['default_context'], **kwargs)
		return lambda *args, **kwargs: fun(exec_globals['default_context'], *args, **kwargs)
	def create_ctx(**kwargs):
		platform = kwargs.pop('platform', ctx.platform)
		compiler = kwargs.pop('compiler', ctx.compiler)
		return Context(registry, platform, compiler, **kwargs)
	exec_globals = {
		'pyrate_version': pyrate_version,
		'compiler': compiler,
		'default': None,
		'default_context': ctx,
		'match': match,
		'version': VersionComparison(),
		'find_external': default_ctx_call(Context.find_external),
		'get_rule': default_ctx_call(Context.get_rule),
		'executable': default_ctx_call(Context.executable),
		'shared_library': default_ctx_call(Context.shared_library),
		'static_library': default_ctx_call(Context.static_library),
		'BuildSource': default_ctx_call(BuildSource, keyword_only = True),
		'Context': create_ctx,
		'InputFile': InputFile,
	}

	with open(bfn) as bfp:
		exec(bfp.read(), exec_globals)

	(rules, targets) = registry.write()
	writer = NinjaBuildFileWriter(ofn)
	list(map(writer.write_rule, rules))
	list(map(writer.write_target, targets))
	if exec_globals['default']:
		writer.set_default(map(str, exec_globals['default']))

def main():
	try:
		import argparse
		parser = argparse.ArgumentParser()
		parser.add_argument('build_file', nargs=1)
		parser.add_argument('--output', nargs=1, default = ['build.ninja'],
			help = 'name of output build file')
		args = parser.parse_args()
		(bfn, ofn) = (args.build_file[0], args.output[0])
	except ImportError:
		import optparse
		parser = optparse.OptionParser(usage = 'pyrate [options] build_file')
		parser.add_option('', '--output', default = 'build.ninja',
			help = 'name of output build file', dest="output")
		(args, posargs) = parser.parse_args()
		(bfn, ofn) = (posargs[0], args.output)

	if os.path.dirname(bfn):
		os.chdir(os.path.dirname(bfn))
	generate_build_file(os.path.basename(bfn), ofn)

if __name__ == '__main__':
	main()
