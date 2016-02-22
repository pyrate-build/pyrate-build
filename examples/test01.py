import logging
assert(pyrate_version > (0, 1, 9))
assert(pyrate_version >= '0.1.10')
assert(pyrate_version != '0.0.1')
assert(pyrate_version == pyrate_version)

match('*.cpp', recurse = True)
exe = executable('test.bin', ['test.cpp'])

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
repr(install(exe))
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
assert(False)
