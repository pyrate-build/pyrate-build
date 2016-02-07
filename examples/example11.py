default_context.basepath = 'build'
default_context.basepath_object_file = 'build/obj'
exe = executable('subdir/example11.bin', 'test.cpp foo.cpp')
install(exe)
