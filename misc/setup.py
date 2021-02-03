#!/usr/bin/env python3

"""Bolt miscellaneous Python modules."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BOLT_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bolt-misc',
    version=VERSION,
    url='https://github.com/boltlinux/bolt-distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'boltlinux',
        'boltlinux.miscellaneous',
    ],
    package_dir={'': 'lib'},
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Cool Kids',
        'Topic :: Admin :: Configuration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bolt Linux shared modules',
    description='Python modules shared between Bolt Linux Python projects',
    long_description='Python modules shared between Bolt Linux Python projects',
)
