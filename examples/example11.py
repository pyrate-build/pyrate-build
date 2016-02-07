default_context.basedir = 'build'
default_context.basedir_object_file = 'build/obj'
exe = executable('subdir/example11.bin', 'test.cpp foo.cpp')
install(exe)
