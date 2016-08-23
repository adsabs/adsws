# -*- coding: utf-8 -*-
#


# NOTE: for now this doesn't do much (it is not meant) to be installable
# as a python package

try:
    from setuptools import setup
except:
    from distutils.core import setup

import os
import re
import sys

from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main()
        sys.exit(errno)


# Get the version string.  Cannot be done with import!
with open(os.path.join('adsws', 'version.py'), 'rt') as f:
    version = re.search(
        '__version__\s*=\s*"(?P<version>.*)"\n',
        f.read()
    ).group('version')

setup(
    name='adsws',
    packages=['adsws'],
    version=version,
    description='ADS Web Services',
    author='adslabs.org',
    url='https://github.com/adsabs/adsws',
    keywords=['api', 'web services'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Utilities',
    ],
    tests_require=[
        'pytest', 'pytest-cache', 'pytest-cov', 'pytest-pep8', 'cloud',
        'coverage'
    ],
    cmdclass={'test': PyTest},
    install_requires=['configobj>4.7.0', 'six'],
    long_description="""\
ADS Web Services
-------------------------------------

Astrophysics Data System (http://adslabs.org) provides the search and
discovery of scientific papers for astrophysics, astronomy and related fields

Our services are accessible through the API. And this is the software
that we use to expose them!
"""
)
