#!/usr/bin/env pyrate

assert(pyrate_version >= '0.1.10')
files = ['test.cpp', 'foo.cpp']
executable('example4_debug.bin', files)
executable('example4_release.bin', files, compiler_opts = '-O3')
