#!/usr/bin/env pyrate

default_context.basedir = 'obj'
executable('example10a.bin', 'test.cpp foo.cpp', link_mode = 'direct')
find_external('abcd')
repr(toolchain)
