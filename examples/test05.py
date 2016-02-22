#!/usr/bin/env pyrate

import logging, os
logging.critical(repr(list(filter(lambda x: x.endswith('.a'), os.listdir('/usr/lib')))))
logging.critical(repr(list(filter(lambda x: x.endswith('.so'), os.listdir('/usr/lib')))))

try:
	executable('test05a.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libpython2.7.a')])
except Exception:
	logging.critical('referencing static library')
try:
	executable('test05b.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libpython2.7.so')])
except Exception:
	logging.critical('referencing shared library')
try:
	executable('test05c.bin', ['test.cpp', 'foo.cpp', static_library('/usr/lib/libfoo')])
except Exception:
	logging.critical('referencing bogus static library')
try:
	executable('test05d.bin', ['test.cpp', 'foo.cpp', shared_library('/usr/lib/libfoo')])
except Exception:
	logging.critical('referencing bogus shared library')
