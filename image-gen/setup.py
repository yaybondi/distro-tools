#!/usr/bin/env python3

"""Bolt OS image generator tool."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BOLT_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bolt-image',
    version=VERSION,
    url='https://github.com/boltlinux/image-generator',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'boltlinux.osimage',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', ['bin/bolt-image']),
    ],
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bolt Linux image generator',
    description='Bolt Linux image generator tool',
    long_description='Bolt Linux image generator tool',
)
