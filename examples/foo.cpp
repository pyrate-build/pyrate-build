struct FooStruct
{
	FooStruct(int _f) : f(_f) {}
	int f;
};

FooStruct bar(int x)
{
	return FooStruct(x + 4);
}
