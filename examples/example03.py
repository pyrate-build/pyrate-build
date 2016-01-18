#!/usr/bin/env pyrate

foo_lib_a = shared_library('libExample03a', ['foo.cpp'], compiler_opts = '-O3 -fPIC')
ex_a = executable('example03a.bin', ['test.cpp', foo_lib_a])

foo_lib_b = shared_library('libExample03b', ['foo.cpp'], compiler_opts = '-O3')
ex_b = executable('example03b.bin', ['test.cpp', foo_lib_b])
ex_c = executable('example03c.bin', ['test.cpp', foo_lib_b], compiler_opts = '-O0')

default_targets = [ex_c]
