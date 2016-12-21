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

__version__ = '0.2.10'

import os, sys
try:
	if os.environ.get('TESTOLDIMPORTS'):
		raise ImportError()
	import hashlib
	def calc_hash(value):
		return hashlib.md5(repr(value).encode('ascii')).hexdigest()
except ImportError:
	def calc_hash(value):
		return __import__('md5').md5(repr(value)).hexdigest()


def ensure_list(value):
	if isinstance(value, (list, tuple)):
		return list(value)
	elif value:
		return [value]


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


def match(value, dn, recurse):
	import fnmatch
	result = []
	if recurse:
		walk_entries = os.walk(dn)
	else:
		walk_entries = [(dn, [], os.listdir(dn))]
	for walk_result in walk_entries:
		for fn in walk_result[2]:
			fn = os.path.relpath(os.path.join(walk_result[0], fn), dn)
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


class SelfReference(object):
	def __init__(self, ref = None):
		self._ref = ref


class Rule(object):
	def __init__(self, connection, name, cmd, desc, defaults,
			target_on_use_inputs = None, target_on_use_deps = None, target_on_use_variables = None, **kwargs):
		# persistent values
		(self.name, self.cmd, self.desc, self.defaults, self.params) = (name, cmd, desc, defaults, sorted(kwargs.items()))
		# transient values used to help build system
		(self.connection, self.target_on_use_inputs, self.target_on_use_deps, self.target_on_use_variables) =\
			(connection, target_on_use_inputs, target_on_use_deps, target_on_use_variables)

	def get_hash(self):
		return calc_hash([self.name, self.cmd, self.desc, sorted(self.defaults.items()), self.params])

	def clone(self):
		return Rule(self.connection, self.name, self.cmd, self.desc, self.defaults,
			self.target_on_use_inputs, self.target_on_use_deps, self.target_on_use_variables, **dict(self.params))

	def __str__(self):
		return nice_repr(self, 8)

	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, repr(self.name))

phony_rule = Rule((None, None), 'phony', '', '', {})

class BuildSource(object):
	def __init__(self, on_use_inputs = None, on_use_deps = None, on_use_variables = None):
		self.on_use_inputs = self._resolve_self(on_use_inputs)
		self.on_use_deps = self._resolve_self(on_use_deps)
		self.on_use_variables = dict(on_use_variables or {})

	def _resolve_self(self, on_use_dict):
		on_use_dict = on_use_dict or {}
		result = {}
		for key, value_list in on_use_dict.items():
			for value in value_list:
				if isinstance(value, SelfReference):
					value = self
				result.setdefault(key, []).append(value)
		return result

	def get_hash(self):
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
		return calc_hash(hash_tmp + sorted(self.on_use_variables.items()))

	def __str__(self):
		return nice_repr(self, 14)


class InputFile(BuildSource):
	def __init__(self, name, rule_list = None):
		self.name = name
		rule_list = ensure_list(rule_list or [None])
		BuildSource.__init__(self, on_use_inputs = dict.fromkeys(rule_list, [self]))

	def __repr__(self):
		return '%s(name = %s, on_use_inputs = {None: [self]})' % (self.__class__.__name__, repr(self.name))


class TargetAlias(BuildSource):
	def __init__(self, target):
		self.target = target
		BuildSource.__init__(self, on_use_inputs = {None: [target]})

	def __repr__(self):
		return '%s(target = %s)' % (self.__class__.__name__, repr(self.target))


class RuleVariables(BuildSource):
	def __init__(self, on_use_variables):
		BuildSource.__init__(self, on_use_variables = on_use_variables)

	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, self.on_use_variables)


def add_rule_vars(**kwargs):
	variables = {}
	for key, value in kwargs.items():
		if value:
			variables.setdefault(key, []).extend(ensure_list(value))
	if variables:
		return [RuleVariables(on_use_variables = {None: variables})]
	return []


class BuildTarget(BuildSource):
	def __init__(self, build_name, build_rule, build_src,
			on_use_inputs = None, on_use_deps = None, on_use_variables = None,
			target_type = None, no_rename = False, install_name = None, user_name = None):
		BuildSource.__init__(self, on_use_inputs, on_use_deps, on_use_variables)
		(self.name, self.install_name, self.user_name) = (build_name, install_name, user_name)
		(self.build_rule, self.build_src) = (build_rule, build_src)
		(self.target_type, self.no_rename) = (target_type, no_rename)
		self._drop_opt = False

	def get_hash(self):
		return calc_hash([self.name, self.build_rule.get_hash(),
			sorted(map(lambda t: t.get_hash(), self.get_build_inputs())),
			sorted(map(lambda t: t.get_hash(), self.get_build_deps())),
			sorted(self.get_build_variables().items())])

	def _get_build(self, src_getter, default, combine):
		result = default()
		for entry in self.build_src:
			src_dict = src_getter(entry)
			found = False
			for key, value in src_dict.items():
				if key and (key in self.build_rule.name):
					combine(result, value)
					found = True
					break
			if not found:
				combine(result, src_dict.get(None, default()))
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
				for value in (values or []):
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

	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, repr(self.name))


def get_normed_name(fn, forced_ext):
	return os.path.splitext(fn)[0] + forced_ext


class Registry(object):
	def __init__(self):
		self.target_list = []
		self.rename_all_targets = False
		self.rename_all_constants = False
		self.rename_all_rules = False
		self.fold_target_opts = True

	def register_target(self, target):
		assert(isinstance(target, BuildTarget))
		self.target_list.append(target)
		return target

	def _collect_target_infos(self):
		# collect information about target infos
		# and deduplicate targets in target_list (and recursively in build_src) based on hash
		target_by_thash = {}
		target_order = []
		targets_by_topts_by_rhash = {}
		thashs_by_name = {}
		thashs_no_rename = set()
		def update_target_hash_list(target, target_hash):
			known_target = target_by_thash.get(target_hash)
			if target.no_rename:
				thashs_no_rename.add(target_hash)
			if known_target and target.no_rename:
				known_target.no_rename = True # mark no_rename target
			if not known_target:
				target_order.append(target)
				target_by_thash[target_hash] = target

				rhash = target.build_rule.get_hash()
				topts = target.get_build_variables().get('opts', '')
				targets_by_topts_by_rhash.setdefault(rhash, {}).setdefault(topts, set()).add(target)
				thashs_by_name.setdefault(target.name, set()).add(target_hash)

				# recurse into sources of target
				for idx, src in enumerate(target.build_src):
					if isinstance(src, BuildTarget):
						src_hash = src.get_hash()
						update_target_hash_list(src, src_hash)
						target.build_src[idx] = target_by_thash[src_hash]
		for target in self.target_list: # recurse to find all targets
			update_target_hash_list(target, target.get_hash())
		return (target_by_thash, thashs_by_name, thashs_no_rename, targets_by_topts_by_rhash, target_order)

	def _rename_targets(self, target_by_thash, thashs_by_name, thashs_no_rename):
		# rename targets with different hashs and same name - except no_rename was set
		for thash_list_same_names in thashs_by_name.values():
			if (len(thash_list_same_names) < 2) and not self.rename_all_targets:
				continue
			blocked_rename = False
			for thash in thash_list_same_names:
				target = target_by_thash[thash]
				if thash in thashs_no_rename:
					if blocked_rename:
						raise Exception('Multiple targets (%r) requested no renaming!' % target.name)
					blocked_rename = True
					continue
				(root, ext) = os.path.splitext(target.name)
				target.name = root + '_' + thash + ext
		# thash invalidated by rename
		target_by_thash.clear()
		thashs_by_name.clear()
		thashs_no_rename.clear()

	def _fold_target_opts(self, targets_by_topts_by_rhash):
		# identify rules with a fixed set of parameters to fold them into the rule definition
		for targets_by_topts in targets_by_topts_by_rhash.values():
			if (len(targets_by_topts) > 1) or not self.fold_target_opts: # the rule 'rule_name' is called with the different opts
				continue
			for (topts, target_set) in targets_by_topts.items():
				if not topts or (len(target_set) < 2): # ignore if the rule is only called once anyway or opts is empty
					continue
				for target in target_set:
					target.build_rule.cmd = target.build_rule.cmd.replace('${opts}', topts)
					if not self.rename_all_rules: # otherwise it will be done later
						target.build_rule.name += '_' + target.build_rule.get_hash()
					target.drop_build_opt()
		targets_by_topts_by_rhash.clear() # rhash invalidated by folding

	def _process_rules(self, target_list):
		rule_order = []
		rule_by_rhash = {}
		rules_by_rvalues_by_rkeys = {}
		for target in target_list:
			rhash = target.build_rule.get_hash()
			known_rule = rule_by_rhash.get(rhash)
			if not known_rule:
				known_rule = target.build_rule
				rule_by_rhash[rhash] = known_rule
				rule_order.append(known_rule)
			target.build_rule = known_rule
			known_rule.defaults = dict(known_rule.defaults)
			for key, value in known_rule.defaults.items():
				rules_by_rvalues_by_rkeys.setdefault(key, {}).setdefault(value, set()).add(known_rule)

		self._rename_rule_constants(rules_by_rvalues_by_rkeys)
		self._rename_rule_names(rule_order)
		return rule_order

	def _rename_rule_constants(self, rules_by_rvalues_by_rkeys):
		for rkey in rules_by_rvalues_by_rkeys:
			if (len(rules_by_rvalues_by_rkeys[rkey]) < 2) and not self.rename_all_constants:
				continue
			for rule_list in rules_by_rvalues_by_rkeys[rkey].values():
				for rule in rule_list:
					rkey_new = rkey + '_' + calc_hash(rule.defaults[rkey])
					rule.cmd = rule.cmd.replace('$%s' % rkey, '$%s' % rkey_new).replace('${%s}' % rkey, '${%s}' % rkey_new)
					rule.defaults[rkey_new] = rule.defaults.pop(rkey)
		rules_by_rvalues_by_rkeys.clear() # invalidated by rkey rename

	def _rename_rule_names(self, rule_order):
		# this catches rules with same names and different commands (unlikely but possible)
		rule_by_rhash = {}
		rhashs_by_name = {}
		for rule in rule_order:
			rhash = rule.get_hash()
			rule_by_rhash[rhash] = rule
			rhashs_by_name.setdefault(rule.name, set()).add(rhash)
		for rhash_set in rhashs_by_name.values():
			if (len(rhash_set) > 1) or self.rename_all_rules:
				for rhash in rhash_set:
					rule_by_rhash[rhash].name += '_' + rhash

	def write(self):
		(target_by_thash, thashs_by_name, thashs_no_rename, targets_by_topts_by_rhash, target_order) =\
			self._collect_target_infos()
		self._rename_targets(target_by_thash, thashs_by_name, thashs_no_rename)
		self._fold_target_opts(targets_by_topts_by_rhash)
		rule_order = self._process_rules(target_order)
		return (sorted(rule_order, key = lambda r: r.name), target_order)


class Context(object):
	targets = []
	install_targets = []

	def __init__(self, registry, platform, tools, prefix, prefix_mode, # pylint:disable=too-many-locals
			implicit_input = None,
			implicit_object_input = None,
			implicit_static_library_input = None,
			implicit_shared_library_input = None,
			implicit_executable_input = None,
			basepath = None,
			basepath_object_file = None,
			basepath_static_library = None,
			basepath_shared_library = None,
			basepath_executable = None):
		# set parameters that are not available to user in constructor
		self._set_fixed(registry, platform, tools, prefix, prefix_mode)
		self.basepath = basepath
		self.basepath_object_file = basepath_object_file
		self.basepath_static_library = basepath_static_library
		self.basepath_shared_library = basepath_shared_library
		self.basepath_executable = basepath_executable
		self.implicit_input = implicit_input
		self.implicit_object_input = implicit_object_input
		self.implicit_static_library_input = implicit_static_library_input
		self.implicit_shared_library_input = implicit_shared_library_input
		self.implicit_executable_input = implicit_executable_input

	def _set_fixed(self, registry, platform, tools, prefix, prefix_mode):
		(self.registry, self.platform) = (registry, platform)
		(self.tools, self.toolchain) = (tools, tools.toolchain)
		(self.prefix, self.prefix_mode) = (prefix, prefix_mode)
		self._tracker = []

	def match(self, value, dn = '.', recurse = False):
		return match(value = value, dn = os.path.join(self.prefix, dn), recurse = recurse)

	def match_libs(self, dn = '.', recurse = False, lib_types = None):
		result = []
		for lib_type in (lib_types or ['shared', 'static']):
			for fn in self.match('*%s' % self.platform.extensions[lib_type], dn = dn, recurse = recurse):
				if lib_type == 'shared':
					result.append(self.shared_library(os.path.join(dn, fn)))
				elif lib_type == 'static':
					result.append(self.static_library(os.path.join(dn, fn)))
		return result

	def get_basepath(self, basepath):
		def pathjoin(value):
			if self.prefix_mode and (self.prefix_mode.lower() == 'front'):
				return os.path.join(self.prefix, value)
			return os.path.join(value, self.prefix)
		if basepath:
			return pathjoin(basepath)
		elif self.basepath:
			return pathjoin(self.basepath)
		return self.prefix

	def get_implicit_input(self, implicit_input):
		return (implicit_input or []) + (self.implicit_input or [])

	def find_toolchain(self, name, *args, **kwargs):
		name = name.lower()
		if name not in Toolchain.available:
			sys.stderr.write('Unknown toolchain %r\n' % name)
			return
		return Toolchain.available[name](self, *args, **kwargs)

	def use_toolchain(self, name, *args, **kwargs):
		tc = self.find_toolchain(name, *args, **kwargs)
		if tc:
			self.tools.toolchain.append(tc)

	def find_internal(self, name):
		result = set()
		for obj in Context.targets + self.registry.target_list:
			if name in [obj.name, obj.install_name, obj.user_name]:
				result.add(obj)
		if len(result) == 1:
			return result.pop()
		elif len(result) > 1:
			raise Exception('Multiple matches found for %s: %s', repr(name), repr(result))

	def find_external(self, name, *args, **kwargs):
		name = name.lower()
		version_parser = kwargs.pop('version_parser', None)
		if name not in External.available and not define_pkg_config_external(name, version_parser):
			sys.stderr.write('Unknown external %r\n' % name)
			return
		try:
			return External.available[name](self, *args, **kwargs)
		except ProcessError:
			sys.stderr.write('Unable to find external %s\n' % name)
		except VersionError as e:
			sys.stderr.write('VersionError(%s): %s\n' % (name, e.args[0]))

	def use_external(self, name, *args, **kwargs):
		ext = self.find_external(name, *args, **kwargs)
		if ext:
			self.implicit_input = (self.implicit_input or [])
			self.implicit_input.append(ext)

	def create_external(self, name, *args, **kwargs):
		version = kwargs.pop('version', None)
		create_build_helper_external(name, **kwargs)
		kwargs_external = {}
		if version and ('version_query' in kwargs):
			kwargs_external['version'] = version
		return self.find_external(name, *args, **kwargs_external)

	def find_rule(self, ttfrom, ttto): # return a new instance going from target type (from -> to)
		for tool in self.tools.get_tools():
			for rule in tool.rules:
				if rule.connection == (ttfrom, ttto):
					return rule.clone()
		for rule in self.platform.rules:
			if rule.connection == (ttfrom, ttto):
				return rule.clone()
		raise Exception('build rule translating %s -> %s not found!' % (ttfrom, ttto))

	def find_target_type(self, obj):
		result = set()
		if hasattr(obj, 'target_type') and obj.target_type:
			result.add(obj.target_type)
		elif hasattr(obj, 'name'):
			ext = os.path.splitext(obj.name)[1].lower()
			for tool in self.tools.get_tools():
				if ext in tool.target_types_by_ext:
					result.add(tool.target_types_by_ext[ext])
		if len(result) > 1:
			raise Exception('Multiple target types (%s) found for %s.' % (repr(result), repr(obj)) +
				'Please set target_type property manually!')
		elif result:
			return result.pop()

	def create_target(self, target_name, rule, input_list, add_self_to_on_use_inputs = False, **kwargs):
		on_use_inputs = kwargs.pop('on_use_inputs', {})
		if add_self_to_on_use_inputs:
			on_use_inputs.setdefault(None, []).append(SelfReference())
		target = BuildTarget(target_name, rule, input_list, on_use_inputs = on_use_inputs, **kwargs)
		return self.registry.register_target(target)

	def force_build_source(self, input_list_raw):
		input_list_raw = (input_list_raw or [])
		if isinstance(input_list_raw, str): # support accepting user supplied space separated string
			input_list_raw = input_list_raw.split()
		input_list = []
		for entry in ensure_list(input_list_raw):
			if entry is None:
				raise Exception('None found in input list!')
			input_list.extend(ensure_list(entry))
		def translate_str(value):
			if isinstance(value, str):
				return InputFile(os.path.join(self.prefix, value))
			return value
		return list(map(translate_str, input_list))

	def _collect_object_env(self, input_list):
		for obj in input_list:
			source_target_type = self.find_target_type(obj)
			if (not isinstance(obj, BuildTarget)) and (source_target_type is None):
				yield obj

	def _get_link_input_list(self, build_name, input_list, implicit_input_list, link_mode,
			linker_opts = None, compiler_opts = None):
		for obj in (implicit_input_list + add_rule_vars(opts = linker_opts)):
			yield obj
		for idx, obj in enumerate(input_list):
			source_target_type = self.find_target_type(obj)
			if source_target_type in ['object', 'shared', 'static']:
				yield obj
			elif source_target_type is not None:
				if link_mode == 'single':
					object_input_list = list(self.get_implicit_input(self.implicit_object_input))
					object_input_list.extend(self._collect_object_env(input_list[:idx]))
					object_input_list.append(obj)
					object_input_list.extend(self._collect_object_env(input_list[idx+1:]))
					yield self.object_file(os.path.relpath(obj.name, self.prefix),
						compiler_opts = compiler_opts, input_list = object_input_list)
				elif link_mode == 'direct':
					for obj_input in (self.get_implicit_input(self.implicit_object_input) + add_rule_vars(opts = compiler_opts)):
						yield obj_input
					link_mode = 'direct_obj' # object input is only added once in direct link_mode
				if link_mode == 'direct_obj':
					yield obj
			elif isinstance(obj, BuildSource) and not isinstance(obj, BuildTarget):
				yield obj
			else:
				raise Exception('%s: Unable to process input %s' % (build_name, repr(obj)))

	def link(self, build_name, target_type, input_list, implicit_input_list,
			add_self_to_on_use_inputs, link_mode = 'single', **kwargs):
		input_list = self.force_build_source(input_list)
		input_list.extend(self.platform.get_required_inputs(target_type, self.tools))
		# Discover source target types in input_list
		input_target_types = set()
		for input_target_type in map(self.find_target_type, input_list):
			if input_target_type:
				input_target_types.add(input_target_type)
		# Disable direct link_mode if multiple source types are present
		if (len(input_target_types) > 1) and (link_mode == 'direct'):
			link_mode = 'single' # multiple input targets
		# Find rule for direct
		if link_mode == 'single':
			rule = self.find_rule('object', target_type)
		elif link_mode == 'direct':
			rule = self.find_rule(input_target_types.pop(), target_type)

		link_input = self._get_link_input_list(build_name, input_list, implicit_input_list, link_mode,
			linker_opts = kwargs.pop('linker_opts', None), compiler_opts = kwargs.pop('compiler_opts', None))
		if target_type == 'static':
			link_input = list(filter(lambda item: not isinstance(item, External), link_input))
		target = self.create_target(build_name, rule = rule, input_list = list(link_input),
			add_self_to_on_use_inputs = add_self_to_on_use_inputs,
			target_type = target_type, **kwargs)
		Context.targets.append(target)
		return target

	def object_file(self, obj_name, input_list = None, compiler_opts = None, **kwargs):
		input_list = self.force_build_source(input_list)
		# collect rules from the input object extensions
		source_target_type = set()
		for source_target_type_new in map(self.find_target_type, input_list):
			if source_target_type_new:
				source_target_type.add(source_target_type_new)
		if len(source_target_type) != 1:
			raise Exception('Unable to find unique handler (%s) to generate %s' % (repr(source_target_type), obj_name))
		install_name = get_normed_name(obj_name, self.platform.extensions['object'])
		build_name = os.path.join(self.get_basepath(self.basepath_object_file), install_name)
		return self.create_target(build_name, install_name = install_name, user_name = obj_name,
			target_type = 'object', rule = self.find_rule(source_target_type.pop(), 'object'),
			input_list = self.get_implicit_input(self.implicit_object_input) + input_list + add_rule_vars(opts = compiler_opts),
			add_self_to_on_use_inputs = True, **kwargs)

	def shared_library(self, lib_name, input_list = None, **kwargs):
		install_name = get_normed_name(lib_name, self.platform.extensions['shared'])
		link_name = os.path.basename(install_name.replace(self.platform.extensions['shared'], ''))
		lib_path = os.path.dirname(lib_name) or '.'
		if link_name.startswith('lib'):
			link_name = link_name[3:]
		if (input_list is None) and not kwargs:
			if not os.path.exists(install_name):
				raise Exception('Unable to create reference to shared library: %s does not exist!' % repr(install_name))
			return RuleVariables(dict.fromkeys(['link_exe', 'link_shared'], {'opts':
				['-L%s' % lib_path, '-Wl,-rpath %s' % os.path.abspath(lib_path), '-l%s' % link_name]}))
		if not input_list:
			raise Exception('shared_library(%s) was defined with empty input list!' % repr(lib_name))
		on_use_variables = kwargs.pop('on_use_variables', {})
		on_use_variables.setdefault(None, {}).setdefault('opts', [])
		on_use_variables[None]['opts'] += ['-L%s' % lib_path, '-Wl,-rpath %s' % lib_path, '-l%s' % link_name]
		on_use_deps = kwargs.pop('on_use_deps', {})
		on_use_deps.setdefault(None, []).append(SelfReference())
		build_name = os.path.join(self.get_basepath(self.basepath_shared_library), install_name)
		return self.link(build_name, install_name = install_name, user_name = lib_name,
			target_type = 'shared', input_list = input_list, add_self_to_on_use_inputs = False,
			implicit_input_list = self.get_implicit_input(self.implicit_shared_library_input),
			on_use_deps = on_use_deps, on_use_variables = on_use_variables, **kwargs)

	def static_library(self, lib_name, input_list = None, **kwargs):
		install_name = get_normed_name(lib_name, self.platform.extensions['static'])
		if (input_list is None) and not kwargs:
			if not os.path.exists(install_name):
				raise Exception('Unable to create reference to static library: %s does not exist!' % repr(install_name))
			return InputFile(install_name, rule_list = ['link_exe', 'link_shared', 'link_static'])
		if not input_list:
			raise Exception('static_library(%s) was defined with empty input list!' % repr(lib_name))
		build_name = os.path.join(self.get_basepath(self.basepath_static_library), install_name)
		return self.link(build_name, install_name = install_name, user_name = lib_name,
			target_type = 'static', input_list = input_list, add_self_to_on_use_inputs = True,
			implicit_input_list = self.get_implicit_input(self.implicit_static_library_input), **kwargs)

	def executable(self, exe_name, input_list, **kwargs):
		install_name = exe_name
		if not install_name.endswith(self.platform.extensions['exe']):
			install_name += self.platform.extensions['exe']
		build_name = os.path.join(self.get_basepath(self.basepath_executable), install_name)
		return self.link(build_name, install_name = install_name, user_name = exe_name,
			target_type = 'exe', input_list = input_list, add_self_to_on_use_inputs = False,
			implicit_input_list = self.get_implicit_input(self.implicit_executable_input), **kwargs)

	def install(self, target_list, destination = None):
		result = []
		for obj in ensure_list(target_list):
			obj_target_type = self.find_target_type(obj)
			install_name = obj.name
			if obj.install_name:
				install_name = obj.install_name
			prefix = self.platform.install_paths[obj_target_type]
			if destination:
				prefix = os.path.abspath(os.path.expanduser(os.path.expandvars(destination)))
			install_name = os.path.join(prefix, install_name)
			rule = self.find_rule(obj_target_type, 'install')
			target = self.create_target(install_name, rule = rule, input_list = [TargetAlias(obj)])
			result.append(target)
			Context.install_targets.append(target)
		return result

	def _push_tracker(self):
		self._tracker.append((len(Context.targets), len(Context.install_targets)))

	def _pop_tracker(self):
		(idx_targets, idx_install_targets) = self._tracker.pop()
		return (Context.targets[idx_targets:], Context.install_targets[idx_install_targets:])

	def include(self, build_file_list, inherit = False, target_name = None, prefix_mode = None):
		result = []
		self._push_tracker()
		for build_cfg in ensure_list(build_file_list):
			build_name = None
			if os.path.isdir(build_cfg):
				build_name = build_cfg.replace('/', '_').replace('\\', '_').replace('.', '_')
				build_cfg = os.path.join(build_cfg, 'build.py')
			build_path = os.path.dirname(build_cfg)
			kwargs = {}
			if inherit:
				kwargs['implicit_input'] = self.implicit_input
				kwargs['implicit_object_input'] = self.implicit_object_input
				kwargs['implicit_static_library_input'] = self.implicit_static_library_input
				kwargs['implicit_shared_library_input'] = self.implicit_shared_library_input
				kwargs['implicit_executable_input'] = self.implicit_executable_input
				kwargs['basepath'] = self.basepath
				kwargs['basepath_object_file'] = self.basepath_object_file
				kwargs['basepath_static_library'] = self.basepath_static_library
				kwargs['basepath_shared_library'] = self.basepath_shared_library
				kwargs['basepath_executable'] = self.basepath_executable
			self._push_tracker()
			ctx = Context(self.registry, self.platform, self.tools,
				os.path.join(self.prefix, build_path), prefix_mode = prefix_mode, **kwargs)
			run_build_file(build_cfg, ctx, {})
			(included_targets, included_install_targets) = self._pop_tracker()
			if build_name and not target_name:
				if included_targets:
					self.create_target(build_name, phony_rule,
						input_list = list(map(TargetAlias, included_targets)))
				if included_install_targets:
					self.create_target('install_' + build_name, phony_rule,
						input_list = list(map(TargetAlias, included_install_targets)))
			result.append((build_cfg, included_targets, included_install_targets))
		(included_targets, included_install_targets) = self._pop_tracker()
		if target_name:
			if included_targets:
				self.create_target(target_name, phony_rule,
					input_list = list(map(TargetAlias, included_targets)))
			if included_install_targets:
				self.create_target('install_' + target_name, phony_rule,
					input_list = list(map(TargetAlias, included_install_targets)))
		return result


def create_ctx(ctx, **kwargs):
	platform = kwargs.pop('platform', ctx.platform)
	tools = kwargs.pop('tools', ctx.tools.copy())
	tools.toolchain = kwargs.pop('toolchain', list(ctx.tools.toolchain))
	return Context(ctx.registry, platform, tools, prefix = ctx.prefix, prefix_mode = ctx.prefix_mode, **kwargs)


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
		self._deleted = set()
	def copy(self):
		return ToolHolder(list(self.toolchain), dict(self._tools))
	def _update(self):
		for tc in reversed(self.toolchain):
			for toolname, toolfactory in tc.tools.items():
				if toolfactory and not self._tools.get(toolname):
					try:
						tool_instance = toolfactory.get_instance()
					except (ProcessError, VersionError):
						tool_instance = None
					if tool_instance and (toolname not in self._deleted):
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
		self._deleted.add(key)
		self._update()
		self._tools.__delitem__(key)
	def __iter__(self):
		self._update()
		return iter(self._tools)
	def __len__(self):
		self._update()
		return len(self._tools)
	def get_tools(self):
		self._update()
		return list(map(lambda name_tool: name_tool[1], sorted(self._tools.items())))


def create_macro(expr):
	rule_list = []
	for lang in ['c', 'cpp']:
		rule_list.extend(['compile_' + lang, 'compile_link_exe_' + lang, 'compile_link_shared_' + lang])
	return RuleVariables(dict.fromkeys(rule_list, {'opts': ['-D' + expr]}))


def format_exception(bfn, ex):
	import traceback, linecache
	exinfo = traceback.format_exception_only(ex.__class__, ex)
	if ex.__class__ == SyntaxError:
		exinfo = exinfo[1:]
		lineno = ex.lineno
		content = ''
		sys.stderr.write('Error while processing %s:%s\n\t%s\n' % (os.path.abspath(bfn), lineno, content.strip()))
	else:
		exec_line = None
		exloc = traceback.extract_tb(sys.exc_info()[2])
		for idx, entry in enumerate(exloc):
			if entry[3] is None:
				exec_line = idx
		if exec_line is not None:
			exloc = [(bfn, exloc[exec_line][1], '', linecache.getline(bfn, exloc[exec_line][1]))] + exloc[exec_line:]
		sys.stderr.write('Error while processing %s\n' % os.path.abspath(bfn))
		sys.stderr.write(str.join('', traceback.format_list(exloc)))
	sys.stderr.write(str.join('', exinfo))
	sys.exit(1)


def run_build_file(bfn, ctx, user_env):
	pyrate_version = Version(__version__)
	exec_globals = {} # needed to reference itself in default_ctx_call
	exec_globals.update({
		# globals
		'default_context': ctx,
		'pyrate_version': pyrate_version,
		'tools': ctx.tools,
		'toolchain': ctx.tools.toolchain,
		'macro': create_macro,
		'version': ver,
		# stable API
		'create_external': default_ctx_call(exec_globals, Context.create_external),
		'executable': default_ctx_call(exec_globals, Context.executable),
		'find_external': default_ctx_call(exec_globals, Context.find_external),
		'find_internal': default_ctx_call(exec_globals, Context.find_internal),
		'find_toolchain': default_ctx_call(exec_globals, Context.find_toolchain),
		'include': default_ctx_call(exec_globals, Context.include),
		'install': default_ctx_call(exec_globals, Context.install),
		'match': default_ctx_call(exec_globals, Context.match),
		'match_libs': default_ctx_call(exec_globals, Context.match_libs),
		'object_file': default_ctx_call(exec_globals, Context.object_file),
		'shared_library': default_ctx_call(exec_globals, Context.shared_library),
		'static_library': default_ctx_call(exec_globals, Context.static_library),
		'use_external': default_ctx_call(exec_globals, Context.use_external),
		'use_toolchain': default_ctx_call(exec_globals, Context.use_toolchain),
		# development API
		'BuildSource': BuildSource,
		'BuildTarget': create_registered(ctx.registry, BuildTarget),
		'BuildTargetFree': BuildTarget,
		'Context': default_ctx_call(exec_globals, create_ctx),
		'External': default_ctx_call(exec_globals, External, keyword_only = True),
		'find_rule': default_ctx_call(exec_globals, Context.find_rule),
		'InputFile': InputFile,
		'Rule': Rule,
	})
	exec_globals.update(user_env)
	with open(bfn) as bfp:
		try:
			exec(bfp.read(), exec_globals)
		except Exception as ex:
			format_exception(bfn, ex)
	return exec_globals


def generate_build_file(bfn, ofn, mode):
	if os.path.dirname(bfn):
		os.chdir(os.path.dirname(bfn))
		bfn = os.path.basename(bfn)

	registry = Registry()
	platform = Platform_linux()
	tools = ToolHolder([], {})
	ctx = Context(registry, platform, tools, '', None)
	ctx.tools.toolchain.append(Toolchain_GCC(ctx))
	user_env = {}
	if mode:
		user_env['build_output'] = ['makefile']
	exec_globals = run_build_file(bfn, ctx, user_env)

	default_targets = exec_globals.get('default_targets')
	(rules, targets) = registry.write()
	if Context.install_targets:
		targets.append(BuildTarget('install', phony_rule, list(map(lambda t: InputFile(t.name), Context.install_targets))))
	target_all = BuildTarget('all', phony_rule, list(map(lambda t: InputFile(t.name), Context.targets)))
	targets.append(target_all)
	default_targets = ensure_list(default_targets)
	if default_targets is None:
		default_targets = [target_all]

	bsys_list = exec_globals.get('build_output', ['ninja'])
	for bsys in bsys_list:
		if ofn and (len(bsys_list) > 1):
			ofn = os.path.splitext(ofn)[0] + '.' + bsys
		process_build_output(bsys, targets, rules, default_targets, ofn)


def main():
	version_info = 'pyrate version ' + __version__
	try:
		if os.environ.get('TESTOLDIMPORTS'):
			raise ImportError()
		import argparse
		parser = argparse.ArgumentParser()
		parser.add_argument('build_file', nargs = '?', default = 'build.py',
			help = 'name of the input file - default: build.py')
		parser.add_argument('-V', '--version', action = 'version', version = version_info)
		parser.add_argument('-M', '--makefile', action = 'store_true', help = 'enable makefile mode')
		parser.add_argument('-o', '--output', nargs = 1, default = None,
			help = 'name of output build file')
		args = parser.parse_args()
		if args.output:
			args.output = args.output[0]
		bfn = args.build_file
	except ImportError:
		optparse = __import__('optparse')
		parser = optparse.OptionParser(usage = 'pyrate [options] build_file')
		parser.add_option('-V', '--version', action='store_true', help = 'display version')
		parser.add_option('-M', '--makefile', action = 'store_true', help = 'enable makefile mode')
		parser.add_option('-o', '--output', default = None,
			help = 'name of output build file', dest='output')
		(args, posargs) = parser.parse_args()
		if len(posargs) > 1:
			sys.stderr.write('too many build_file arguments provided! %s\n' % repr(posargs))
			return os.EX_USAGE
		elif not posargs:
			posargs = ['build.py']
		bfn = posargs[0]
		if args.version:
			sys.stderr.write(version_info + '\n')
			sys.exit(os.EX_OK)

	generate_build_file(bfn, args.output, args.makefile)

################################################################################
# Externals + helper functions
################################################################################

class External(BuildSource):
	def __init__(self, ctx, on_use_variables = None, rules = None, target_types_by_ext = None,
			required_inputs_by_target_type = None):
		assert(ctx)
		self.name = self.__class__.name
		BuildSource.__init__(self, on_use_variables = on_use_variables)
		self.rules = (rules or [])
		self.target_types_by_ext = (target_types_by_ext or {})
		self.required_inputs_by_target_type = (required_inputs_by_target_type or {})

	def _check_version(self, version_req, version_str):
		self.version = Version(version_str)
		if version_req and not version_req(self.version):
			raise VersionError('Unable to find correct version!')

	def __repr__(self):
		try:
			return '%s(%s)' % (self.__class__.__name__, self.version)
		except Exception:
			return self.__class__.__name__

	def register_external(cls, *names):
		cls.name = names[0]
		for name in names:
			External.available[name] = cls
	register_external = classmethod(register_external)
External.available = {}


class External_linker(External):
	def __init__(self, ctx,
			link_static, link_static_opts, link_static_def, link_static_opts_def,
			link_shared, link_shared_opts, link_shared_def, link_shared_opts_def,
			link_exe, link_exe_opts, link_exe_def, link_exe_opts_def):
		link_static = (link_static or link_static_def)
		link_static_opts = (link_static_opts or link_static_opts_def)
		link_shared = (link_shared or link_shared_def)
		link_shared_opts = (link_shared_opts or link_shared_opts_def)
		link_exe = (link_exe or link_exe_def)
		link_exe_opts = (link_exe_opts or link_exe_opts_def)
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
External_link_base.register_external('link-base')


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
External_link_gcc.register_external('link-gcc')


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
External_link_llvm.register_external('link-llvm')


class External_SimpleCompiler(External): # C family compiler
	std = property(lambda self: self._std, lambda self, value: self._set_std(value))

	def __init__(self, ctx, lang, std, compiler, compiler_opts, var_prefix, ext_list, req_input = None):
		self._std = None
		self._var_prefix = var_prefix
		self._compiler_opts = compiler_opts
		self._compiler_variables = {var_prefix: compiler, var_prefix + '_FLAGS': self._compiler_opts}
		required_inputs_by_target_type = {
			'linux': {'shared': [RuleVariables({'compile_' + lang: {'opts': ['-fPIC']}})]},
		}
		if req_input:
			for platform in required_inputs_by_target_type:
				for target_type in req_input:
					required_inputs_by_target_type[platform].setdefault(target_type, []).extend(req_input[target_type])
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

	def _find_latest(self, vcmp_list, default = None):
		for (vcmp, result) in vcmp_list:
			if vcmp(self.version):
				return result
		return default

	def get_latest(self):
		raise Exception('%s: Unable to find latest language standard!' % self.__class__.__name__)

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
		compiler = (compiler or 'gcc')
		compiler_opts = (compiler_opts or '-Wall -pedantic')
		ext_list = (ext_list or ['.c'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'c',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'CC', ext_list = ext_list)
External_gcc.register_external('gcc')


class External_gpp(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = (compiler or 'g++')
		compiler_opts = (compiler_opts or '-Wall -pedantic')
		ext_list = (ext_list or ['.cpp', '.cxx', '.cc'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'cpp',
			compiler = compiler, compiler_opts = compiler_opts,
			var_prefix = 'CXX', ext_list = ext_list, req_input = {
				'exe': [External_libstdcpp(ctx)], 'shared': [External_libstdcpp(ctx)],
				'static': [External_libstdcpp(ctx)]})

	def get_latest(self):
		return self._find_latest([
			(ver < '4.3', 'c++03'),
			(ver < '4.7', 'c++0x'),
			(ver < '4.8', 'c++11'),
			(ver < '5.0', 'c++14')],
			'c++1z')
External_gpp.register_external('g++', 'gpp')


class External_gfortran(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = (compiler or 'gfortran')
		compiler_opts = (compiler_opts or '-Wall')
		ext_list = (ext_list or ['.f'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[-1])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'fortran',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'F', ext_list = ext_list)
External_gfortran.register_external('gfortran')


class External_clang(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = (compiler or 'clang')
		compiler_opts = (compiler_opts or '-Weverything -Wno-padded')
		ext_list = (ext_list or ['.c'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[2])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'c',
			compiler = compiler, compiler_opts = compiler_opts, var_prefix = 'CC', ext_list = ext_list)
External_clang.register_external('clang')


class External_clangpp(External_SimpleCompiler):
	def __init__(self, ctx, version = None, std = None, compiler = None, compiler_opts = None, ext_list = None):
		compiler = (compiler or 'clang++')
		compiler_opts = (compiler_opts or '-Weverything -Wno-padded')
		ext_list = (ext_list or ['.cpp', '.cxx', '.cc'])
		self._check_version(version, run_process([compiler, '--version'])[0].splitlines()[0].split()[2])
		External_SimpleCompiler.__init__(self, ctx, std = std, lang = 'cpp',
			compiler = compiler, compiler_opts = compiler_opts,
			var_prefix = 'CXX', ext_list = ext_list, req_input = {
				'exe': [External_libstdcpp(ctx)], 'shared': [External_libstdcpp(ctx)],
				'static': [External_libstdcpp(ctx)]})

	def get_latest(self):
		return self._find_latest([
			(ver >= '3.5', 'c++1z'),
			(ver < '3.4', 'c++14'),
			(ver < '3.3', 'c++11')])
External_clangpp.register_external('clang++', 'clangpp')


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
		wrapper_src = BuildTarget(get_normed_name(name, '.cpp'), swig_rule,
			[InputFile(ifile)] + add_rule_vars(opts = swig_opts, module_name = name),
			on_use_inputs = {None: [SelfReference()]},
			on_use_variables = wrapper_ext.on_use_variables, target_type = 'cpp')
		return context.shared_library('_' + name, [wrapper_src, wrapper_ext] + (libs or []), **kwargs)
External_SWIG.register_external('swig')


class SimpleExternal(External):
	def __init__(self, ctx, **kwargs):
		link_opts = ensure_list(kwargs.pop('link', []))
		if link_opts:
			kwargs['link_static'] = link_opts
			kwargs['link_shared'] = link_opts
			kwargs['link_exe'] = link_opts
		on_use_variables = {}
		for rule_name, opts in kwargs.items():
			on_use_variables.setdefault(rule_name, {})['opts'] = ensure_list(opts)
		External.__init__(self, ctx, on_use_variables = on_use_variables)


class External_pthread(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link = '-pthread', compile_cpp = '-pthread')
External_pthread.register_external('pthread')


class External_libstdcpp(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link_shared = '-lstdc++ -lm', link_exe = '-lstdc++ -lm')
External_libstdcpp.register_external('libstdc++', 'libstdcpp')


class External_libcpp(SimpleExternal):
	def __init__(self, ctx):
		SimpleExternal.__init__(self, ctx, link_shared = '-lc++ -lc++abi -lm', link_exe = '-lc++ -lc++abi -lm')
External_libcpp.register_external('libc++', 'libcpp')


class External_Python(SimpleExternal):
	def __init__(self, ctx, version = None, build_helper = 'python-config'):
		link_opts = run_process([build_helper, '--ldflags'])[0]
		python_lib = list(filter(lambda entry: entry.startswith('-lpython'), link_opts.split()))
		self._check_version(version, python_lib.pop().replace('-lpython', ''))
		SimpleExternal.__init__(self, ctx, link = link_opts,
			compile_cpp = run_process([build_helper, '--cflags'])[0])
External_Python.register_external('python')


class External_ROOT(SimpleExternal):
	def __init__(self, ctx, version = None, build_helper = 'root-config', link_opts = ''):
		self._check_version(version, run_process([build_helper, '--version'])[0].split()[-1].replace('/', '.'))
		SimpleExternal.__init__(self, ctx, link = run_process([build_helper, '--libs'])[0] + ' ' + link_opts,
			compile_cpp = run_process([build_helper, '--cflags'])[0])
		self._ctx = ctx

	def dictionary(self, name, header_list = None, include_list = None, opts = None, context = None, **kwargs):
		cint_rule = Rule(('c++.h', 'c++'), 'rootdict', 'rootcint -f $out ${include_opts} $in', 'rootcint $out', {})
		include_opts = []
		if include_list:
			include_opts = add_rule_vars(include_opts = str.join(' ', map(lambda dn: '-I%s' % dn, include_list)))
		context = context or self._ctx
		return BuildTarget(get_normed_name(name, '.cpp'), cint_rule,
			context.force_build_source(header_list) + include_opts + add_rule_vars(opts = opts),
			on_use_inputs = {None: [SelfReference()]},
			on_use_variables = self.on_use_variables,
			target_type = 'cpp', **kwargs)
External_ROOT.register_external('root')


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
	TempExternal.register_external(name)
	return TempExternal


def define_pkg_config_external(name, version_parser = None):
	try:
		run_process(['pkg-config', name, '--exists'])
	except ProcessError:
		return
	version_parser_dict = {
		'openssl': lambda version_str: version_str[:-1] + '.' + version_str[-1],
	}
	version_parser = version_parser or version_parser_dict.get(name)
	return create_build_helper_external(name, 'pkg-config',
		version_query = '%s --modversion' % name, version_parser = version_parser,
		link = '%s --libs' % name, compile_cpp = '%s --cflags' % name)


def define_non_pkg_config_externals():
	for (tool, ldopt, cxxopt) in [
		('fltk-config',     '--ldflags', '--cxxflags'),
		('llvm-config',     '--libs',    '--cppflags'),
		('odbc_config',     '--libs',    '--cflags'),
		('wx-config',       '--libs',    '--cxxflags'),
	]:
		create_build_helper_external(tool.split('-')[0].split('_')[0], tool,
			link = ldopt, compile_cpp = cxxopt, version_query = '--version',
			version_parser = lambda version_str: version_str.split()[-1].replace('/', '.'))
define_non_pkg_config_externals()

################################################################################
# Toolchains + helper functions
################################################################################

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
Toolchain.available['gcc'] = Toolchain_GCC


class Toolchain_LLVM(Toolchain):
	def __init__(self, ctx, version = None, c_std = None, c_opts = None, cpp_std = None, cpp_opts = None,
			link_shared_opts = None, link_exe_opts = None):
		Toolchain.__init__(self, ctx)

		self.tools['linker'] = Delayed(External_link_llvm, ctx, link_shared_opts = link_shared_opts, link_exe_opts = link_exe_opts)
		self.tools['c'] = Delayed(External_clang, ctx, version = version, std = c_std, compiler_opts = c_opts)
		self.tools['cpp'] = Delayed(External_clangpp, ctx, version = version, std = cpp_std, compiler_opts = cpp_opts)
Toolchain.available['llvm'] = Toolchain_LLVM

################################################################################
# Platforms
################################################################################

class Platform(object):
	def __init__(self, name, extensions, install_paths, rules):
		(self.name, self.extensions, self.install_paths, self.rules) = (name, extensions, install_paths, rules)

	def get_required_inputs(self, target_type, toolholder):
		result = []
		for tool in toolholder.get_tools():
			result.extend(tool.required_inputs_by_target_type.get(self.name, {}).get(target_type, []))
		return result

	def __str__(self):
		return nice_repr(self, 8)

	def __repr__(self):
		return '%s' % (self.__class__.__name__)


class Platform_linux(Platform):
	def __init__(self):
		Platform.__init__(self, name = 'linux',
			extensions = {'object': '.o', 'shared': '.so', 'static': '.a', 'exe': ''},
			install_paths = {'shared': '/usr/lib', 'static': '/usr/lib', 'exe': '/usr/bin'},
			rules = [
				Rule(('exe', 'install'), 'install', 'cp $in $out', 'installing executable $out', {}),
				Rule(('shared', 'install'), 'install_lib', 'cp $in $out', 'installing shared library $out', {}),
				Rule(('static', 'install'), 'install_lib', 'cp $in $out', 'installing static library $out', {}),
			])

################################################################################
# Build file writer
################################################################################

class BuildFileWriter(object):
	def __init__(self, fn, default_fn):
		if fn is None:
			fn = default_fn
		self._fn = fn
		self._fp = open(self._fn, 'w')
BuildFileWriter.available = {}


class NinjaBuildFileWriter(BuildFileWriter):
	def __init__(self, fn = None):
		BuildFileWriter.__init__(self, fn, 'build.ninja')
		self._vars = {}
	def _write_var(self, key, value):
		if self._vars.get(key) != value:
			self._fp.write('%s = %s\n' % (key, value.strip()))
		self._vars[key] = value
	def write_default(self, default_targets, all_targets): # pylint:disable=unused-argument
		if (len(default_targets) == 1) and (default_targets[0].name == 'all'): # ninja's default rule is all
			return
		self._fp.write('default %s\n' % str.join(' ', map(lambda t: t.name, default_targets)))
	def write_rule(self, rule):
		for key, value in sorted(rule.defaults.items()):
			self._write_var(key, value)
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
BuildFileWriter.available['ninja'] = NinjaBuildFileWriter


class MakefileWriter(BuildFileWriter):
	def __init__(self, fn = None):
		BuildFileWriter.__init__(self, fn, 'Makefile')
		self._vars = set()
	def _write_var(self, key, value):
		self._fp.write('%s := %s\n' % (key, value.strip()))
	def write_default(self, default_targets, all_targets):
		all_targets = filter(lambda t: t.build_rule != phony_rule, all_targets)
		self._fp.write('clean:\n\t@rm -f %s\n' % str.join(' ', map(lambda t: t.name, all_targets)))
		default = default_targets[0].name
		if len(default_targets) > 1:
			default = 'default_target'
			self._fp.write('%s: %s\n' % (default, str.join(' ', map(lambda t: t.name, default_targets))))
			self._fp.write('.PHONY: %s\n' % default)
		self._fp.write('.DEFAULT_GOAL := %s\n' % default)
	def write_rule(self, rule):
		for key, value in sorted(rule.defaults.items()):
			self._write_var(key, value)
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
				self._write_var(opt + '_' + opt_hash, opt_value)
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
		if cmd:
			self._fp.write('\t%s\n\n' % cmd)
		if target.build_rule == phony_rule:
			self._fp.write('.PHONY: %s\n' % target.name)
BuildFileWriter.available['makefile'] = MakefileWriter


def process_build_output(name, targets, rules, default_targets, ofn = None):
	name = name.lower()
	writer = BuildFileWriter.available[name](ofn)
	list(map(writer.write_rule, filter(lambda r: r != phony_rule, rules)))
	list(map(writer.write_target, targets))
	writer.write_default(default_targets, targets)

################################################################################
# Version support
################################################################################

class VersionError(Exception):
	pass


def _parse_version_str(value):
	if value.isdigit():
		return int(value)
	elif value.isalpha():
		return ord(value.lower()) - ord('a')
	assert(False)


class Version(object):
	def __init__(self, value):
		try:
			if isinstance(value, Version):
				value = value.value
			if isinstance(value, (list, tuple)): # (1,32,5)
				value = list(value)
			elif isinstance(value, (float, int)): # 1.32
				value = list(map(int, str(value).split('.')))
			else: # '1.32.5'
				value = list(map(_parse_version_str, value.split('.')))
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
ver = VersionComparison()

################################################################################

if __name__ == '__main__':
	sys.exit(main())
