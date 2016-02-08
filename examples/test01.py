assert(pyrate_version > (0, 1, 9))
assert(pyrate_version >= '0.1.10')
assert(pyrate_version != '0.0.1')
assert(pyrate_version == pyrate_version)

exe = executable('test.bin', ['test.cpp'])

find_external('abcd')
find_toolchain('abcd')
str(exe)
str(exe.build_src[0])
str(exe.build_rule)
repr(toolchain)
repr(tools)
len(tools)
for tool in tools:
	repr(tool)
assert(False)
