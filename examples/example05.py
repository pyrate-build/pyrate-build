#!/usr/bin/env pyrate

files = match('test*.cpp foo*.cpp -test_cpp11.cpp')
executable('example05.bin', files)
executable('example05.bin', files, no_rename = True)
executable('example05.bin', files, compiler_opts = '-O3')
