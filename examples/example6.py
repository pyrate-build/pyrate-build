#!/usr/bin/env pyrate

gcc_cpp11 = find_external('gcc', std = 'c++11')
pthread = find_external('pthread')

if gcc_cpp11 and pthread:
	compiler['C++'] = gcc_cpp11
	executable('example6.bin', ['test_cpp11.cpp', pthread])
