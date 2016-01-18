#!/usr/bin/env pyrate

lib_foo = shared_library('libExample7', ['foo.cpp'])
python = find_external('python')
swig = find_external('swig', version >= 2.0)
if swig and python:
	x = swig.wrapper('python', 'py_foo', 'foo.i', libs = [lib_foo])
