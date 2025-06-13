#!/usr/bin/env python3

"""Bondi OS distro info."""

import os

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

VERSION = os.environ.get("BONDI_DISTRO_TOOLS_VERSION", "0.0.0")

setup(
    name='bondi-distro-info',
    version=VERSION,
    url='https://github.com/yaybondi/bondi-distro-tools',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=[
        'yaybondi.distro.config',
        'yaybondi.distro.config.v1',
    ],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', [
            'bin/bondi-distro-info',
        ]),
    ],
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Cool Kids',
        'Topic :: Admin :: Configuration',
        'Programming Language :: Python :: 3'
    ],

    keywords='Bondi OS distro versions releases mirrors',
    description='Bondi OS distro info',
    long_description='Bondi OS distro info',
)
