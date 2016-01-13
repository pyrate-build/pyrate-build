#!/usr/bin/env pyrate

static_library('libFoo_debug', ['foo.cpp'], compiler_opts = '-O0')
static_library('libFoo_final', ['foo.cpp'], compiler_opts = '-O3')
lib = static_library('libFoo_unchg', ['foo.cpp'])
executable('bar.exe', ['test.cpp', lib])
