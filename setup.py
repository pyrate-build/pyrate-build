#!/usr/bin/env python
import os
from setuptools import setup, find_packages

version = None
dn = os.path.dirname(__file__)
with open(os.path.join(dn, 'pyrate.py')) as fp:
	for line in fp:
		if line.startswith('__version__'):
			version = line.split('=')[-1].strip().strip("'")
			break

setup(
	name='pyrate-build',
	version=version,
	description='A small python based build file generator targeting ninja',
	long_description=open(os.path.join(dn, 'README.rst')).read(),
	url='https://github.com/pyrate-build/pyrate-build',
	download_url = 'https://github.com/pyrate-build/pyrate-build/tarball/' + version,
	author='Fred Stober',
	author_email='fred.stober@gmx.de',
	license='License :: OSI Approved :: Apache Software License',
	platforms=['Operating System :: OS Independent'],
	classifiers=[
		'Development Status :: 4 - Beta',
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Build Tools',
		'License :: OSI Approved :: Apache Software License',
		'Operating System :: OS Independent',
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
