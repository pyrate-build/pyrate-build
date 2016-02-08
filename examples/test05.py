#!/usr/bin/env pyrate

import logging, os
logging.critical(repr(list(filter(lambda x: x.endswith('.a'), os.listdir('/usr/lib')))))
logging.critical(repr(list(filter(lambda x: x.endswith('.so'), os.listdir('/usr/lib')))))

executable('example12a.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libdl')])
executable('example12b.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libdl')])
try:
	executable('example12c.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libfoo')])
except Exception:
	logging.critical('referencing library')
try:
	executable('example12d.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libfoo')])
except Exception:
	logging.critical('referencing library')
