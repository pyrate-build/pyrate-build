#!/usr/bin/env pyrate

default_context.basedir = 'obj'
executable('example10.bin', 'test.cpp foo.cpp', link_mode = 'direct')
repr(toolchain)
