#!/usr/bin/env pyrate

assert(pyrate_version >= '0.1.10')
files = ['test.cpp', 'foo.cpp']
executable('example03_debug.bin', files + [macro('DEBUG')])
executable('example03_release.bin', files, compiler_opts = '-O3')
