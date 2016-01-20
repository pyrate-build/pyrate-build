#!/usr/bin/env pyrate

def print_ver(ext):
	if ext:
		info = '\t%-20s' % ext.__class__.__name__
		try:
			info += '\t' + repr(ext.version)
		except:
			pass
		print(info)
print_ver(create_external('xml2', build_helper = 'xml2-config',
	version_query = '--version', version_parser = lambda x: x,
	link = '--libs', compile_cpp = '--cflags'))
print_ver(create_external('xml2_nover', build_helper = 'xml2-config',
	link = '--libs', compile_cpp = '--cflags'))
print_ver(find_external('dbus-1'))
print_ver(find_external('nss'))
print_ver(find_external('sfml-all'))
print_ver(find_external('wx'))
print_ver(find_external('x11', version < 12))
print_ver(find_external('xt'))
