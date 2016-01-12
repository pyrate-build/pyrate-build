| |PyPI Version| |Build Status|

pyrate
======

**pyrate** is a small python based build file generator targeting
`ninja(s)`_.

It allows to describe the build process of small projects in a very simple way.
This description is then turned into ninja build files, that enable a very quick turnaround of project builds.

Installation
------------

**pyrate** is very easy to deploy - there are no particular installation steps to use it!
It can even board the project directory of your project and simply get called from there.
The only dependency of the software is having a working python installation.
**pyrate** should work without modifications with all python versions between 2.4 and 3.4.

It is also possible to get the latest version from the Python Package
Index with:

.. code:: sh

    pip install pyrate-build

Usage
-----

**pyrate** can be directly invoked with the name of the build configure script
and the optional parameter ‘–output’ to specify the name of the generated ninja build file.

.. code:: sh

    pyrate.py --output mybuild.ninja mybuild.py

When the script is started, it first changes the current directory to the directory
containing the build configuration script, so all path names are relative to it.

If **pyrate** is placed in a directory listed in the PATH environment variable, the
build configure script can be made executable to invoke **pyrate** automatically by
starting the build config script with:

.. code:: python

    #!/usr/bin/env pyrate.py

Syntax
------

The build configuration script is written in python. Several functions and variables are
available as global variables to ease the configuration of the build process.

-  ``match(selector, dir_name = '.')``

The function *match* allows to select files from a directory using a string consisting of
black / whilelisting pathname patterns.
The selector ``'*.cpp -test*.cpp test3.cpp *.h'`` for example selects all files ending with
‘.h’ and ‘.cpp’, with the exception of those ‘.cpp’ files that start with ‘test’ and are not
called ‘test3.cpp’.

There are three helper functions to define executables and libraries based on
a list of inputs (which can be files, other targets or externals)

-  ``executable(name, input_list, linker_opts = None, compiler_opts = None)``
-  ``shared_library(name, input_list, linker_opts = None, compiler_opts = None)``
-  ``static_library(name, input_list, linker_opts = None, compiler_opts = None)``

By default, all targets that are defined by these functions (or direct API calls) are built.
In order to select these default targets, the global variable *default* can be set to a list
of targets

-  ``default = [<target>,...]`` (``None`` == all targets are built)

The build environment and dependencies on external packages can be expressed using the
following functions / variables:

-  ``find_external(name, ...)``

The function *find\_external* searches for some external dependency (built-in or self-defined)
with the given name and returns either None or a representation of the dependency.
The function takes additional positional and keyword arguments that depend on the external package.
A common argument for this function is a version selector, that is supplied through a global variable:

-  ``version``

The comparisons with this variable (eg. ``version >= 4.1``) will create new version instance
that is used by the external package finder. This allows for example to write
``find_external('clang', version >= 3.5)`` to discover a clang installation with version 3.5 or later.
Currently only a small number of builtin external packages are available (listed under **Externals**),
but it is easy to add new packages that are recognized.

Finally, the used default compilers can be configured via the global variable

-  ``compiler``

This is a dictionary that contains links to external packages that provide the basic rules
and parameters that are used to build the source.

Externals
---------

Currently the following builtin externals are supported (listed with
possible ``find_external`` arguments):

- gcc

  * ``version`` - specifies required version (eg. ``version >= 5.2``)
  * ``std`` - C/C++ language standard version (eg. gnu++14)
  * ``compiler_flags`` - flags that are used during the compilation stage
  * ``static_flags``, ``shared_flags``, ``exe_flags`` - flags that are used during the linking stage

- clang

  * ``version`` - specifies required version (eg. ``version > 3.5``)
  * ``std`` - C/C++ language standard version (eg. c++14)
  * ``compiler_flags`` - flags that are used during the compilation stage
  * ``static_flags``, ``shared_flags``, ``exe_flags`` - flags that are used during the linking stage

- python

  * ``version`` - specifies required version (eg. ``version >= 2.6``)

- swig - The swig package also provides a member function to describe the generation of automated interface code

  * ``version`` - specifies required version (eg. ``version > '3.0.2'``)
  * ``wrapper(target_language, library_name, interface_filename, libs = [<targets>...])``

Example
-------

A trivial example for a C++ project is the following build configuration
file:

.. code:: python

    executable('test', ['test.cpp'])

The following is a more complicated example that overrides the default compiler,
defines a native static and dynamic library and several executables.
In case the swig and python package are found, it also creates a python interface
that uses the dynamic library.

.. code:: python

    compiler['C++'] = find_external('clang', version >= 3.7, std = 'c++11')

    libFiles = match("*.cpp -test* -mylib.cpp")
    static_library('libUser', libFiles, compiler_opts = '-O3')
    libUser = shared_library('libUser', libFiles)

    python = find_external('python')
    swig = find_external('swig')
    if swig and python:
            swig.wrapper('python', 'mylib', 'mylib.i', libs = [libUser])

    for fn in match("test*.cpp"):
            executable(fn.replace('.cpp', '.exe'), [fn, libUser])


.. _ninja(s): https://github.com/ninja-build/ninja

.. |PyPI Version| image:: https://badge.fury.io/py/pyrate-build.svg
   :target: https://badge.fury.io/py/pyrate-build
   :alt: Latest PyPI version
.. |Build Status| image:: https://travis-ci.org/pyrate-build/pyrate-build.svg?branch=master
   :target: https://travis-ci.org/pyrate-build/pyrate-build
   :alt: Build Status
