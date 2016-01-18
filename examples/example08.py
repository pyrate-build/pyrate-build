#!/usr/bin/env pyrate

compiler['C++'].std = 'latest'
print(compiler['C++'].std)
compiler['C++'].std = 'c++11'

pthread = find_external('pthread')
executable('example08.bin', ['test_cpp11.cpp', 'foo.cpp', pthread], compiler_opts = '-O3')
