#!/usr/bin/env pyrate

executable('example10.bin', 'test.cpp foo.cpp', link_mode = 'direct', compiler_opts = '-O1')
