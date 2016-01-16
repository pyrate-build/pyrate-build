#/bin/sh

set -e
cd $(dirname $0)
if [ -n "$(which coverage 2> /dev/null)" ]; then
	EXEC="coverage run -a ../pyrate"
else
	EXEC="../pyrate"
fi
echo "Running $EXEC"

TESTS="example1.py example2.py example3.py example4.py example5.py example6.py example7.py"
if [ -n "$(which swig 2> /dev/null)" ]; then
	TESTS="$TESTS example8.py example9.py"
fi

for EXAMPLE in $TESTS; do
	echo $EXAMPLE
	EXAMPLE_NINJA="${EXAMPLE/.py/.ninja}"
	$EXEC $EXAMPLE --output $EXAMPLE_NINJA.test
	diff -u $EXAMPLE_NINJA $EXAMPLE_NINJA.test
	echo "TEST OK"
done

if [ -n "$(which coverage 2> /dev/null)" ]; then
	mv .coverage ..
fi
