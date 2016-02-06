build_output = ['makefile']
ex_d = executable('exampleA1_debug.bin', 'test.cpp foo.cpp', compiler_opts = '-O0')
ex_r = executable('exampleA1_release.bin', 'test.cpp foo.cpp', compiler_opts = '-O3')
default_targets = ex_r
