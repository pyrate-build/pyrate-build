#!/usr/bin/env pyrate

files = ['test.cpp', 'foo.cpp']
executable('example5.bin', files)
executable('example5.bin', files)
executable('example5.bin', files, compiler_opts = '-O3')
