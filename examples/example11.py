#!/usr/bin/env pyrate

executable('example11.bin', 'test.cpp test.c foo.cpp', link_mode = 'direct') # automatic switching to 'single' mode
