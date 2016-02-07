CXX := g++
CXX_FLAGS := -Wall -pedantic

LINKER_EXE := gcc
LINKER_EXE_FLAGS := 

-include test.o.d
test.o: test.cpp
	$(CXX) $(CXX_FLAGS) ${opts} -MMD -MT test.o -MF test.o.d -c test.cpp -o test.o

-include foo.o.d
foo.o: foo.cpp
	$(CXX) $(CXX_FLAGS) ${opts} -MMD -MT foo.o -MF foo.o.d -c foo.cpp -o foo.o

opts_9e8cf39befe9dfb32ef2884bf7903ce0 := -lstdc++
exampleM1.bin: test.o foo.o
	$(LINKER_EXE) $(LINKER_EXE_FLAGS) $(opts_9e8cf39befe9dfb32ef2884bf7903ce0) -o exampleM1.bin test.o foo.o

all: exampleM1.bin
.DEFAULT_GOAL := all
