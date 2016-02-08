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
if [ -n "$(python --version 2>&1 | grep "Python 2.6")" ]; then
	export TESTOLDIMPORTS="1"
fi
echo "Running $EXEC"

run_test() {
	echo $EXAMPLE
	EXAMPLE_NINJA="${EXAMPLE/.py/.ninja}"
	$EXEC $EXAMPLE --output $EXAMPLE_NINJA.test
	diff -u $EXAMPLE_NINJA $EXAMPLE_NINJA.test
	rm $EXAMPLE_NINJA.test
	echo "TEST OK"
}

run_project() {
	echo $EXAMPLE
	EXAMPLE_NINJA="${EXAMPLE/.py/.ninja}"
	mv $EXAMPLE_NINJA $EXAMPLE_NINJA.ref
	$EXEC $EXAMPLE
	mv $EXAMPLE_NINJA $EXAMPLE_NINJA.test
	mv $EXAMPLE_NINJA.ref $EXAMPLE_NINJA
	diff -u $EXAMPLE_NINJA $EXAMPLE_NINJA.test
	rm $EXAMPLE_NINJA.test
	echo "TEST OK"
}

run_test_make() {
	echo $EXAMPLE
	EXAMPLE_MAKE="${EXAMPLE/.py/.make}"
	$EXEC $EXAMPLE --output $EXAMPLE_MAKE.test
	diff -u $EXAMPLE_MAKE $EXAMPLE_MAKE.test
	rm $EXAMPLE_MAKE.test
	echo "TEST OK"
}

run_test_general() {
	echo $EXAMPLE
	EXAMPLE_GENERAL="${EXAMPLE/.py/}"
	mv $EXAMPLE_GENERAL.makefile $EXAMPLE_GENERAL.makefile.ref
	mv $EXAMPLE_GENERAL.ninja $EXAMPLE_GENERAL.ninja.ref
	$EXEC $EXAMPLE --output $EXAMPLE_GENERAL.test
	mv $EXAMPLE_GENERAL.makefile $EXAMPLE_GENERAL.makefile.test
	mv $EXAMPLE_GENERAL.makefile.ref $EXAMPLE_GENERAL.makefile
	mv $EXAMPLE_GENERAL.ninja $EXAMPLE_GENERAL.ninja.test
	mv $EXAMPLE_GENERAL.ninja.ref $EXAMPLE_GENERAL.ninja
	diff -u $EXAMPLE_GENERAL.makefile $EXAMPLE_GENERAL.makefile.test
	diff -u $EXAMPLE_GENERAL.ninja $EXAMPLE_GENERAL.ninja.test
	rm $EXAMPLE_GENERAL.makefile.test $EXAMPLE_GENERAL.ninja.test
	echo "TEST OK"
}

$EXEC --version
TESTS="../examples/example01.py example01.py example02.py example03.py example04.py example05.py"
TESTS="$TESTS example06.py example07.py example08.py example09.py example10.py example11.py"
for EXAMPLE in $TESTS; do
	run_test $EXAMPLE
done

for EXAMPLE in exampleM1.py exampleM2.py; do
	run_test_make $EXAMPLE
done

for EXAMPLE in exampleG1.py exampleG2.py; do
	run_test_general $EXAMPLE
done

for EXAMPLE in project1/build.py project1/foo/build.py; do
	run_project $EXAMPLE
done

cp example01.py build.py
$EXEC
diff -u example01.ninja build.ninja
rm build.py build.ninja

cp exampleM1.py build.py
$EXEC -M
diff -u exampleM1.make Makefile
rm build.py Makefile

echo
echo "non essential tests"
echo
set +e

for TEST in test01.py test02.py test03.py test04.py test05.py; do
	$EXEC $TEST 2> /dev/null
done

$EXEC example01.py example02.py 2> /dev/null

TESTS=""
if [ -n "$(which swig 2> /dev/null)" ]; then
	TESTS="$TESTS exampleS1.py"
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

rm -f *.o *.d
echo "============"
