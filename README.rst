| |PyPI Version| |Build Status| |Coverage|

pyrate
======

**pyrate** is a small python based build file generator targeting `ninja(s)`_.

It allows to describe the build process of small projects in a very simple way
using a python based configuration file.
This description is then turned into ninja build files, that enable a very
quick turnaround of project builds.

Quick HOWTO
-----------

The following presents the necessary steps to quickly test the waters with this tool (assuming
ninja is already installed). These commands will install **pyrate**, generate the ninja
build file, build and execute a small executable:

.. code:: sh

    pip install pyrate-build
    echo -e '#include <cstdio>\nint main() { printf("Ahoy World!"); return 0; }' > test.cpp
    echo -e "executable('test', 'test.cpp')" > build.py
    pyrate
    ninja
    ./test

Installation
------------

**pyrate** is very easy to deploy - there are no particular installation steps to use it
once the single script ``pyrate.py`` is available somewhere.
It can even board the project directory of your project and simply get called from there.
The only dependency to generate the ninja build files is having a working python installation.
**pyrate** should work out of the box with all python versions between 2.4 and 3.4.
To actually build the project, ninja has to be installed as well.

The latest release version of **pyrate** can be installed from the Python Package Index with:

.. code:: sh

    pip install pyrate-build

The latest development version can be retrieved from the github repository:

.. code:: sh

    git clone https://github.com/pyrate-build/pyrate-build

Usage
-----

The quickest way to execute **pyrate** is:

.. code:: sh

    pyrate

Without any parameters, **pyrate** will use the build configuration script (*pyrate script*) named ``build.py``
and create a ninja build file called ``build.ninja``.
If another pyrate script should be used, this can be specified as a positional argument.
The name of the created ninja build file can be customized using the option ``-o`` or ``--output``.
The quick invocation shown above is therefore equivalent to the following invocation:

.. code:: sh

    pyrate --output mybuild.ninja mybuild.py

When the script is started, it first changes the current directory to the directory
containing the build configuration script, so all path names are relative to it.

.. code:: sh

    pyrate path/to/mybuild.py

will therefore create the ninja build file path/to/build.ninja

If **pyrate** is placed in a directory listed in the PATH environment variable (as automatically
done by ``pip install pyrate-build``), the build configure script can be made executable to
invoke **pyrate** automatically by starting the build config script with:

.. code:: python

    #!/usr/bin/env pyrate

*There is some experimental support for the generation of plain makefiles,
which can be switched on with* ``-M`` *or* ``--makefile``.

Build File Configuration Syntax
-------------------------------

The build configuration for **pyrate** is written in python - so the full power
of python can be used to construct and describe the build process.
Several classes, functions and variables are available to ease and customize
the configuration of the build process.

Specifying build input
~~~~~~~~~~~~~~~~~~~~~~

In general, a build input list that can be used to construct a build target takes the form:

- ``[<item1>, <item2>, ...]``

Each item can be one of the following:

-  a *string* is interpreted as a file name that is processed according to the rules specified by the packages in the ``compiler`` dictionary
-  a *build target* as returned by the functions described in `Defining build targets`_ or explicitly defined
-  an *external dependency* as returned by the functions described in `External dependencies`_ or explicitly defined
-  or any other kind of ``BuildSource`` (explained later)

Instead of a list, it is also possible to specify a space separated string of file names.
Such a string is automatically split, so the following two build input lists behave identically:

- ``"<file1> <file2> ..."``
- ``['<file1>', '<file2>', ...]``

Besides specifying file names by hand, there are many ways to get a list of files.
Common methods include calling the python function ``os.listdir`` or using the helper
function ``match`` provided by **pyrate**:

-  ``match(selector, dir_name = '.')``

This functions allows to select files from a directory using a string consisting
of black / white listing path name patterns.
The selector ``'*.cpp -test*.cpp test3.cpp *.h'`` for example selects all files ending with
‘.h’ and ‘.cpp’, with the exception of those ‘.cpp’ files that start with ‘test’ and are not
called ‘test3.cpp’.

Defining build targets
~~~~~~~~~~~~~~~~~~~~~~

There are four global helper functions to define object files, executables and libraries based
on a list of build inputs (which can be files, other targets or externals - as shown in `Specifying build input`_):

-  ``executable(name, input_list, compiler_opts = None, linker_opts = None)``
-  ``shared_library(name, input_list, compiler_opts = None, linker_opts = None)``
-  ``static_library(name, input_list, compiler_opts = None, linker_opts = None)``
-  ``object_file(name, input_list, compiler_opts = None)``

Each function returns a build target object, that can be used as input / dependency of another function.
If multiple executables / libraries or object files with the same name but different inputs / options
are defined, **pyrate** will ensure that the output will have a unique name
(by appending a hash based suffix as needed). More details about this is available in `Target Collision Avoidance`_.

These functions exist as global functions and as member functions of a so-called build context,
that describes how these functions are processed. The global functions are just executing
within the default build context.

By default, all build targets that are defined by the above functions (or direct API calls) are built.
In order to select only certain default targets, the global variable ``default_targets`` can be used:

-  ``default_targets = [<target>,...]`` (list of targets), ``<target>`` (single target) or ``None`` (all targets are built)

External dependencies
~~~~~~~~~~~~~~~~~~~~~

The build environment / dependencies on external packages can be expressed using the
following functions / variables:

-  ``find_external(name, ...)``

The function ``find_external`` searches for some external dependency (built-in, pkg-config package
or self-defined) with the given name and returns either None or a representation of the dependency.
The function takes additional positional and keyword arguments that depend on the external package.
A common argument for this function is a version selector, that is supplied through a global variable:

-  ``version``

The comparison between this variable (eg. ``version >= 4.1``) and a version specifier
will return a function that can be used to check the expression and is used by the external package finder.
A version specifier can be a string (``'0.1.2'``) or tuple (``(0, 1, 2)``) with an arbitrary number
of subversion separators, or a floating point number (``1.2``).
This allows for example to write ``find_external('clang', version >= 3.5)`` to discover a clang installation with version 3.5 or later.

Since ``find_external`` also integrates with ``pkg-config``, a large number of external packages is
available - in addition to a handful of builtin external packages with special implementation features.
It is also possible to add new packages that are recognized.
A list of the builtin packages is presented in `Externals`_.

In order to simplify the creation of external packages that already provide a build configuration tool
to query version, linker or compiler options, **pyrate** provides the function:

-  ``create_external(name, build_helper, ...)``

It requires the user to define a name for the external package and to supply the build configuration tool.
The values of additional parameters are interpreted as command line options for the build configuration tool.
The name of these additional parameters specify the name of the
rule that gets supplied with the flags given by the output of the build configuration tool.
However there are four parameters that have a special meaning:

-  ``version_query`` - similar to the other parameters, the value of this parameter is used as build
   configuration tool option to determine the current version of the external package.
   As a consequence of providing this option, the resulting external package will support the parameter ``version``.
-  ``version_parser`` - this parameter allows to supply a function that parses the version string
   provided by the build configuration tool and is only used if ``version_query`` is given.
-  ``version`` - specifies required version (eg. ``version = version >= 11.5``) and can only be used if
   ``version_query`` is given
-  ``link = opts`` is equivalent to specifying ``link_shared = opts``, ``link_static = opts`` and
   ``link_exe = opts``

The following example recreates the builtin external package for wxWidgets:

.. code:: python

    my_wxwidgets = create_external('wxwidgets', build_helper = 'wx-config',
        version_query = '--version', link = '--libs', compile_cpp = '--cxxflags')

Configuration of the build environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A build context allows for example to define implicit dependencies that are automatically
included in all generated object files, executables or libraries (via ``implicit_input_*`` options).
It is also possible to set base directories for the output generated by the build (via ``basedir_*`` options).

The default context used by the global functions presented in `Defining build targets`_
can be set or accessed using the variable:

-  ``default_context = Context(...)``

An instance of such a build context is created with:

-  ``Context(...)`` - the most important parameters are:

   * ``implicit_input``, ``implicit_object_input``, ``implicit_static_library_input``,
     ``implicit_shared_library_input`` and ``implicit_executable_input``
   * ``basedir``, ``basedir_object_file``, ``basedir_static_library``, ``basedir_shared_libray``,
     ``basedir_executable``

These parameters can also be changed on an existing context instance:

.. code:: python

    default_context.basedir = 'build'

Finally, the used default compilers can be configured via the global variable

-  ``compiler``

This is a dictionary that contains links to external packages that provide the basic rules
and parameters that are used to build the source. This dictionary can be modified, but should
not be overwritten.

It is possible to query the current version of **pyrate** via the variable:

-  ``pyrate_version``

this allows to ensure a compatible version of **pyrate** with something along the lines of:

.. code:: python

    assert(pyrate_version > '0.1.8')

Target Collision Avoidance
~~~~~~~~~~~~~~~~~~~~~~~~~~

As explained in `Defining build targets`_, **pyrate** will always ensure that targets with different inputs / options but
same name will generate different output files (by appending a hash based suffix as needed).
However it is possible to switch off the renaming of colliding targets for a **unique** target.
Beware: Having two different targets that switch off the renaming with the option
``no_rename = True`` will abort the build file generation.
The following build configuration file:

.. code:: python

    ex1 = executable('example.bin', 'test.cpp', compiler_opts = '-O1')
    ex2 = executable('example.bin', 'test.cpp', compiler_opts = '-O2')
    ex3 = executable('example.bin', 'test.cpp', compiler_opts = '-O3')
    ex4 = executable('example.bin', 'test.cpp', compiler_opts = '-O2', no_rename = True)
    print('hash(ex1) = %s' % ex1.get_hash())
    print('hash(ex2) = %s' % ex2.get_hash())
    print('hash(ex3) = %s' % ex3.get_hash())
    print('hash(ex4) = %s' % ex4.get_hash())

will result (for example in an linux environment) in the generation of **three** object files named
``test_<hash1>.o``, ``test_<hash2>.o``, ``test_<hash3>.o``, since there are only three different
settings used during the compilation of ``test.cpp``.
During the linking step, these object files will generate **three** binaries named
``example.bin``, ``example_<hash4>.bin``, ``example_<hash5>.bin``.
Where ``example.bin`` was compiled with the compiler option '-O2'. To identify which
target belong to which hash, the ``<target_obj>.get_hash()`` function can be used.

However it is **strongly** recommended to always ensure collision free names for executables
and shared / static libraries.

Externals
---------

Currently the following builtin externals are supported (listed with all possible ``find_external`` arguments):

- ``gcc``

  * ``version`` - specifies required version (eg. ``version >= 5.2``)
  * ``std`` - C/C++ language standard version (eg. ``'gnu++14'`` or ``'latest'``).
    A property with the same name allows to also set this value on an existing external (eg. ``compiler['C++'].std = 'latest'``).
  * ``compile_cpp`` - name of the executable
  * ``compile_cpp_opts`` - options that are used during the compilation stage
  * ``link_static_opts``, ``link_shared_opts``, ``link_exe_opts`` - options that are used during the linking stage

- ``clang``

  * ``version`` - specifies required version (eg. ``version > 3.5``)
  * ``std`` - C/C++ language standard version (eg. ``'c++1y'`` or ``'latest'``).
    A property with the same name allows to also set this value on an existing external (eg. ``compiler['C++'].std = 'latest'``).
  * ``compile_cpp`` - name of the executable
  * ``compile_cpp_opts`` - options that are used during the compilation stage
  * ``link_static_opts``, ``link_shared_opts``, ``link_exe_opts`` - options that are used during the linking stage

- ``swig`` - The swig package also provides the member function ``wrapper`` to describe the generation of automated interface code

  * ``version`` - specifies required version (eg. ``version > '3.0.2'``)
  * ``wrapper(target_language, library_name, interface_filename, libs = [<targets>...])``

- ``pthread`` - posix thread library

The following list contains all builtin externals with a single ``find_external`` parameter ``version``,
that specifies the required version (eg. ``version >= 2.6``):

- ``fltk`` - FLTK GUI Library
- ``llvm`` - LLVM compiler infrastructure libraries
- ``odbc`` - Open Database Connectivity middleware
- ``root`` - Library for large scale data analysis
- ``wx`` - wxWidgets GUI Toolkit

Many more externals are available through the integration with ``pkg-config``. The full list
of available packages on a system can be queried with:

.. code:: sh

    pkg-config --list-all

All packages listed in that overview can be accessed with the ``find_external`` function.

Example
-------

The basic **pyrate** build configuration file for a simple C++ project with a single source file
producing a single executable looks like this:

.. code:: python

    executable('test', ['test.cpp'])

A more complicated example is presented in the following code fragment. It demonstrates how to

- change the default compiler to clang,
- define a native static and dynamic library from a set of files selected by wildcards,
- generate several executables accessing to the shared library and
- generate a wrapper library to access the C++ library from python (if swig is available).

.. code:: python

    clang = find_external('clang', version >= 3.7, std = 'c++11')
    if clang:
        compiler['C++'] = clang

    lib_files = match("*.cpp -test* -mylib.cpp")
    static_library('libFoo', lib_files, compiler_opts = '-O3')
    lib_reference = shared_library('libFoo', lib_files)

    python = find_external('python', version > 2)
    swig = find_external('swig')
    if swig and python:
        swig.wrapper('python', 'mylib', 'mylib.i', libs = [lib_reference])

    for fn in match("test*.cpp"):
        executable(fn.replace('.cpp', '.exe'), [fn, lib_reference])

Many more examples with an increasing level of complexity are available in the `github`_ repository.

.. _ninja(s): https://github.com/ninja-build/ninja

.. _github: https://github.com/pyrate-build/pyrate-build/tree/master/examples

.. |PyPI Version| image:: https://badge.fury.io/py/pyrate-build.svg
   :target: https://badge.fury.io/py/pyrate-build
   :alt: Latest PyPI version

.. |Build Status| image:: https://travis-ci.org/pyrate-build/pyrate-build.svg?branch=master
   :target: https://travis-ci.org/pyrate-build/pyrate-build
   :alt: Build Status

.. |Coverage| image:: https://codecov.io/github/pyrate-build/pyrate-build/coverage.svg?branch=master
   :target: https://codecov.io/github/pyrate-build/pyrate-build?branch=master


.. image:: https://badges.gitter.im/pyrate-build/pyrate-build.svg
   :alt: Join the chat at https://gitter.im/pyrate-build/pyrate-build
   :target: https://gitter.im/pyrate-build/pyrate-build?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge