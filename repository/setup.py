#!/usr/bin/env python3

"""Bondi OS repository index generator."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BONDI_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bondi-repository',
    version=VERSION,
    url='https://github.com/yaybondi/distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'yaybondi.repository',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', [
            'bin/bondi-repo-index',
        ]),
    ],
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bondi OS package repository index',
    description='Bondi OS package repository index generator',
    long_description='Bondi OS package repository index generator',
)
