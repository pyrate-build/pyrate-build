#!/usr/bin/env pyrate

clang = find_external('clang', version >= 3.7, std = 'c++11')
if clang:
	compiler['C++'] = clang

lib_files = match("*.cpp -test* -mylib.cpp")
static_library('libFoo', lib_files, compiler_opts = '-O3')
lib_reference = shared_library('libFoo', lib_files)

python = find_external('python', version > 2)
swig = find_external('swig')
if swig and python:
	swig.wrapper('python', 'mylib', 'mylib.i', libs = [lib_reference])

for fn in match("test*.cpp"):
	executable(fn.replace('.cpp', '.exe'), [fn, lib_reference])
