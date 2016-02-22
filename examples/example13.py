#!/usr/bin/env pyrate

install(executable('example13.bin', 'test.cpp foo.cpp'))
include('example13a.py', target_name = 'included', prefix_mode = 'front')
