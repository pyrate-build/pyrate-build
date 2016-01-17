#!/usr/bin/env pyrate

foo_lib = static_library('libExample2', 'foo.cpp')
executable('example2.bin', ['test.cpp', foo_lib])
