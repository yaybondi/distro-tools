#!/usr/bin/env python3

"""Bondi OS image generator tool."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BONDI_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bondi-image',
    version=VERSION,
    url='https://github.com/yaybondi/image-generator',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'yaybondi.osimage',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', ['bin/bondi-image']),
    ],
    package_data={
        'yaybondi.osimage': [
            "customize/ollie/build-essential",
            "customize/ollie/minimal",
            "package/common/tarball",
        ],
    },
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bondi OS image generator',
    description='Bondi OS image generator tool',
    long_description='Bondi OS image generator tool',
)
