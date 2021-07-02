#!/usr/bin/env python3

"""Bolt OS distro info."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BOLT_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bolt-distro-info',
    version=VERSION,
    url='https://github.com/boltlinux/bolt-distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'boltlinux.archive.config',
        'boltlinux.archive.config.v1',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', [
            'bin/bolt-distro-info',
        ]),
    ],
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Cool Kids',
        'Topic :: Admin :: Configuration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bolt Linux distro versions releases mirrors',
    description='Bolt Linux distro info',
    long_description='Bolt Linux distro info',
)
