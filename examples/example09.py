#!/usr/bin/env pyrate

print(create_external('xml2', build_helper = 'xml2-config',
	version_query = '--version', version_parser = lambda x: x,
	link = '--libs', compile_cpp = '--cflags'))
print(create_external('xml2_nover', build_helper = 'xml2-config',
	link = '--libs', compile_cpp = '--cflags'))
print(find_external('dbus-1'))
print(find_external('nss'))
print(find_external('sfml-all'))
print(find_external('wx'))
print(find_external('x11', version < 12))
print(find_external('xt'))
