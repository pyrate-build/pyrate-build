#!/usr/bin/env pyrate

import logging
def print_ver(ext):
	if ext:
		try:
			ver = repr(ext.version)
		except Exception:
			ver = 'Version(unavailable)'
		logging.warning('external:%-20s\t%s', ext.__class__.__name__, ver)

print_ver(create_external('wxwidgets', version >= 2.8, build_helper = 'wx-config',
	version_query = '--version', link = '--libs', compile_cpp = '--cxxflags'))
print_ver(create_external('wxwidgets', version = version >= 2.8, build_helper = 'wx-config',
	version_query = '--version', link = '--libs', compile_cpp = '--cxxflags'))
print_ver(create_external('xml2', build_helper = 'xml2-config',
	version_query = '--version', version_parser = lambda x: x,
	link = '--libs', compile_cpp = '--cflags'))
print_ver(create_external('xml2_nover', build_helper = 'xml2-config',
	link = '--libs', compile_cpp = '--cflags'))

print_ver(find_external('dbus-1'))
print_ver(find_external('nss'))
print_ver(find_external('sfml-all', version == 2.0))
print_ver(find_external('wx', version != 1.0))
print_ver(find_external('x11', version < 12))
print_ver(find_external('xt', version <= 12))
print_ver(find_external('xt', version > 12))
r1 = repr(tools['cpp'])
executable('test.bin', 'test.cpp foo.cpp')
r2 = repr(tools['cpp'])
assert(r1 == r2)
