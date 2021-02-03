#!/usr/bin/env python3

"""Bolt OS repository index generator."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BOLT_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bolt-repository',
    version=VERSION,
    url='https://github.com/tobijk/bolt-package',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'boltlinux.repository',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', [
            'bin/bolt-repo-index',
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

    keywords='Bolt Linux package repository index',
    description='Bolt Linux package repository index generator',
    long_description='Bolt Linux package repository index generator',
)
