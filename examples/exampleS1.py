#!/usr/bin/env pyrate

tools['cpp'].std = 'c++11'
lib_foo = shared_library('libExample7', ['foo.cpp'])
python = find_external('python')
swig = find_external('swig', version >= 2.0)
if swig and python:
	swig.wrapper('python', 'py_foo', 'foo.i', libs = [lib_foo])
