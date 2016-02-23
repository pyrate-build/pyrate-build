import logging
assert(pyrate_version > (0, 1, 9))
assert(pyrate_version >= '0.1.10')
assert(pyrate_version != '0.0.1')
assert(pyrate_version == pyrate_version)

match('*.cpp', recurse = True)
exe = executable('test.bin', ['test.cpp'])
exe = executable('test.bin', ['test.cpp'])
try:
	executable('test.bin', ['test.cpp', None])
except Exception:
	logging.critical('None found!')
try:
	executable('test.bin', ['test.cpp', version])
except Exception:
	logging.critical('Invalid input!')

find_external('libc++')
find_external('abcd')
find_toolchain('abcd')
str(exe)
str(default_context.platform)
str(exe.build_src[0])
str(exe.build_rule)
repr(default_context.platform)
repr(macro('DEBUG'))
repr(toolchain)
repr(tools)
len(tools)
str(install(exe)[0])
for tool in tools:
	logging.critical('%s: %s', tool, repr(tools[tool]))
logging.critical('deleting c/c++')
del tools['c']
del tools['cpp']
for tool in tools:
	logging.critical('%s: %s', tool, repr(tools[tool]))
try:
	object_file('test.obj', ['test.cpp'])
except Exception:
	logging.critical('rule not found!')
try:
	find_rule('object', 'cpp')
except Exception:
	logging.critical('rule not found!')
try:
	find_internal('test.bin')
except Exception:
	logging.critical('multiple test.bins found!')
assert(False)
