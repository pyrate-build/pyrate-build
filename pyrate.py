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

__version__ = '0.2.0'

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
	return (stdout.decode('utf-8').strip(), stderr.decode('utf-8').strip())


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


class Version(object):
	def __init__(self, value):
		if isinstance(value, Version):
			value = value.value
		if isinstance(value, (list, tuple)): # (1,32,5)
			value = list(value)
		elif isinstance(value, str): # '1.32.5'
			value = list(map(int, value.split('.')))
		else:
			try:
				value = list(map(int, str(value).split('.'))) # 1.32
			except Exception:
				raise VersionError('unable to parse version string %s' % repr(value))
		self.value = tuple(value + [0] * (4 - len(value)))
	def __repr__(self):
		return 'Version(%s)' % str.join('.', map(repr, self.value))
	def __lt__(self, other):
		return self.value < Version(other).value
	def __le__(self, other):
		return self.value <= Version(other).value
	def __eq__(self, other):
		return self.value == Version(other).value
	def __ne__(self, other):
		return self.value != Version(other).value
	def __gt__(self, other):
		return self.value > Version(other).value
	def __ge__(self, other):
		return self.value >= Version(other).value


class VersionComparison(object):
	def __init__(self):
		pass
	def __lt__(self, other):
		return Version(other).__gt__
	def __le__(self, other):
		return Version(other).__ge__
	def __eq__(self, other):
		return Version(other).__eq__
	def __ne__(self, other):
		return Version(other).__ne__
	def __gt__(self, other):
		return Version(other).__lt__
	def __ge__(self, other):
		return Version(other).__le__


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
	result.sort()
	return result


class Delayed(object):
	def __init__(self, cls, *args, **kwargs):
		(self._cls, self._args, self._kwargs) = (cls, args, kwargs)
	def get_instance(self):
		return self._cls(*self._args, **self._kwargs)
	def __repr__(self):
		return 'Delayed(%s(*%s, **%s))' % (self._cls, self._args, self._kwargs)


class NinjaBuildFileWriter(object):
	def __init__(self, fn = 'build.ninja'):
		self._fp = open(fn, 'w')
		self._vars = {}
	def set_var(self, key, value):
		if self._vars.get(key) != value:
			self._fp.write('%s = %s\n' % (key, value.strip()))
		self._vars[key] = value
	def set_default(self, target_list, target_list_all):
		self._fp.write('build all: phony %s\n' % str.join(' ', map(lambda t: t.name, target_list_all)))
		if target_list is not None:
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
		for key_value in sorted(target.get_build_variables().items()):
			self._fp.write('  %s = %s\n' % key_value)


class MakefileWriter(object):
	def __init__(self, fn = 'build.make'):
		self._fp = open(fn, 'w')
		self._vars = set()
	def set_var(self, key, value):
		self._fp.write('%s := %s\n' % (key, value.strip()))
	def set_default(self, target_list, target_list_all):
		self._fp.write('all: %s\n' % str.join(' ', map(lambda t: t.name, target_list_all)))
		if target_list is not None:
			self._fp.write('default: %s\n' % str.join(' ', map(lambda t: t.name, target_list)))
		self._fp.write('.DEFAULT_GOAL := default\n')
	def write_rule(self, rule):
		for key, value in sorted(rule.defaults.items()):
			self.set_var(key, value)
		self._fp.write('\n')
	def write_target(self, target):
		def replace_var(value, var_name, var_value):
			return value.replace('$%s' % var_name, var_value).replace('${%s}' % var_name, var_value)
		def replace_var_ref(value, var_name, new_var_name):
			return replace_var(value, var_name, '$(%s)' % new_var_name)

		variables = target.get_build_variables()
		for opt, opt_value in sorted(variables.items()):
			opt_hash = calc_hash([opt, opt_value])
			if opt_hash not in self._vars:
				self._vars.add(opt_hash)
				self.set_var(opt + '_' + opt_hash, opt_value)
		inputs = list(map(lambda t: t.name, target.get_build_inputs()))
		deps = inputs + list(map(lambda t: t.name, target.get_build_deps()))
		rule_params = dict(target.build_rule.params)
		if rule_params.get('deps') == 'gcc':
			depfile = replace_var(rule_params['depfile'], 'out', target.name)
			self._fp.write('-include %s\n' % depfile)
		self._fp.write('%s: %s\n' % (target.name, str.join(' ', deps)))
		cmd = replace_var(replace_var(target.build_rule.cmd, 'out', target.name), 'in', str.join(' ', inputs))
		for opt in sorted(target.build_rule.defaults.keys(), key = len, reverse = True):
			cmd = replace_var_ref(cmd, opt, opt)
		for opt in sorted(variables.keys(), key = len, reverse = True):
			opt_hash = calc_hash([opt, variables[opt]])
			cmd = replace_var_ref(cmd, opt, opt + '_' + opt_hash)
		self._fp.write('\t%s\n\n' % cmd)


class SelfReference(object):
	def __init__(self, ref = None):
		self._ref = ref

	def __repr__(self):
		return 'self'


class Rule(object):
	def __init__(self, connection, name, cmd, desc, defaults, **kwargs):
		(self.connection, self.name, self.cmd, self.desc, self.defaults) = (connection, name, cmd, desc, defaults)
		self.params = sorted(kwargs.items())

	def get_hash(self):
		return calc_hash([self.name, self.cmd, self.desc, sorted(self.defaults.items()), self.params])

	def __repr__(self):
		return nice_repr(self, 8)


class BuildSource(object):
	def __init__(self, on_use_inputs = None, on_use_deps = None, on_use_variables = None):
		self.on_use_inputs = self._resolve_self(on_use_inputs)
		self.on_use_deps = self._resolve_self(on_use_deps)
		self.on_use_variables = dict(none_to_obj(on_use_variables, {}))

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
			for key, value_list in sorted(src.items()):
				result.append(calc_hash(key))
				for value in value_list:
					if value == self:
						result.append(calc_hash(0))
					else:
						result.append(value.get_hash())
			return result
		hash_tmp = get_dict_keys(self.on_use_inputs) + get_dict_keys(self.on_use_deps)
		return calc_hash(none_to_obj(others, []) + hash_tmp + sorted(self.on_use_variables.items()))

	def __repr__(self):
		return nice_repr(self, 14)


class BuildTarget(BuildSource):
	def __init__(self, name, build_rule, build_src,
			on_use_inputs = None, on_use_deps = None, on_use_variables = None, no_rename = False):
		BuildSource.__init__(self, on_use_inputs, on_use_deps, on_use_variables)
		(self.name, self.build_rule, self.build_src) = (name, build_rule, build_src)
		self.no_rename = no_rename
		self._drop_opt = False

	def get_hash(self):
		return calc_hash([self.name, self.build_rule.get_hash(),
			sorted(map(lambda t: t.get_hash(), self.get_build_inputs())),
			sorted(map(lambda t: t.get_hash(), self.get_build_deps())),
			sorted(self.get_build_variables().items())])

	def _get_build(self, src_getter, default, combine):
		result = default()
		for entry in self.build_src:
			src_default = src_getter(entry).get(None, default())
			new = src_getter(entry).get(self.build_rule.name, src_default)
			combine(result, new)
		return result

	def get_build_inputs(self):
		return self._get_build(lambda e: e.on_use_inputs, list, list.extend)

	def get_build_deps(self):
		return self._get_build(lambda e: e.on_use_deps, list, list.extend)

	def drop_build_opt(self):
		self._drop_opt = True

	def get_build_variables(self):
		def combine_variables(result, variables):
			for key, values in variables.items():
				for value in values:
					opt_list = result.setdefault(key, [])
					if value not in opt_list:
						opt_list.append(value)
		result = self._get_build(lambda e: e.on_use_variables, dict, combine_variables)
		if self._drop_opt:
			result.pop('opts', None)
		for key in sorted(result):
			values = result.pop(key)
			tmp = ''
			for value in values:
				if value not in tmp:
					tmp += ' ' + value
			if tmp:
				result[key] = tmp.strip()
		return result


class InputFile(BuildSource):
	def __init__(self, name):
		self.name = name
		BuildSource.__init__(self, on_use_inputs = {None: [self]})

	def __repr__(self):
		return '%s(name = %s, on_use_inputs = {None: [self]})' % (self.__class__.__name__, self.name)


class RuleVariables(BuildSource):
	def __init__(self, on_use_variables):
		BuildSource.__init__(self, on_use_variables = on_use_variables)


def add_rule_vars(**kwargs):
	variables = {}
	for key, value in kwargs.items():
		if value:
			if isinstance(value, list):
				variables.setdefault(key, []).extend(value)
			else:
				variables.setdefault(key, []).append(value)
	if variables:
		return [RuleVariables(on_use_variables = {None: variables})]
	return []


class External(BuildSource):
	def __init__(self, ctx, on_use_variables = None, rules = None, target_types_by_ext = None,
			required_inputs_by_target_type = None):
		assert(ctx)
		BuildSource.__init__(self, on_use_variables = on_use_variables)
		self.rules = none_to_obj(rules, [])
		self.target_types_by_ext = none_to_obj(target_types_by_ext, {})
		self.required_inputs_by_target_type = none_to_obj(required_inputs_by_target_type, {})

	def _check_version(self, version_req, version_str):
		self.version = Version(version_str)
		if version_req and not version_req(self.version):
			raise VersionError('Unable to find correct version!')

External.available = {}


class External_linker(External):
	def __init__(self, ctx,
			link_static, link_static_opts, link_static_def, link_static_opts_def,
			link_shared, link_shared_opts, link_shared_def, link_shared_opts_def,
			link_exe, link_exe_opts, link_exe_def, link_exe_opts_def):
		link_static = none_to_obj(link_static, link_static_def)
		link_static_opts = none_to_obj(link_static_opts, link_static_opts_def)
		link_shared = none_to_obj(link_shared, link_shared_def)
		link_shared_opts = none_to_obj(link_shared_opts, link_shared_opts_def)
		link_exe = none_to_obj(link_exe, link_exe_def)
		link_exe_opts = none_to_obj(link_exe_opts, link_exe_opts_def)
		External.__init__(self, ctx,
			rules = [
				Rule(('object', 'static'), 'link_static',
					'rm -f $out && $LINKER_STATIC $LINKER_STATIC_FLAGS ${opts} $out $in', 'link(static) $out',
					{'LINKER_STATIC': link_static, 'LINKER_STATIC_FLAGS': link_static_opts}),
				Rule(('object', 'shared'), 'link_shared',
					'$LINKER_SHARED $LINKER_SHARED_FLAGS ${opts} -o $out $in', 'link(shared) $out',
					{'LINKER_SHARED': link_shared, 'LINKER_SHARED_FLAGS': link_shared_opts}),
				Rule(('object', 'exe'), 'link_exe',
					'$LINKER_EXE $LINKER_EXE_FLAGS ${opts} -o $out $in', 'link(exe) $out',
					{'LINKER_EXE': link_exe, 'LINKER_EXE_FLAGS': link_exe_opts})])


class External_link_base(External_linker):
	def __init__(self, ctx, link_static = None, link_static_opts = None,
			link_shared = None, link_shared_opts = None,
			link_exe = None, link_exe_opts = None):
		External_linker.__init__(self, ctx,
			link_static = link_static, link_static_opts = link_static_opts,
			link_static_def = 'ar', link_static_opts_def = 'rcs',
			link_shared = link_shared, link_shared_opts = link_shared_opts,
			link_shared_def = 'ld', link_shared_opts_def = '-shared -fPIC',
			link_exe = link_exe, link_exe_opts = link_exe_opts,
			link_exe_def = 'ld', link_exe_opts_def = '')
External.available['link-base'] = External_link_base


class External_link_gcc(External_linker):
	def __init__(self, ctx, link_static = None, link_static_opts = None,
			link_shared = None, link_shared_opts = None,
			link_exe = None, link_exe_opts = None):
		External_linker.__init__(self, ctx,
			link_static = link_static, link_static_opts = link_static_opts,
			link_static_def = 'gcc-ar', link_static_opts_def = 'rcs',
			link_shared = link_shared, link_shared_opts = link_shared_opts,
			link_shared_def = 'gcc', link_shared_opts_def = '-shared -fPIC',
			link_exe = link_exe, link_exe_opts = link_exe_opts,
			link_exe_def = 'gcc', link_exe_opts_def = '')
External.available['link-gcc'] = External_link_gcc


class External_link_llvm(External_linker):
	def __init__(self, ctx, link_static = None, link_static_opts = None,
			link_shared = None, link_shared_opts = None,
			link_exe = None, link_exe_opts = None):
		External_linker.__init__(self, ctx,
			link_static = link_static, link_static_opts = link_static_opts,
			link_static_def = 'llvm-ar', link_static_opts_def = 'rcs',
			link_shared = link_shared, link_shared_opts = link_shared_opts,
			link_shared_def = 'clang', link_shared_opts_def = '-shared -fPIC',
			link_exe = link_exe, link_exe_opts = link_exe_opts,
			link_exe_def = 'clang', link_exe_opts_def = '')
External.available['link-llvm'] = External_link_llvm


class External_SimpleCompiler(External): # C family compiler
	std = property(lambda self: self._std, lambda self, value: self._set_std(value))

	def __init__(self, ctx, lang, std, compiler, compiler_opts, var_prefix, ext_list, req_input = None):
		self._std = None
		self._var_prefix = var_prefix
		self._compiler_opts = compiler_opts
		self._compiler_variables = {var_prefix: compiler, var_prefix + '_FLAGS': self._compiler_opts}
		required_inputs_by_target_type = {
			'shared': [RuleVariables({'compile_' + lang: {'opts': ['-fPIC']}})],
		}
		if req_input:
			for target_type in req_input:
				required_inputs_by_target_type.setdefault(target_type, []).extend(req_input[target_type])
		External.__init__(self, ctx, rules = [
				Rule((lang, 'object'), 'compile_' + lang,
					'$%s $%s_FLAGS ${opts} -MMD -MT $out -MF $out.d -c $in -o $out' % (var_prefix, var_prefix),
					'compile(%s) $out' % lang, self._compiler_variables,
					depfile = '$out.d', deps = 'gcc'),
				Rule((lang, 'exe'), 'compile_link_exe_' + lang,
					'$%s $%s_FLAGS ${opts} -MMD -MT $out -MF $out.d $in -o $out' % (var_prefix, var_prefix),
					'compile+link(%s) $out' % lang, self._compiler_variables,
					depfile = '$out.d', deps = 'gcc'),
				Rule((lang, 'shared'), 'compile_link_shared_' + lang,
					'$%s $%s_FLAGS ${opts} -shared -fPIC -MMD -MT $out -MF $out.d $in -o $out' % (var_prefix, var_prefix),
					'compile+link(%s) $out' % lang, self._compiler_variables,
					depfile = '$out.d', deps = 'gcc'),
			],
			target_types_by_ext = dict.fromkeys(ext_list, lang),
			required_inputs_by_target_type = required_inputs_by_target_type)
		self._set_std(std)

	def get_latest(self):
		raise Exception('Unable to find latest language standard!')

	def _set_std(self, value):
		if value == 'latest':
			value = self.get_latest()
		self._std = value
		if not value:
			opts = self._compiler_opts
		else:
			opts = ('-std=%s ' % value) + self._compiler_opts
		self._compiler_variables[self._var_prefix + '_FLAGS'] = opts


class External_gcc(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = none_to_obj(compiler, 'gcc')
		compiler_opts = none_to_obj(compiler_opts, '-Wall -pedantic')
		ext_list = none_to_obj(ext_list, ['.c'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'compile_c',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'CC', ext_list = ext_list)
External.available['gcc'] = External_gcc


class External_gpp(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = none_to_obj(compiler, 'g++')
		compiler_opts = none_to_obj(compiler_opts, '-Wall -pedantic')
		ext_list = none_to_obj(ext_list, ['.cpp', '.cxx', '.cc'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'cpp',
			compiler = compiler, compiler_opts = compiler_opts,
			var_prefix = 'CXX', ext_list = ext_list, req_input = {
				'exe': [External_libstdcpp(ctx)], 'shared': [External_libstdcpp(ctx)],
				'static': [External_libstdcpp(ctx)]})

	def get_latest(self):
		if self.version < 4.3:
			return 'c++03'
		elif self.version < 4.7:
			return 'c++0x'
		elif self.version < 4.8:
			return 'c++11'
		elif self.version < 5.0:
			return 'c++14'
		return 'c++1z'
External.available['g++'] = External_gpp
External.available['gpp'] = External_gpp


class External_gfortran(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = none_to_obj(compiler, 'gfortran')
		compiler_opts = none_to_obj(compiler_opts, '-Wall')
		ext_list = none_to_obj(ext_list, ['.f'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'fortran',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'F', ext_list = ext_list)
External.available['gfortran'] = External_gfortran


class External_clang(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = none_to_obj(compiler, 'clang')
		compiler_opts = none_to_obj(compiler_opts, '-Weverything -Wno-padded')
		ext_list = none_to_obj(ext_list, ['.c'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[2])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'compile_c',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'CC', ext_list = ext_list)
External.available['clang'] = External_clang


class External_clangpp(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = none_to_obj(compiler, 'clang++')
		compiler_opts = none_to_obj(compiler_opts, '-Weverything -Wno-padded')
		ext_list = none_to_obj(ext_list, ['.cpp', '.cxx', '.cc'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[2])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'cpp',
			compiler = compiler, compiler_opts = compiler_opts,
			var_prefix = 'CXX', ext_list = ext_list, req_input = {
				'exe': [External_libstdcpp(ctx)], 'shared': [External_libstdcpp(ctx)],
				'static': [External_libstdcpp(ctx)]})

	def get_latest(self):
		if self.version >= 3.5:
			return 'c++1z'
		elif self.version >= 3.4:
			return 'c++14'
		elif self.version >= 3.3:
			return 'c++11'
External.available['clang++'] = External_clangpp
External.available['clangpp'] = External_clangpp


class External_SWIG(External):
	def __init__(self, ctx, version = None):
		version_str = ''
		for version_line in run_process(['swig', '-version'])[0].splitlines():
			if 'version' in version_line.lower():
				version_str = version_line.split()[-1]
				break
		self._check_version(version, version_str)
		External.__init__(self, ctx)
		self._ctx = ctx

	def wrapper(self, lang, name, ifile, libs = None, swig_opts = None, context = None, **kwargs):
		if context is None:
			context = self._ctx
		wrapper_ext = context.find_external(lang)
		swig_rule = Rule(('swig', 'c++'), 'swig_cpp_%s' % lang,
			'swig -c++ -%s -I. ${opts} -module ${module_name} -o $out $in' % lang,
			'swig(C++ -> %s) $out' % lang, {})
		(src_name, ext) = get_normed_name(name, '.cpp')
		wrapper_src = BuildTarget(src_name, swig_rule,
			[InputFile(ifile)] + add_rule_vars(opts = swig_opts, module_name = name),
			on_use_inputs = {None: [SelfReference()]},
			on_use_variables = wrapper_ext.on_use_variables)
		return context.shared_library('_' + name, [wrapper_src, wrapper_ext] + none_to_obj(libs, []), **kwargs)
External.available['swig'] = External_SWIG


class SimpleExternal(External):
	def __init__(self, ctx, **kwargs):
		link_opts = kwargs.pop('link', [])
		if not isinstance(link_opts, list):
			link_opts = [link_opts]
		if link_opts:
			kwargs['link_static'] = link_opts
			kwargs['link_shared'] = link_opts
			kwargs['link_exe'] = link_opts
		on_use_variables = {}
		for rule_name, opts in kwargs.items():
			if not isinstance(opts, list):
				opts = [opts]
			on_use_variables.setdefault(rule_name, {})['opts'] = opts
		External.__init__(self, ctx, on_use_variables = on_use_variables)


class External_pthread(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link = '-pthread', compile_cpp = '-pthread')
External.available['pthread'] = External_pthread


class External_libstdcpp(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link_shared = '-lstdc++', link_exe = '-lstdc++')
External.available['libstdc++'] = External_libstdcpp
External.available['libstdcpp'] = External_libstdcpp


class External_libcpp(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link_shared = '-lc++', link_exe = '-lc++')
External.available['libc++'] = External_libcpp
External.available['libcpp'] = External_libcpp


class External_Python(SimpleExternal):
	def __init__(self, ctx, version = None, build_helper = 'python-config'):
		link_opts = run_process([build_helper, '--ldflags'])[0]
		python_lib = list(filter(lambda entry: entry.startswith('-lpython'), link_opts.split()))
		self._check_version(version, python_lib.pop().replace('-lpython', ''))
		SimpleExternal.__init__(self, ctx, link = link_opts,
			compile_cpp = run_process([build_helper, '--cflags'])[0])
External.available['python'] = External_Python


def create_build_helper_external(name, build_helper, **kwargs):
	version_query = kwargs.pop('version_query', None)
	version_parser = kwargs.pop('version_parser', None)
	if version_query:
		class TempExternal(SimpleExternal):
			def __init__(self, ctx, version = None):
				version_str = run_process([build_helper] + version_query.split())[0]
				if version_parser:
					version_str = version_parser(version_str)
				self._check_version(version, version_str)
				for rule_name in list(kwargs.keys()):
					kwargs[rule_name] = run_process([build_helper] + kwargs[rule_name].split())[0]
				SimpleExternal.__init__(self, ctx, **kwargs)
	else:
		class TempExternal(SimpleExternal):
			def __init__(self, ctx):
				for rule_name in list(kwargs.keys()):
					kwargs[rule_name] = run_process([build_helper] + kwargs[rule_name].split())[0]
				SimpleExternal.__init__(self, ctx, **kwargs)
	TempExternal.__name__ = 'External_' + name.replace('-', '_')
	External.available[name] = TempExternal
	return TempExternal


def define_pkg_config_external(name):
	return create_build_helper_external(name, 'pkg-config',
		version_query = '%s --modversion' % name,
		link = '%s --libs' % name, compile_cpp = '%s --cflags' % name)


def define_non_pkg_config_externals():
	for (tool, ldopt, cxxopt) in [
		('fltk-config',     '--ldflags', '--cxxflags'),
		('llvm-config',     '--libs',    '--cppflags'),
		('odbc_config',     '--libs',    '--cflags'),
		('root-config',     '--libs',    '--cflags'),
		('wx-config',       '--libs',    '--cxxflags'),
	]:
		create_build_helper_external(tool.split('-')[0].split('_')[0], tool,
			link = ldopt, compile_cpp = cxxopt, version_query = '--version',
			version_parser = lambda version_str: version_str.split()[-1])
define_non_pkg_config_externals()


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
		priority_targets = {}
		def update_target_hash_list(target, target_hash):
			if target.no_rename:
				priority_targets[target_hash] = target
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
		for target in self.target_list: # recurse to find all targets
			update_target_hash_list(target, target.get_hash())

		# identify targets with the same name but different configuration and
		# find all used rules (and their parameters)
		rules_used_variables = {}
		target_collisions = {}
		target_no_rename = set()
		for idx, (target, target_hash) in enumerate(target_hash_list):
			target = priority_targets.get(target_hash, target)
			target_hash_list[idx] = (target, target_hash)
			target_opts = target.get_build_variables().get('opts', '')
			rules_used_variables.setdefault(target.build_rule.get_hash(), {}).setdefault(target_opts, []).append(target)
			target_collisions.setdefault(target.name, []).append(target_hash)
			if target.no_rename:
				if target.name in target_no_rename:
					raise Exception('Multiple targets (%r) requested no renaming!' % target.name)
				target_no_rename.add(target.name)
		# rename colliding targets
		for target, target_hash in target_hash_list:
			target = priority_targets.get(target_hash, target)
			if (len(set(target_collisions.get(target.name, []))) != 1) and not target.no_rename:
				(root, ext) = os.path.splitext(target.name)
				target.name = root + '_' + target_hash + ext

		# identify rules with a fixed set of parameters to fold them into the rule definition
		for opts_of_targets in rules_used_variables.values():
			if len(opts_of_targets) == 1: # the rule 'rule_name' is always called with the same opts
				target_opts, targets = list(opts_of_targets.items())[0]
				if target_opts and (len(targets) > 1): # ignore if the rule is only called once anyway
					for target in targets:
						target.build_rule.cmd = target.build_rule.cmd.replace('${opts}', target_opts)
						target.build_rule.name += '_' + target.build_rule.get_hash()
						target.drop_build_opt()

		# Unify all rules with the same hash in rules_unique,
		# identify rules with different hashes and same name and rename collisions (in name / variable name)
		rules_unique = {}
		rules_collisions = {}
		rules_default_collisions = {}
		for target, target_hash in target_hash_list:
			rule_hash = target.build_rule.get_hash()
			target.build_rule = rules_unique.setdefault(rule_hash, target.build_rule)
			rules_collisions.setdefault(target.build_rule.name, []).append(rule_hash)
			for key, value in target.build_rule.defaults.items():
				rules_default_collisions.setdefault(key, {}).setdefault(value, []).append(target.build_rule)
		rules_default_rename = {}
		for key in rules_default_collisions:
			if len(rules_default_collisions[key]) != 1:
				for rules in rules_default_collisions[key].values():
					for rule in rules:
						rules_default_rename.setdefault(rule, set()).add(key)
		for rule in rules_default_rename:
			rule.defaults = dict(rule.defaults)
			for key in rules_default_rename[rule]:
					key_new = key + '_' + calc_hash(rule.defaults[key])
					rule.cmd = rule.cmd.replace('$%s' % key, '$%s' % key_new).replace('${%s}' % key, '${%s}' % key_new)
					rule.defaults[key_new] = rule.defaults.pop(key)
		for rule_hash_list in rules_collisions.values():
			if len(set(rule_hash_list)) != 1:
				for rule_hash in rule_hash_list:
					rules_unique[rule_hash].name += '_' + target.build_rule.get_hash()

		write_rules = sorted(rules_unique.values(), key = lambda r: r.name)
		write_targets = list(map(lambda t_th: t_th[0], target_hash_list))
		return (write_rules, write_targets)


class Platform(object):
	def __init__(self):
		self.extensions = {'object': '.o', 'shared': '.so', 'static': '.a', 'exe': ''}

	def get_required_inputs(self, target_type, compiler_dict):
		result = []
		for lang, compiler in sorted(compiler_dict.items()):
			result.extend(compiler.required_inputs_by_target_type.get(target_type, []))
		return result


class Context(object):
	targets = []

	def __init__(self, registry, platform, tools,
			implicit_input = None,
			implicit_object_input = None,
			implicit_static_library_input = None,
			implicit_shared_library_input = None,
			implicit_executable_input = None,
			basedir = None,
			basedir_object_file = None,
			basedir_static_library = None,
			basedir_shared_library = None,
			basedir_executable = None):
		(self.registry, self.platform, self.tools, self.toolchain) = (registry, platform, tools, tools.toolchain)
		self.basedir = basedir
		self.basedir_object_file = basedir_object_file
		self.basedir_static_library = basedir_static_library
		self.basedir_shared_libray = basedir_shared_library
		self.basedir_executable = basedir_executable
		self.implicit_input = implicit_input
		self.implicit_object_input = implicit_object_input
		self.implicit_static_library_input = implicit_static_library_input
		self.implicit_shared_library_input = implicit_shared_library_input
		self.implicit_executable_input = implicit_executable_input

	def get_basedir(self, basedir):
		if basedir:
			return basedir
		elif self.basedir:
			return self.basedir
		return ''

	def get_implicit_input(self, implicit_input):
		return none_to_obj(implicit_input, []) + none_to_obj(self.implicit_input, [])

	def find_toolchain(self, value, *args, **kwargs):
		value == value.lower()
		if value not in Toolchain.available:
			raise Exception('Unknown toolchain %r' % value)
		return Toolchain.available[value](self, *args, **kwargs)

	def use_toolchain(self, value, *args, **kwargs):
		tc = self.find_toolchain(value, *args, **kwargs)
		if tc:
			self.tools.toolchain.append(tc)

	def find_external(self, name, *args, **kwargs):
		name == name.lower()
		if name not in External.available and not define_pkg_config_external(name):
			raise Exception('Unknown external %r' % name)
		try:
			return External.available[name](self, *args, **kwargs)
		except ProcessError:
			sys.stderr.write('Unable to find external %s\n' % name)
		except VersionError as e:
			sys.stderr.write('VersionError(%s): %s\n' % (name, e.args[0]))

	def use_external(self, name, *args, **kwargs):
		ext = self.find_external(name, *args, **kwargs)
		if ext:
			self.implicit_input = none_to_obj(self.implicit_input, [])
			self.implicit_input.append(ext)

	def create_external(self, name, *args, **kwargs):
		version = kwargs.pop('version', None)
		external = create_build_helper_external(name, **kwargs)
		kwargs_external = {}
		if version and ('version_query' in kwargs):
			kwargs_external['version'] = version
		return self.find_external(name, *args, **kwargs_external)

	def find_rule(self, ttfrom, ttto): # return a new instance going from target type (from -> to)
		for lang, tool in sorted(self.tools.items()):
			for r in tool.rules:
				if r.connection == (ttfrom, ttto):
					return Rule(r.connection, r.name, r.cmd, r.desc, r.defaults, **dict(r.params))
		raise Exception('build rule translating %s -> %s not found!' % (ttfrom, ttto))

	def find_target_types(self, obj):
		result = set()
		if hasattr(obj, 'name'):
			ext = os.path.splitext(obj.name)[1].lower()
			for lang, tool in sorted(self.tools.items()):
				if ext in tool.target_types_by_ext:
					result.add(tool.target_types_by_ext[ext])
		return result

	def force_build_source(self, input_list):
		input_list = none_to_obj(input_list, [])
		if isinstance(input_list, str): # support accepting user supplied space separated string
			input_list = input_list.split()
		def translate_str(value):
			if isinstance(value, str):
				return InputFile(value)
			return value
		return list(map(translate_str, input_list))

	def create_target(self, target_name, rule, input_list, add_self_to_on_use_inputs, **kwargs):
		on_use_inputs = kwargs.pop('on_use_inputs', {})
		if add_self_to_on_use_inputs:
			on_use_inputs.setdefault(None, []).append(SelfReference())
		target = BuildTarget(target_name, rule, input_list, on_use_inputs = on_use_inputs, **kwargs)
		return self.registry.register_target(target)

	def object_file(self, obj_name, input_list = None, compiler_opts = None, **kwargs):
		input_list = self.force_build_source(input_list)
		# collect rules from the input object extensions
		target_types = set()
		for target_types_new in map(self.find_target_types, input_list):
			target_types.update(target_types_new)
		if len(target_types) != 1:
			raise Exception('Unable to find unique handler (%s) to generate %s' % (repr(target_types), obj_name))
		obj_name = os.path.join(self.get_basedir(self.basedir_object_file), obj_name)
		(obj_name, obj_name_ext) = get_normed_name(obj_name, self.platform.extensions['object'])
		return self.create_target(obj_name, rule = self.find_rule(target_types.pop(), 'object'),
			input_list = self.get_implicit_input(self.implicit_object_input) + input_list + add_rule_vars(opts = compiler_opts),
			add_self_to_on_use_inputs = True, **kwargs)

	def link(self, output_name, target_type, input_list, implicit_input_list,
			add_self_to_on_use_inputs, link_mode = 'single', **kwargs):
		input_list = self.force_build_source(input_list)
		input_list.extend(self.platform.get_required_inputs(target_type, self.tools))
		object_input = []
		link_input = []
		inputs_by_target_type = {}
		for obj in input_list:
			target_types = self.find_target_types(obj)
			if len(target_types) == 1:
				inputs_by_target_type.setdefault(target_types.pop(), []).append(obj)
			elif not target_types: # nothing to compile in any way
				if not isinstance(obj, BuildTarget):
					object_input.append(obj)
				link_input.append(obj)
			else:
				raise Exception('Found multiple rules (%s) to generate object from %s' % (repr(target_types), repr(obj)))

		input_list_new = list(self.get_implicit_input(implicit_input_list))
		input_list_new.extend(add_rule_vars(opts = kwargs.pop('linker_opts', None)))

		compiler_opts = kwargs.pop('compiler_opts', None)
		if (link_mode == 'direct') and (len(inputs_by_target_type) == 1):
			(input_target_type, input_list) = inputs_by_target_type.popitem()
			rule = self.find_rule(input_target_type, target_type)
			input_list_new.extend(self.get_implicit_input(self.implicit_object_input))
			input_list_new.extend(input_list + object_input + add_rule_vars(opts = compiler_opts))
		else:
			for (input_target_type, input_list) in inputs_by_target_type.items():
				if link_mode == 'single':
					for obj in input_list:
						input_list_new.append(self.object_file(obj.name, compiler_opts = compiler_opts,
							input_list = self.get_implicit_input(self.implicit_object_input) + [obj] + object_input))
				else:
					input_list_new.append(self.object_file(obj.name, compiler_opts = compiler_opts,
						input_list = self.get_implicit_input(self.implicit_object_input) + input_list + object_input))
			rule = self.find_rule('object', target_type)

		target = self.create_target(output_name, rule = rule,
			input_list = input_list_new + link_input,
			add_self_to_on_use_inputs = add_self_to_on_use_inputs, **kwargs)
		Context.targets.append(target)
		return target

	def shared_library(self, lib_name, input_list, **kwargs):
		lib_name = os.path.join(self.get_basedir(self.basedir_shared_libray), lib_name)
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['shared'])
		link_name = lib_name.replace(self.platform.extensions['shared'], '')
		if lib_name.startswith('lib'):
			link_name = link_name[3:]
		on_use_variables = kwargs.pop('on_use_variables', {})
		on_use_variables.setdefault(None, {}).setdefault('opts', [])
		on_use_variables[None]['opts'] += ['-L.', '-l%s' % link_name]
		on_use_deps = kwargs.pop('on_use_deps', {})
		on_use_deps.setdefault(None, []).append(SelfReference())
		return self.link(lib_name, target_type = 'shared', 
			input_list = input_list, add_self_to_on_use_inputs = False,
			implicit_input_list = self.get_implicit_input(self.implicit_shared_library_input),
			on_use_deps = on_use_deps, on_use_variables = on_use_variables, **kwargs)

	def static_library(self, lib_name, input_list, **kwargs):
		lib_name = os.path.join(self.get_basedir(self.basedir_static_library), lib_name)
		(lib_name, ext) = get_normed_name(lib_name, self.platform.extensions['static'])
		return self.link(lib_name, target_type = 'static',
			input_list = input_list, add_self_to_on_use_inputs = True,
			implicit_input_list = self.get_implicit_input(self.implicit_static_library_input), **kwargs)

	def executable(self, exe_name, input_list, **kwargs):
		exe_name = os.path.join(self.get_basedir(self.basedir_executable), exe_name)
		if not exe_name.endswith(self.platform.extensions['exe']):
			exe_name += self.platform.extensions['exe']
		return self.link(exe_name, target_type = 'exe',
			input_list = input_list, add_self_to_on_use_inputs = False,
			implicit_input_list = self.get_implicit_input(self.implicit_executable_input), **kwargs)


def create_ctx(ctx, **kwargs):
	platform = kwargs.pop('platform', ctx.platform)
	tools = kwargs.pop('tools', ctx.tools.copy())
	tools.toolchain = kwargs.pop('toolchain', list(ctx.tools.toolchain))
	return Context(ctx.registry, platform, tools, **kwargs)


def default_ctx_call(exec_dict, fun, keyword_only = False):
	if keyword_only:
		return lambda **kwargs: fun(exec_dict['default_context'], **kwargs)
	return lambda *args, **kwargs: fun(exec_dict['default_context'], *args, **kwargs)


def create_registered(registry, cls):
	def create_registered_cls(*args, **kwargs):
		target = cls(*args, **kwargs)
		return registry.register_target(target)
	return create_registered_cls


class ToolHolder(object):
	def __init__(self, toolchain, tools):
		self._tools = tools
		self.toolchain = toolchain
	def copy(self):
		return ToolHolder(list(self.toolchain), dict(self._tools))
	def _update(self):
		for tc in reversed(self.toolchain):
			for toolname, toolfactory in tc.tools.items():
				if toolfactory and isinstance(self._tools.get(toolname), (type(None), Delayed)):
					try:
						tool_instance = toolfactory.get_instance()
					except Exception:
						tool_instance = None
					if tool_instance:
						self._tools[toolname] = tool_instance
	def __repr__(self):
		self._update()
		return 'Tools(%s)' % repr(self._tools)
	def __getitem__(self, key):
		self._update()
		return self._tools.__getitem__(key)
	def __setitem__(self, key, value):
		self._tools.__setitem__(key, value)
	def __delitem__(self, key):
		self._update()
		self._tools.__delitem__(key)
	def __iter__(self):
		self._update()
		return iter(self._tools)
	def __len__(self):
		self._update()
		return len(self._tools)
	def items(self):
		self._update()
		return self._tools.items()


class Toolchain(object):
	def __init__(self, ctx):
		self._ctx = ctx
		self.tools = {}

	def __repr__(self):
		return nice_repr(self, 14)
Toolchain.available = {}


class Toolchain_GCC(Toolchain):
	def __init__(self, ctx, version = None, c_std = None, c_opts = None, cpp_std = None, cpp_opts = None,
			fortran_std = None, fortran_opts = None, link_shared_opts = None, link_exe_opts = None):
		Toolchain.__init__(self, ctx)

		self.tools['linker'] = Delayed(External_link_gcc, ctx, link_shared_opts = link_shared_opts, link_exe_opts = link_exe_opts)
		self.tools['c'] = Delayed(External_gcc, ctx, version = version, std = c_std, compiler_opts = c_opts)
		self.tools['cpp'] = Delayed(External_gpp, ctx, version = version, std = cpp_std, compiler_opts = cpp_opts)
		self.tools['fortran'] = Delayed(External_gfortran, ctx, version = version, std = fortran_std, compiler_opts = fortran_opts)


class Toolchain_LLVM(Toolchain):
	def __init__(self, ctx, version = None, c_std = None, c_opts = None, cpp_std = None, cpp_opts = None,
			link_shared_opts = None, link_exe_opts = None):
		Toolchain.__init__(self, ctx)

		self.tools['linker'] = Delayed(External_link_llvm, ctx, link_shared_opts = link_shared_opts, link_exe_opts = link_exe_opts)
		self.tools['c'] = Delayed(External_clang, ctx, version = version, std = c_std, compiler_opts = c_opts)
		self.tools['cpp'] = Delayed(External_clangpp, ctx, version = version, std = cpp_std, compiler_opts = cpp_opts)
Toolchain.available['llvm'] = Toolchain_LLVM


def generate_build_file(bfn, ofn, mode):
	pyrate_version = Version(__version__)
	registry = Registry()
	platform = Platform()
	tools = ToolHolder([], {})
	ctx = Context(registry, platform, tools)
	ctx.tools.toolchain.append(Toolchain_GCC(ctx))

	exec_globals = {}
	exec_globals.update({
		# globals
		'default_context': ctx,
		'default_targets': None,
		'match': match,
		'pyrate_version': pyrate_version,
		'tools': tools,
		'toolchain': tools.toolchain,
		'version': VersionComparison(),
		# stable API
		'create_external': default_ctx_call(exec_globals, Context.create_external),
		'executable': default_ctx_call(exec_globals, Context.executable),
		'find_external': default_ctx_call(exec_globals, Context.find_external),
		'find_toolchain': default_ctx_call(exec_globals, Context.find_toolchain),
		'object_file': default_ctx_call(exec_globals, Context.object_file),
		'shared_library': default_ctx_call(exec_globals, Context.shared_library),
		'static_library': default_ctx_call(exec_globals, Context.static_library),
		'use_external': default_ctx_call(exec_globals, Context.use_external),
		'use_toolchain': default_ctx_call(exec_globals, Context.use_toolchain),
		# development API
		'BuildSource': BuildSource,
		'BuildTarget': create_registered(registry, BuildTarget),
		'BuildTargetFree': BuildTarget,
		'Context': default_ctx_call(exec_globals, create_ctx),
		'External': default_ctx_call(exec_globals, External, keyword_only = True),
		'InputFile': InputFile,
		'Rule': Rule,
		'find_rule': default_ctx_call(exec_globals, Context.find_rule),
	})
	if mode:
		exec_globals['build_system'] = 'makefile'
	else:
		exec_globals['build_system'] = 'ninja'

	with open(bfn) as bfp:
		exec(bfp.read(), exec_globals)

	(rules, targets) = registry.write()
	if exec_globals['build_system'] == 'makefile':
		writer = MakefileWriter(ofn.replace('build.ninja', 'Makefile'))
	else:
		writer = NinjaBuildFileWriter(ofn)
	list(map(writer.write_rule, rules))
	list(map(writer.write_target, targets))
	default_targets = exec_globals['default_targets']
	if default_targets and not isinstance(default_targets, (tuple, list)):
		default_targets = [default_targets]
	writer.set_default(default_targets, Context.targets)

def main():
	def parse_arguments():
		version_info = 'pyrate version ' + __version__
		try:
			if os.environ.get('PYTHONOPTPARSE'):
				raise ImportError()
			import argparse
			parser = argparse.ArgumentParser()
			parser.add_argument('build_file', nargs = '?', default = 'build.py',
				help = 'name of the input file - default: build.py')
			parser.add_argument('-V', '--version', action = 'version', version = version_info)
			parser.add_argument('-M', '--makefile', action = 'store_true', help = 'enable makefile mode')
			parser.add_argument('-o', '--output', nargs = 1, default = ['build.ninja'],
				help = 'name of output build file')
			args = parser.parse_args()
			return ([args.build_file], args.output[0], args.makefile)
		except ImportError:
			import optparse
			parser = optparse.OptionParser(usage = 'pyrate [options] build_file')
			parser.add_option('-V', '--version', action='store_true', help = 'display version')
			parser.add_option('-M', '--makefile', action = 'store_true', help = 'enable makefile mode')
			parser.add_option('-o', '--output', default = 'build.ninja',
				help = 'name of output build file', dest='output')
			(args, posargs) = parser.parse_args()
			if args.version:
				sys.stderr.write(version_info + '\n')
				sys.exit(os.EX_OK)
			return (posargs, args.output, args.makefile)
	(bfn_list, ofn, mode) = parse_arguments()
	if not bfn_list:
		bfn = 'build.py'
	elif len(bfn_list) == 1:
		bfn = bfn_list[0]
	else:
		sys.stderr.write('too many build_file arguments provided! %s\n' % repr(bfn_list))
		return os.EX_USAGE

	if os.path.dirname(bfn):
		os.chdir(os.path.dirname(bfn))
	generate_build_file(os.path.basename(bfn), ofn, mode)

if __name__ == '__main__':
	sys.exit(main())
