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

pyrate_version = (0, 1, 3)

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
		self._fp.write('%s = %s\n' % (key, value))
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
		inputs = str.join(' ', target.build_inputs)
		self._fp.write('build %s: %s %s' % (target.name, target.build_rule.name, inputs))
		if target.build_deps:
			self._fp.write(' | %s' % str.join(' ', target.build_deps))
		self._fp.write('\n')
		for key_value in target.build_flags.items():
			self._fp.write('  %s = %s\n' % key_value)


class Rule(object):
	def __init__(self, name, cmd, desc, defaults, **kwargs):
		(self.name, self.cmd, self.desc, self.defaults) = (name, cmd, desc, defaults)
		self.params = kwargs.items()


class BuildSource(object):
	def __init__(self, on_use_inputs = {}, on_use_deps = {}, on_use_flags = {}):
		(self.on_use_inputs, self.on_use_deps, self.on_use_flags) = (on_use_inputs, on_use_deps, on_use_flags)


class BuildTarget(BuildSource):
	def __init__(self, name, build_rule, build_src, on_use_inputs = {}, on_use_deps = {}, on_use_flags = {}):
		BuildSource.__init__(self, on_use_inputs, on_use_deps, on_use_flags)
		(self.name, self.build_rule) = (name, build_rule)
		(self.build_inputs, self.build_deps, self.build_flags) = ([], [], {})
		def get(src, default):
			return src.get(build_rule.name, src.get(None, default))
		for entry in build_src:
			self.build_inputs.extend(get(entry.on_use_inputs, []))
			self.build_deps.extend(get(entry.on_use_deps, []))
			for key, value in get(entry.on_use_flags, {}).items():
				if value:
					flags = self.build_flags.get(key, '')
					self.build_flags[key] = ('%s %s' % (flags, value)).strip()


class InputFile(BuildSource):
	def __init__(self, name):
		BuildSource.__init__(self, on_use_inputs = {None: [name]})


class Environment(BuildSource):
	def __init__(self, **kwargs):
		BuildSource.__init__(self, on_use_flags = {None: kwargs})


class External(BuildSource):
	def __init__(self, tm, on_use_flags = {}, rules = [], handlers = {}):
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


def create_external(tm, value, *args, **kwargs):
	value == value.lower()
	if value not in External.available:
		raise Exception('Unknown external %r' % value)
	try:
		return External.available[value](tm, *args, **kwargs)
	except ProcessError:
		sys.stderr.write('Unable to find external %s\n' % value)
	except VersionError:
		sys.stderr.write('Unable to find correct version of %s\n' % value)


class External_CPP(External):
	def __init__(self, tm, compiler, linker, compiler_flags, static_flags, shared_flags, exe_flags):
		External.__init__(self, tm,
			rules = [
				Rule('compile_cpp', '$CXX $CXX_FLAGS $opts -MMD -MT $out -MF $out.d -c $in -o $out', 'compile(cpp) $out',
					{'CXX': compiler, 'CXX_FLAGS': compiler_flags}, depfile = '$out.d', deps = 'gcc'),
				Rule('link_static', 'rm -f $out && $LINKER_STATIC $LINKER_STATIC_FLAGS $opts $out $in', 'link(static) $out',
					{'LINKER_STATIC': linker, 'LINKER_STATIC_FLAGS': static_flags}),
				Rule('link_shared', '$LINKER_SHARED $LINKER_SHARED_FLAGS $opts -o $out $in', 'link(shared) $out',
					{'LINKER_SHARED': compiler, 'LINKER_SHARED_FLAGS': shared_flags}),
				Rule('link_exe', '$LINKER_EXE $LINKER_EXE_FLAGS $opts -o $out $in', 'link(exe) $out',
					{'LINKER_EXE': compiler, 'LINKER_EXE_FLAGS': exe_flags}),
			],
			handlers = {'cpp': 'compile_cpp', 'cxx': 'compile_cpp', 'cc': 'compile_cpp'}
		)


class External_GCC(External_CPP):
	def __init__(self, tm, version = None, std = None,
			compiler_flags = '-fPIC -Wall -pedantic -pthread',
			static_flags = 'rcs',
			shared_flags = '-shared -g -Ofast',
			exe_flags = '-g -Ofast'):
		compiler = self._get_exec('g++', version)
		run_process([compiler, '-v'])
		if std:
			compiler_flags = '-std=%s %s' % (std, compiler_flags)
		External_CPP.__init__(self, tm, compiler, 'gcc-ar', compiler_flags, static_flags, shared_flags, exe_flags)
External.available['gcc'] = External_GCC


class External_Clang(External_CPP):
	def __init__(self, tm, version = None, std = None,
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
		External_CPP.__init__(self, tm, compiler, 'llvm-ar', compiler_flags, static_flags, shared_flags, exe_flags)
External.available['clang'] = External_Clang


class External_Python(External):
	def __init__(self, tm, version = None):
		build_helper = self._get_exec('python-config', version, fmt = '%s%s')
		link_flags = run_process([build_helper, '--ldflags'])[0]
		External.__init__(self, tm,
			on_use_flags = {
				'compile_cpp': {'opts': run_process([build_helper, '--cflags'])[0]},
				'link_static': {'opts': link_flags},
				'link_shared': {'opts': link_flags},
				'link_exe': {'opts': link_flags},
			})
External.available['python'] = External_Python


class External_SWIG(External):
	def __init__(self, tm, version = None):
		run_process(['swig', '-version'])
		External.__init__(self, tm)
		self._tm = tm

	def wrapper(self, lang, name, ifile, libs = [], swig_opts = None, **kwargs):
		wrapper_ext = self._tm.find_external(lang)

		swig_rule = Rule('swig_cpp_%s' % lang, 'swig -c++ -%s -I. $opts -o $out $in' % lang, 'swig(C++ -> %s) $out' % lang, {})
		self._tm.registry.register_rule(swig_rule)

		wrapper_create_target = BuildTarget(name + '.cpp', swig_rule,
			[InputFile(ifile), Environment(opts = swig_opts)],
			on_use_inputs = {'compile_cpp': [name + '.cpp']})
		self._tm.registry.register_target(wrapper_create_target)

		wrapper_compile_target = BuildTarget(name + '.o', self._tm.registry.find_rule('compile_cpp'),
			[wrapper_create_target, wrapper_ext],
			on_use_inputs = {'link_shared': [name + '.o']})
		self._tm.registry.register_target(wrapper_compile_target)

		wrapper_lib_target = self._tm.shared_library('_' + name, [wrapper_compile_target] + libs)
		return wrapper_lib_target
External.available['swig'] = External_SWIG


def get_normed_name(fn, forced_ext, suffix = None):
	(tmp, ext) = os.path.splitext(fn)
	if suffix:
		tmp += '_' + suffix
	return (tmp + forced_ext, ext.lstrip('.'))


class Registry(object):
	def __init__(self, compiler, platform):
		(self._compiler, self._platform) = (compiler, platform)
		try:
			import collections
			dict_cls = collections.OrderedDict
		except Exception:
			dict_cls = dict
		self.handlers = dict_cls()
		self.rules = dict_cls()
		self.targets = dict_cls()

	def find_rule(self, name):
		if name not in self.rules:
			for pn, p in self._compiler.items():
				for r in p.rules:
					if r.name == name:
						return self.register_rule(r)
		return self.rules[name]

	def find_object_target(self, value, compiler_opts):
		suffix = ''
		if compiler_opts:
			suffix = md5(repr(compiler_opts).encode('ascii')).hexdigest()
		(obj_name, ext) = get_normed_name(value, self._platform.extensions['object'], suffix)
		for pn, p in self._compiler.items():
			if ext in p.handlers:
				rule_name = p.handlers[ext]
				target = BuildTarget(obj_name, self.find_rule(rule_name),
					build_src = [InputFile(value), Environment(opts = compiler_opts)],
					on_use_inputs = {None: [obj_name]})
				return self.register_target(target)

	def register_rule(self, rule):
		return self.rules.setdefault(rule.name, rule)

	def register_target(self, target):
		return self.targets.setdefault(target.name, target)


class TargetManager(object):
	def __init__(self, compiler, **kwargs):
		class Platform(object):
			def __init__(self):
				self.extensions = {'object': '.o', 'shared': '.so', 'static': '.a', 'exe': ''}
		self.platform = Platform()
		self.registry = Registry(compiler, self.platform)

	def sort_inputs(self, input_list, compiler_opts):
		if isinstance(input_list, str):
			input_list = input_list.split()
		result = []
		for entry in input_list:
			if isinstance(entry, str):
				entry = self.registry.find_object_target(entry, compiler_opts)
			elif isinstance(entry, BuildTarget):
				entry = self.registry.register_target(entry)
			result.append(entry)
		return result

	def find_external(self, *args, **kwargs):
		return create_external(self, *args, **kwargs)

	def create_target(self, target_name, rule_name, inputs, linker_opts, compiler_opts, **kwargs):
		target = BuildTarget(target_name, self.registry.find_rule(rule_name),
			self.sort_inputs(inputs, compiler_opts) + [Environment(opts = linker_opts)], **kwargs)
		return self.registry.register_target(target)

	def static_library(self, lib_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['static'])
		return self.create_target(lib_name, 'link_static', inputs, linker_opts, compiler_opts,
			on_use_inputs = {None: [lib_name]}, **kwargs)

	def shared_library(self, lib_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['shared'])
		link_name = lib_name.replace(self.platform.extensions['shared'], '')
		if lib_name.startswith('lib'):
			link_name = link_name[3:]
		return self.create_target(lib_name, 'link_shared', inputs, linker_opts, compiler_opts,
			on_use_flags = {None: {'opts': '-L. -l%s' % link_name}},
			on_use_deps = {None: [lib_name]}, **kwargs)

	def executable(self, exe_name, inputs, linker_opts = None, compiler_opts = None, **kwargs):
		if not exe_name.endswith(self.platform.extensions['exe']):
			exe_name += self.platform.extensions['exe']
		return self.create_target(exe_name, 'link_exe', inputs, linker_opts, compiler_opts, **kwargs)

	def write(self):
		return (self.registry.rules, self.registry.targets)


def generate_build_file(bfn, ofn):
	compiler = {}
	tm = TargetManager(compiler)
	compiler['C++'] = Delayed(External_GCC, tm)
	exec_globals = {
		'pyrate_version': pyrate_version,
		'default': None,
		'match': match,
		'version': VersionComparison(),
		'compiler': compiler,
		'find_external': tm.find_external,
		'executable': tm.executable,
		'static_library': tm.static_library,
		'shared_library': tm.shared_library,
	}

	with open(bfn) as bfp:
		exec(bfp.read(), exec_globals)

	(rules, targets) = tm.write()
	writer = NinjaBuildFileWriter(ofn)
	list(map(writer.write_rule, rules.values()))
	list(map(writer.write_target, targets.values()))
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
