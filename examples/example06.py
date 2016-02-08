#!/usr/bin/env pyrate

gcc_cpp11 = find_external('g++', std = 'c++11')
if gcc_cpp11:
	tools['cpp'] = gcc_cpp11
	use_external('pthread')
	executable('example06.bin', 'test_cpp11.cpp')
