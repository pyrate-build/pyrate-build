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

pyrate_version = (0, 1, 7)

import os, sys
try:
	import hashlib
	def calc_hash(value):
		return hashlib.md5(repr(value).encode('ascii')).hexdigest()
except ImportError:
	def calc_hash(value):
		return __import__('md5').md5(repr(value)).hexdigest()

def none_to_obj(value, obj):
	if value is None:
		return obj
	return value

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
	(stdout, stderr) = p.communicate()
	return (stdout.decode('utf-8'), stderr.decode('utf-8'))


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
		other = tuple(map(int, str(other).split('.')))
		if not other:
			return False
		value = tuple(map(int, self.value))
		if len(other) > len(value):
			value = tuple(list(value) + [0]*(len(other) - len(value)))
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
		self._fp.write('default %s\n' % str.join(' ', map(lambda t: t.name, target_list)))
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
		inputs = str.join(' ', map(lambda t: t.name, target.get_build_inputs()))
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
		self.params = sorted(kwargs.items())

	def get_hash(self):
		return calc_hash([self.name, self.cmd, self.desc, sorted(self.defaults.items()), self.params])

	def __repr__(self):
		return nice_repr(self, 8)


class BuildSource(object):
	def __init__(self, on_use_inputs = None, on_use_deps = None, on_use_flags = None):
		self.on_use_inputs = self._resolve_self(on_use_inputs)
		self.on_use_deps = self._resolve_self(on_use_deps)
		self.on_use_flags = dict(none_to_obj(on_use_flags, {}))

	def _resolve_self(self, on_use_dict):
		on_use_dict = none_to_obj(on_use_dict, {})
		result = {}
		for key, value_list in on_use_dict.items():
			for value in value_list:
				if isinstance(value, SelfReference):
					value = self
				result.setdefault(key, []).append(value)
		return result

	def get_hash(self, others = None):
		def get_dict_keys(src):
			result = []
			for key, value_list in src.items():
				result.append(calc_hash(key))
				for value in value_list:
					if value == self:
						result.append(calc_hash(0))
					else:
						result.append(value.get_hash())
			return result
		hash_tmp = get_dict_keys(self.on_use_inputs) + get_dict_keys(self.on_use_deps)
		return calc_hash(none_to_obj(others, []) + hash_tmp + sorted(self.on_use_flags.items()))

	def __repr__(self):
		return nice_repr(self, 14)


class BuildTarget(BuildSource):
	def __init__(self, name, build_rule, build_src,
			on_use_inputs = None, on_use_deps = None, on_use_flags = None):
		BuildSource.__init__(self, on_use_inputs, on_use_deps, on_use_flags)
		(self.name, self.build_rule, self.build_src) = (name, build_rule, build_src)
		self._drop_opt = False

	def get_hash(self):
		return calc_hash([self.name, self.build_rule.get_hash(),
			list(sorted(map(lambda t: t.get_hash(), self.get_build_inputs()))),
			list(sorted(map(lambda t: t.get_hash(), self.get_build_deps()))),
			list(sorted(self.get_build_flags().items()))])

	def _get_build(self, src_getter, default, combine):
		result = default()
		for entry in self.build_src:
			combine(result, src_getter(entry).get(self.build_rule.name, src_getter(entry).get(None, default())))
		return result

	def get_build_inputs(self):
		return self._get_build(lambda e: e.on_use_inputs, list, list.extend)

	def get_build_deps(self):
		return self._get_build(lambda e: e.on_use_deps, list, list.extend)

	def drop_build_opt(self):
		self._drop_opt = True

	def get_build_flags(self):
		def combine_flags(result, flags):
			for key, value in flags.items():
				if value:
					result[key] = ('%s %s' % (result.get(key, ''), value)).strip()
		result = self._get_build(lambda e: e.on_use_flags, dict, combine_flags)
		if self._drop_opt:
			result.pop('opts', None)
		return result


class InputFile(BuildSource):
	def __init__(self, name):
		self.name = name
		BuildSource.__init__(self, on_use_inputs = {None: [self]})

	def __repr__(self):
		return '%s(name = %s, on_use_inputs = {None: [self]})' % (self.__class__.__name__, self.name)


class RuleVariables(BuildSource):
	def __init__(self, **kwargs):
		BuildSource.__init__(self, on_use_flags = {None: kwargs})


def add_rule_vars(**kwargs):
	kwargs = list(filter(lambda key_value: key_value[1] != None, kwargs.items()))
	if kwargs:
		return [RuleVariables(**dict(kwargs))]
	return []


class External(BuildSource):
	def __init__(self, ctx, on_use_flags = None, rules = None, ext_handlers = None,
			enforced_flags_by_target_type = None):
		assert(ctx)
		BuildSource.__init__(self, on_use_flags = on_use_flags)
		self.rules = none_to_obj(rules, [])
		self.ext_handlers = none_to_obj(ext_handlers, {})
		self.enforced_flags_by_target_type = none_to_obj(enforced_flags_by_target_type, {})

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
		External.__init__(self, ctx, on_use_flags = {
			'compile_cpp': {'opts': '-pthread'},
			'link_static': {'opts': '-pthread'},
			'link_shared': {'opts': '-pthread'},
			'link_exe': {'opts': '-pthread'},
		})
External.available['pthread'] = External_pthread


class External_CPP(External):
	def __init__(self, ctx, compiler, linker, compile_cpp_flags,
			link_static_flags, link_shared_flags, link_exe_flags):
		External.__init__(self, ctx,
			rules = [
				Rule('compile_cpp', '$CXX $CXX_FLAGS ${opts} -MMD -MT $out -MF $out.d -c $in -o $out', 'compile(cpp) $out',
					{'CXX': compiler, 'CXX_FLAGS': compile_cpp_flags}, depfile = '$out.d', deps = 'gcc'),
				Rule('link_static', 'rm -f $out && $LINKER_STATIC $LINKER_STATIC_FLAGS ${opts} $out $in', 'link(static) $out',
					{'LINKER_STATIC': linker, 'LINKER_STATIC_FLAGS': link_static_flags}),
				Rule('link_shared', '$LINKER_SHARED $LINKER_SHARED_FLAGS ${opts} -o $out $in', 'link(shared) $out',
					{'LINKER_SHARED': compiler, 'LINKER_SHARED_FLAGS': link_shared_flags}),
				Rule('link_exe', '$LINKER_EXE $LINKER_EXE_FLAGS ${opts} -o $out $in', 'link(exe) $out',
					{'LINKER_EXE': compiler, 'LINKER_EXE_FLAGS': link_exe_flags}),
			],
			ext_handlers = {'.cpp': 'compile_cpp', '.cxx': 'compile_cpp', '.cc': 'compile_cpp'},
			enforced_flags_by_target_type = {'shared': {'compile_cpp': {'opts': ['-fPIC']}}})


class External_GCC(External_CPP):
	def __init__(self, ctx, version = None, std = None,
			compile_cpp_flags = '-Wall -pedantic',
			link_static_flags = 'rcs',
			link_shared_flags = '-shared -g -fPIC',
			link_exe_flags = '-g'):
		compiler = self._get_exec('g++', version)
		run_process([compiler, '-v'])
		if std:
			compile_cpp_flags = '-std=%s %s' % (std, compile_cpp_flags)
		External_CPP.__init__(self, ctx, compiler, 'gcc-ar',
			compile_cpp_flags, link_static_flags, link_shared_flags, link_exe_flags)
External.available['gcc'] = External_GCC


class External_Clang(External_CPP):
	def __init__(self, ctx, version = None, std = None,
			compile_cpp_flags = '-Weverything',
			link_static_flags = 'rcs',
			link_shared_flags = '-shared -g -fPIC',
			link_exe_flags = '-g'):
		compiler = 'clang++'
		installed_version = run_process([compiler, '-v'])[1].splitlines()[0].split()[2]
		if version and not version.check(installed_version):
			raise VersionError
		if std:
			compile_cpp_flags = '-std=%s %s' % (std, compile_cpp_flags)
		External_CPP.__init__(self, ctx, compiler, 'llvm-ar',
			compile_cpp_flags, link_static_flags, link_shared_flags, link_exe_flags)
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
		installed_version = ''
		for version_line in run_process(['swig', '-version'])[0].splitlines():
			if 'version' in version_line.lower():
				installed_version = version_line.split()[-1]
				break
		if version and not version.check(installed_version):
			raise VersionError
		External.__init__(self, ctx)
		self._ctx = ctx

	def wrapper(self, lang, name, ifile, libs = None, swig_opts = None, context = None, **kwargs):
		if context is None:
			context = self._ctx
		wrapper_ext = context.find_external(lang)
		swig_rule = Rule('swig_cpp_%s' % lang, 'swig -c++ -%s -I. ${opts} -module ${module_name} -o $out $in' % lang, 'swig(C++ -> %s) $out' % lang, {})
		(src_name, ext) = get_normed_name(name, '.cpp')
		wrapper_src = BuildTarget(src_name, swig_rule,
			[InputFile(ifile)] + add_rule_vars(opts = swig_opts, module_name = name),
			on_use_inputs = {None: [SelfReference()]},
			on_use_flags = wrapper_ext.on_use_flags)
		return context.shared_library('_' + name, [wrapper_src, wrapper_ext] + none_to_obj(libs, []))
External.available['swig'] = External_SWIG


def get_normed_name(fn, forced_ext):
	(root, ext) = os.path.splitext(fn)
	return (root + forced_ext, ext.lstrip('.'))


class Registry(object):
	def __init__(self):
		self.target_list = []

	def register_target(self, target):
		assert(isinstance(target, BuildTarget))
		self.target_list.append(target)
		return target

	def write(self):
		# deduplicate targets in target_list (and recursively in build_src) based on hash
		target_hash_list = []
		target_hash_seen = {}
		def update_target_hash_list(target, target_hash):
			if target_hash not in target_hash_seen:
				target_hash_list.append((target, target_hash))
				target_hash_seen[target_hash] = target
				def deduplicate_targets(src):
					if isinstance(src, BuildTarget):
						src_hash = src.get_hash()
						update_target_hash_list(src, src_hash)
						return target_hash_seen[src_hash]
					return src
				target.build_src = list(map(deduplicate_targets, target.build_src))
		for target in self.target_list:
			update_target_hash_list(target, target.get_hash())

		# identify targets with the same name but different configuration and
		# find all used rules (and their parameters)
		rules_used = {}
		target_collisions = {}
		for target, target_hash in target_hash_list:
			target_opts = target.get_build_flags().get('opts', '')
			rules_used.setdefault(target.build_rule.name, {}).setdefault(target_opts, []).append(target)
			target_collisions.setdefault(target.name, []).append(target_hash)
		# rename colliding targets
		for target, target_hash in target_hash_list:
			if len(set(target_collisions.get(target.name, []))) != 1:
				(root, ext) = os.path.splitext(target.name)
				target.name = root + '_' + target_hash + ext

		rules_unique = {}
		# identify rules with a fixed set of parameters to fold them into the rule definition
		for opts_of_targets in rules_used.values():
			if len(opts_of_targets) == 1: # the rule 'rule_name' is always called with the same opts
				target_opts, targets = list(opts_of_targets.items())[0]
				if target_opts and (len(targets) > 1): # ignore if the rule is only called once anyway
					for target in targets:
						target.build_rule.name += '_' + calc_hash(target_opts)
						target.build_rule.cmd = target.build_rule.cmd.replace('${opts}', target_opts)
						target.drop_build_opt()
			for targets in opts_of_targets.values():
				for target in targets:
					target.build_rule = rules_unique.setdefault(target.build_rule.name, target.build_rule)

		write_rules = list(sorted(rules_unique.values(), key = lambda r: r.name))
		write_targets = list(map(lambda t_th: t_th[0], target_hash_list))
		return (write_rules, write_targets)


class Platform(object):
	def __init__(self):
		self.extensions = {'object': '.o', 'shared': '.so', 'static': '.a', 'exe': ''}

	def get_required_flags(self, target_type, compiler_dict):
		required_flags = {}
		for compiler in compiler_dict.values():
			for rule_name, flags in compiler.enforced_flags_by_target_type.get(target_type, {}).items():
				for opt_name, opts in flags.items():
					required_flags.setdefault(rule_name, {}).setdefault(opt_name, []).extend(opts)
		return required_flags


class Context(object):
	def __init__(self, registry, platform, compiler,
			implicit_input = None,
			implicit_object_input = None,
			implicit_static_library_input = None,
			implicit_shared_library_input = None,
			implicit_executable_input = None):
		(self.registry, self.platform, self.compiler) = (registry, platform, compiler)
		implicit_input = none_to_obj(implicit_input, [])
		self._implicit_object_input = none_to_obj(implicit_object_input, []) + implicit_input
		self._implicit_static_library_input = none_to_obj(implicit_static_library_input, []) + implicit_input
		self._implicit_shared_library_input = none_to_obj(implicit_shared_library_input, []) + implicit_input
		self._implicit_executable_input = none_to_obj(implicit_executable_input, []) + implicit_input

	def find_external(self, *args, **kwargs):
		return construct_external(self, *args, **kwargs)

	def find_rule(self, name): # return a new instance
		for compiler in self.compiler.values():
			for r in compiler.rules:
				if r.name == name:
					return Rule(r.name, r.cmd, r.desc, r.defaults, **dict(r.params))

	def find_handlers(self, obj):
		def find_ext_handler(name):
			result = set()
			ext = os.path.splitext(name)[1]
			for compiler in self.compiler.values():
				if ext in compiler.ext_handlers:
					result.add(compiler.ext_handlers[ext])
			return result
		result = set()
		if hasattr(obj, 'name'):
			result.update(find_ext_handler(obj.name))
		return result

	def force_build_source(self, input_list):
		input_list = none_to_obj(input_list, [])
		if isinstance(input_list, str): # support accepting user supplied space separated string
			input_list = input_list.split()
		def translate_str(value):
			if isinstance(value, str):
				return InputFile(value)
			elif isinstance(value, BuildTarget):
				return self.registry.register_target(value)
			return value
		return list(map(translate_str, input_list))

	def create_target(self, target_name, rule_name, input_list, add_self_to_on_use_inputs, **kwargs):
		on_use_inputs = kwargs.pop('on_use_inputs', {})
		if add_self_to_on_use_inputs:
			on_use_inputs.setdefault(None, []).append(SelfReference())
		target = BuildTarget(target_name, self.find_rule(rule_name), input_list,
			on_use_inputs = on_use_inputs, **kwargs)
		return self.registry.register_target(target)

	def object_file(self, obj_name, input_list = None, compiler_opts = None, **kwargs):
		input_list = self.force_build_source(input_list)
		# collect rules from the input object extensions
		input_rules = set()
		for obj in input_list:
			input_rules.update(self.find_handlers(obj))
		if len(input_rules) != 1:
			raise Exception('Unable to find unique rule (%s) to generate %s' % (repr(input_rules), obj_name))
		(obj_name, obj_name_ext) = get_normed_name(obj_name, self.platform.extensions['object'])
		return self.create_target(obj_name, rule_name = input_rules.pop(),
			input_list = self._implicit_object_input + input_list + add_rule_vars(opts = compiler_opts),
			add_self_to_on_use_inputs = True, **kwargs)

	def link(self, output_name, rule_name, input_list, implicit_input_list,
			add_self_to_on_use_inputs, ensure_flags_by_rule, **kwargs):
		input_list = self.force_build_source(input_list)
		obj_sources = {}
		env_list = []
		for obj in input_list:
			input_rules = self.find_handlers(obj)
			if len(input_rules) == 1:
				obj_sources.setdefault(input_rules.pop(), []).append(obj)
			elif not input_rules:
				env_list.append(obj)
			else:
				raise Exception('Found multiple rules (%s) to generate object from %s' % (repr(input_rules), repr(obj)))
		result = []
		compiler_opts = kwargs.pop('compiler_opts', None)
		for input_list in obj_sources.values():
			for input_obj in input_list:
				result.append(self.object_file(input_obj.name,
					input_list = self._implicit_object_input + [input_obj], compiler_opts = compiler_opts))
		input_list = result + env_list
		input_list += implicit_input_list + add_rule_vars(opts = kwargs.pop('linker_opts', None))

		ensure_flags_processed_targets = set()
		def do_ensure_flags(t):
			flags = t.get_build_flags()
			ensure_flags = ensure_flags_by_rule.get(t.build_rule.name, {})
			for opt_key, opt_list in ensure_flags.items():
				for opt in opt_list:
					if opt not in flags.get(opt_key, ''):
						t.build_src += add_rule_vars(opts = opt)
			for src in t.build_src:
				if src not in ensure_flags_processed_targets:
					ensure_flags_processed_targets.add(src)
					if isinstance(src, BuildTarget):
						do_ensure_flags(src)
			return t

		return do_ensure_flags(self.create_target(output_name, rule_name = rule_name,
			input_list = input_list, add_self_to_on_use_inputs = add_self_to_on_use_inputs, **kwargs))

	def shared_library(self, lib_name, input_list, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['shared'])
		link_name = lib_name.replace(self.platform.extensions['shared'], '')
		if lib_name.startswith('lib'):
			link_name = link_name[3:]
		on_use_flags = kwargs.pop('on_use_flags', {})
		on_use_flags.setdefault(None, {}).setdefault('opts', '')
		on_use_flags[None]['opts'] += ' -L. -l%s' % link_name
		on_use_deps = kwargs.pop('on_use_deps', {})
		on_use_deps.setdefault(None, []).append(SelfReference())
		return self.link(lib_name, rule_name = 'link_shared', 
			input_list = input_list, add_self_to_on_use_inputs = False,
			ensure_flags_by_rule = self.platform.get_required_flags('shared', self.compiler),
			implicit_input_list = self._implicit_shared_library_input,
			on_use_deps = on_use_deps, on_use_flags = on_use_flags, **kwargs)

	def static_library(self, lib_name, input_list, **kwargs):
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['static'])
		return self.link(lib_name, rule_name = 'link_static',
			input_list = input_list, add_self_to_on_use_inputs = True,
			ensure_flags_by_rule = self.platform.get_required_flags('static', self.compiler),
			implicit_input_list = self._implicit_static_library_input, **kwargs)

	def executable(self, exe_name, input_list, **kwargs):
		if not exe_name.endswith(self.platform.extensions['exe']):
			exe_name += self.platform.extensions['exe']
		return self.link(exe_name, rule_name = 'link_exe',
			input_list = input_list, add_self_to_on_use_inputs = False,
			ensure_flags_by_rule = self.platform.get_required_flags('exe', self.compiler),
			implicit_input_list = self._implicit_executable_input, **kwargs)


def create_ctx(**kwargs):
	platform = kwargs.pop('platform', ctx.platform)
	compiler = kwargs.pop('compiler', ctx.compiler)
	return Context(registry, platform, compiler, **kwargs)


def default_ctx_call(exec_dict, fun, keyword_only = False):
	if keyword_only:
		return lambda **kwargs: fun(exec_dict['default_context'], **kwargs)
	return lambda *args, **kwargs: fun(exec_dict['default_context'], *args, **kwargs)


def generate_build_file(bfn, ofn):
	compiler = {}
	platform = Platform()
	registry = Registry()
	ctx = Context(registry, platform, compiler)
	compiler['C++'] = Delayed(External_GCC, ctx)
	exec_globals = {}
	exec_globals.update({
		'pyrate_version': pyrate_version,
		'compiler': compiler,
		'default_targets': None,
		'default_context': ctx,
		'register_target': registry.register_target,
		'match': match,
		'version': VersionComparison(),
		'find_external': default_ctx_call(exec_globals, Context.find_external),
		'find_rule': default_ctx_call(exec_globals, Context.find_rule),
		'object_file': default_ctx_call(exec_globals, Context.object_file),
		'executable': default_ctx_call(exec_globals, Context.executable),
		'shared_library': default_ctx_call(exec_globals, Context.shared_library),
		'static_library': default_ctx_call(exec_globals, Context.static_library),
		'BuildSource': default_ctx_call(exec_globals, BuildSource, keyword_only = True),
		'BuildTarget': default_ctx_call(exec_globals, BuildTarget, keyword_only = True),
		'External': default_ctx_call(exec_globals, External, keyword_only = True),
		'Context': create_ctx,
		'InputFile': InputFile,
		'Rule': Rule,
	})

	with open(bfn) as bfp:
		exec(bfp.read(), exec_globals)

	(rules, targets) = registry.write()
	writer = NinjaBuildFileWriter(ofn)
	list(map(writer.write_rule, rules))
	list(map(writer.write_target, targets))
	if exec_globals['default_targets']:
		writer.set_default(exec_globals['default_targets'])

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
			help = 'name of output build file', dest='output')
		(args, posargs) = parser.parse_args()
		(bfn, ofn) = (posargs[0], args.output)

	if os.path.dirname(bfn):
		os.chdir(os.path.dirname(bfn))
	generate_build_file(os.path.basename(bfn), ofn)

if __name__ == '__main__':
	main()
