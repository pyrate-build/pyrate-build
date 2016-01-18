#/bin/sh

set -e
cd $(dirname $0)

if [ -n "$1" ]; then
	EXEC="$1 ../pyrate"
else
	EXEC="../pyrate"
fi
if [ -n "$(which coverage 2> /dev/null)" ]; then
	EXEC="coverage run -a $EXEC"
fi
echo "Running $EXEC"

run_test() {
	echo $EXAMPLE
	EXAMPLE_NINJA="${EXAMPLE/.py/.ninja}"
	$EXEC $EXAMPLE --output $EXAMPLE_NINJA.test
	diff -u $EXAMPLE_NINJA $EXAMPLE_NINJA.test
	echo "TEST OK"
}

run_test_make() {
	echo $EXAMPLE
	EXAMPLE_MAKE="${EXAMPLE/.py/.make}"
	$EXEC $EXAMPLE --output $EXAMPLE_MAKE.test
	diff -u $EXAMPLE_MAKE $EXAMPLE_MAKE.test
	echo "TEST OK"
}

TESTS="example01.py example02.py example03.py example04.py example05.py"
TESTS="$TESTS example06.py example07.py example08.py example09.py"
for EXAMPLE in $TESTS; do
	run_test $EXAMPLE
done

for EXAMPLE in exampleM1.py; do
	run_test_make $EXAMPLE
done

set +e

TESTS=""
if [ -n "$(which swig 2> /dev/null)" ]; then
	TESTS="$TESTS exampleS1.py exampleS2.py"
fi
if [ -n "$(which clang 2> /dev/null)" ]; then
	TESTS="$TESTS exampleS2.py"
fi
for EXAMPLE in $TESTS; do
	run_test $EXAMPLE
done

if [ -n "$(which coverage 2> /dev/null)" ]; then
	mv .coverage ..
fi
