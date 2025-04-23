#!/usr/bin/env python3

"""Bindings to libarchive using ffi."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BONDI_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bondi-ffi-libarchive',
    version=VERSION,
    url='https://github.com/yaybondi/bondi-distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'yaybondi.ffi',
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

    keywords='libarchive bindings ffi',
    description='Python 3 ffi bindings to libarchive',
    long_description='Python 3 ffi bindings to libarchive',
)
