#!/usr/bin/env pyrate

foo_lib_a = shared_library('libExample3a', ['foo.cpp'], compiler_opts = '-O3 -fPIC')
ex_a = executable('example3a.bin', ['test.cpp', foo_lib_a])

foo_lib_b = shared_library('libExample3b', ['foo.cpp'], compiler_opts = '-O3')
ex_b = executable('example3b.bin', ['test.cpp', foo_lib_b])
ex_c = executable('example3c.bin', ['test.cpp', foo_lib_b], compiler_opts = '-O0')

default_targets = [ex_c]
