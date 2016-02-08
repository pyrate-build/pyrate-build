#include "foo.h"
#include <iostream>

int main()
{
#ifdef DEBUG
	std::cout << "DEBUG version!" << std::endl;
#endif
	std::cout << bar(5).f << std::endl;
	return 0;
}
