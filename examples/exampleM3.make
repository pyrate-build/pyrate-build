CXX := g++
CXX_FLAGS := -Wall -pedantic

LINKER_EXE := gcc
LINKER_EXE_FLAGS := 

opts_9498f0e6f8d9e154c7ad200082d9549a := -O0
-include test_ddc519d468dd216db1ca93f9f80094a0.o.d
test_ddc519d468dd216db1ca93f9f80094a0.o: test.cpp
	$(CXX) $(CXX_FLAGS) $(opts_9498f0e6f8d9e154c7ad200082d9549a) -MMD -MT test_ddc519d468dd216db1ca93f9f80094a0.o -MF test_ddc519d468dd216db1ca93f9f80094a0.o.d -c test.cpp -o test_ddc519d468dd216db1ca93f9f80094a0.o

-include foo_e6ba2abe72a10e708d69c4812b7e77c7.o.d
foo_e6ba2abe72a10e708d69c4812b7e77c7.o: foo.cpp
	$(CXX) $(CXX_FLAGS) $(opts_9498f0e6f8d9e154c7ad200082d9549a) -MMD -MT foo_e6ba2abe72a10e708d69c4812b7e77c7.o -MF foo_e6ba2abe72a10e708d69c4812b7e77c7.o.d -c foo.cpp -o foo_e6ba2abe72a10e708d69c4812b7e77c7.o

exampleM2_debug.bin: test_ddc519d468dd216db1ca93f9f80094a0.o foo_e6ba2abe72a10e708d69c4812b7e77c7.o
	$(LINKER_EXE) $(LINKER_EXE_FLAGS) -lstdc++ -lm -o exampleM2_debug.bin test_ddc519d468dd216db1ca93f9f80094a0.o foo_e6ba2abe72a10e708d69c4812b7e77c7.o

opts_ee92e3fe113bee5d2f6f7c5a061c0856 := -O3
-include test_ea06e0f15a7fb50d00928f0d8923fdef.o.d
test_ea06e0f15a7fb50d00928f0d8923fdef.o: test.cpp
	$(CXX) $(CXX_FLAGS) $(opts_ee92e3fe113bee5d2f6f7c5a061c0856) -MMD -MT test_ea06e0f15a7fb50d00928f0d8923fdef.o -MF test_ea06e0f15a7fb50d00928f0d8923fdef.o.d -c test.cpp -o test_ea06e0f15a7fb50d00928f0d8923fdef.o

-include foo_b323f8bc970eb8ff180102d50bd99af1.o.d
foo_b323f8bc970eb8ff180102d50bd99af1.o: foo.cpp
	$(CXX) $(CXX_FLAGS) $(opts_ee92e3fe113bee5d2f6f7c5a061c0856) -MMD -MT foo_b323f8bc970eb8ff180102d50bd99af1.o -MF foo_b323f8bc970eb8ff180102d50bd99af1.o.d -c foo.cpp -o foo_b323f8bc970eb8ff180102d50bd99af1.o

exampleM2_release.bin: test_ea06e0f15a7fb50d00928f0d8923fdef.o foo_b323f8bc970eb8ff180102d50bd99af1.o
	$(LINKER_EXE) $(LINKER_EXE_FLAGS) -lstdc++ -lm -o exampleM2_release.bin test_ea06e0f15a7fb50d00928f0d8923fdef.o foo_b323f8bc970eb8ff180102d50bd99af1.o

all: exampleM2_debug.bin exampleM2_release.bin
.PHONY: all
default_target: exampleM2_release.bin exampleM2_debug.bin
.PHONY: default_target
.DEFAULT_GOAL := default_target
