#!/usr/bin/env pyrate

foo_obj = object_file('foo_obj', ['foo.cpp'], compiler_opts = '-O3')
executable('example07.bin', ['test.cpp', foo_obj])
