#!/usr/bin/env pyrate

assert(pyrate_version >= '0.1.10')
files = ['test.cpp', 'foo.cpp']
executable('example04_debug.bin', files)
executable('example04_release.bin', files, compiler_opts = '-O3')
