#!/usr/bin/env pyrate

import logging
assert(pyrate_version == pyrate_version)

ctx = Context()
ctx.tool['cpp'] = find_external('g++', std = 'c++14')
logging.warning('new_ctx: ' + ctx.tool['cpp'].std)
tool['cpp'].std = 'latest'
logging.warning('def_ctx: ' + tool['cpp'].std)
tool['cpp'].std = 'c++11'
logging.warning('def_ctx: ' + tool['cpp'].std)

pthread = find_external('pthread')
exe1 = executable('example08_default_ctx.bin', ['test_cpp11.cpp', 'foo.cpp', pthread], compiler_opts = '-O3')
exe2 = ctx.executable('example08_own_ctx.bin', ['test_cpp11.cpp', 'foo.cpp', pthread], compiler_opts = '-O3')
default_targets = exe1
repr(exe1)
