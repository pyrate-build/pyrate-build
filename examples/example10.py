#!/usr/bin/env pyrate

executable('example10.bin', 'test.cpp foo.cpp', link_mode = 'direct')
find_external('abcd')
find_toolchain('abcd')
repr(toolchain)
