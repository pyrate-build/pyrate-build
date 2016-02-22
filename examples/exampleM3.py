#!/usr/bin/env pyrate

build_output = ['makefile']
ex_d = executable('exampleM2_debug.bin', 'test.cpp foo.cpp', compiler_opts = '-O0')
ex_r = executable('exampleM2_release.bin', 'test.cpp foo.cpp', compiler_opts = '-O3')
default_targets = [ex_r, ex_d]
