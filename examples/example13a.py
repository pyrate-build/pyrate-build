#!/usr/bin/env pyrate

default_context.basepath = 'included'
install(executable('example13a.bin', 'test.cpp foo.cpp', compiler_opts = '-O3'))
