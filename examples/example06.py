#!/usr/bin/env pyrate

assert(pyrate_version < 1.0)
gcc_cpp11 = find_external('g++', std = 'c++11')
pthread = find_external('pthread')

if gcc_cpp11 and pthread:
	tool['cpp'] = gcc_cpp11
	executable('example06.bin', ['test_cpp11.cpp', pthread])
