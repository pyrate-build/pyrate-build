#!/usr/bin/env pyrate

import logging
assert(pyrate_version == pyrate_version)

ctx = Context()
ctx.tools['cpp'] = find_external('g++', std = 'c++14')
logging.warning('new_ctx: ' + ctx.tools['cpp'].std)
tools['cpp'].std = 'latest'
logging.warning('def_ctx: ' + tools['cpp'].std)
tools['cpp'].std = 'c++11'
logging.warning('def_ctx: ' + tools['cpp'].std)

pthread = find_external('pthread')
exe1 = executable('example08_default_ctx.bin', ['test_cpp11.cpp', 'foo.cpp', pthread], compiler_opts = '-O3')
exe2 = ctx.executable('example08_own_ctx.bin', ['test_cpp11.cpp', 'foo.cpp', pthread], compiler_opts = '-O3')
default_targets = exe1
str(exe1)
str(exe1.build_src[0])
str(exe1.build_rule)
repr(tools)
len(tools)
for tool in tools:
	repr(tool)
