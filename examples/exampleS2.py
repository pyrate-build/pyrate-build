#!/usr/bin/env pyrate

use_toolchain('llvm', version >= 3.7, cpp_std = 'c++11', cpp_opts = '-Wall')

lib_files = match('*.cpp -test* -mylib.* -py_foo.cpp')
static_library('libFoo', lib_files, compiler_opts = '-O3')
lib_reference = shared_library('libFoo', lib_files)

python = find_external('python', version > 2)
swig = find_external('swig', version >= 2)

if swig and python:
	swig.wrapper('python', 'mylib', 'foo.i', libs = [lib_reference])

for fn in match('test*.cpp'):
	executable(fn.replace('.cpp', '.bin'), [fn, lib_reference, find_external('pthread')])
