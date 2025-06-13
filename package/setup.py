#!/usr/bin/env python3

"""Bondi OS packaging scripts and tools."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BONDI_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bondi-package',
    version=VERSION,
    url='https://github.com/yaybondi/bondi-distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',

    packages=[
        'yaybondi.package',
        'yaybondi.package.bondipack',
        'yaybondi.package.deb2bondi',
    ],
    data_files=[
        ('bin', [
            'bin/bondi-pack',
            'bin/deb2bondi',
        ]),
    ],
    package_data={
        'yaybondi.package.bondipack': [
            "helpers/python.sh",
            "helpers/arch.sh",
            "relaxng/package.rng.xml",
        ],
    },
    package_dir={'': 'lib'},

    platforms=['Linux'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bondi OS packaging development',
    description='Bondi OS packaging scripts and tools',
    long_description='Bondi OS packaging scripts and tools',
)
