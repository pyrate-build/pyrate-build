#!/usr/bin/env pyrate

files = ['test.cpp', 'foo.cpp']
executable('example4_debug.bin', files)
executable('example4_release.bin', files, compiler_opts = '-O3')
