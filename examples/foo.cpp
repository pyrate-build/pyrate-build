#include "foo.h"

FooStruct::FooStruct(int _f) : f(_f)
{
}

FooStruct bar(int x)
{
	return FooStruct(x + 4);
}
