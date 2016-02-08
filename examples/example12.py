#!/usr/bin/env pyrate

if default_context.platform.name == 'linux':
	executable('example12a.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libm')])
	executable('example12b.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libm')])
