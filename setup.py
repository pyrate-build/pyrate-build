#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
	name='pyrate-build',
	version='0.1.0',
	description='A small python based build file generator targeting ninja',
	long_description=open('README.rst').read(),
	url='https://github.com/pyrate-build/pyrate-build',
	download_url = 'https://github.com/pyrate-build/pyrate-build/tarball/0.1.0',
	author='Fred Stober',
	author_email='fred.stober@gmx.de',
	license='License :: OSI Approved :: Apache Software License',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Build Tools',
		'License :: OSI Approved :: Apache Software License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.6',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.2',
		'Programming Language :: Python :: 3.3',
		'Programming Language :: Python :: 3.4',
		'Programming Language :: Python :: 3.5',
	],

	# What does your project relate to?
	keywords='ninja build development',
	py_modules=["pyrate"],
	entry_points={
		'console_scripts': [
			'pyrate=pyrate:main',
		],
	},
)
