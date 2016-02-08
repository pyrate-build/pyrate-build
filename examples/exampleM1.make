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

opts_feb8a140c0d0f69d31572276363b144b := -lstdc++ -lm
exampleM1.bin: test.o foo.o
	$(LINKER_EXE) $(LINKER_EXE_FLAGS) $(opts_feb8a140c0d0f69d31572276363b144b) -o exampleM1.bin test.o foo.o

all: exampleM1.bin
.DEFAULT_GOAL := all
