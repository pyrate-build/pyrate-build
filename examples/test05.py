#!/usr/bin/env pyrate

import logging, os

def display_libs(dn, ext):
	logging.critical(repr(list(filter(lambda x: x.endswith(ext), os.listdir(dn)))))
for ext in ['.a', '.so']:
	display_libs('/usr/lib', ext)

def check_linking(name, libtype, libname, msg):
	try:
		executable(name, ['test.cpp', 'foo.cpp', libtype(libname)])
	except Exception:
		logging.critical('%s: %s %s', name, libtype, libname)
		logging.critical(msg)
check_linking('test05a.bin', static_library, '/usr/lib/libpython2.7.a', 'referencing static library')
check_linking('test05b.bin', shared_library, '/usr/lib/libpython2.7.so', 'referencing shared library')
check_linking('test05c.bin', static_library, '/usr/lib/libfoo', 'referencing bogus static library')
check_linking('test05d.bin', shared_library, '/usr/lib/libfoo', 'referencing bogus shared library')
