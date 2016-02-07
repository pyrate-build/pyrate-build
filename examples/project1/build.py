#!/usr/bin/env pyrate

default_context.basepath = 'build'
assert(find_internal('libfoo') == None)
include('foo', inherit = True)
libfoo = find_internal('libfoo')
install(executable('example02.bin', [match('test.cpp'), libfoo]))
