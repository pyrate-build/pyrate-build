#!/usr/bin/env pyrate

install(executable('example12.bin', 'test.cpp foo.cpp'))
include('example12a.py', target_name = 'included', prefix_mode = 'front')
