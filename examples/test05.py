#!/usr/bin/env pyrate

import logging
executable('example12a.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libdl')])
executable('example12b.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libdl')])
try:
	executable('example12c.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libfoo')])
except:
	logging.critical('referencing library')
try:
	executable('example12d.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libfoo')])
except:
	logging.critical('referencing library')
