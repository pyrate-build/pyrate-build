#!/usr/bin/env pyrate

foo_lib = shared_library('libExample3', ['foo.cpp'], compiler_opts = '-fPIC -O3')
executable('example3.bin', ['test.cpp', foo_lib])
