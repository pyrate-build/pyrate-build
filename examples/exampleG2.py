#!/usr/bin/env pyrate

build_output = ['makefile', 'ninja']
install(executable('example11.bin', 'test.cpp foo.cpp'), '/tmp/bin')
