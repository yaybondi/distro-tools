# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Tobias Koch <tobias.koch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import hashlib
import itertools
import logging
import os
import re

from boltlinux.error import BoltError
from boltlinux.ffi.libarchive import ArchiveFileReader
from boltlinux.miscellaneous.downloader import Downloader
from boltlinux.miscellaneous.userinfo import UserInfo

from boltlinux.package.boltpack.debianpackagemetadata import \
        DebianPackageMetaData, DebianPackageVersion
from boltlinux.package.deb2bolt.inrelease import InReleaseFile

LOGGER = logging.getLogger(__name__)

class DebianPackageDict:

    def __init__(self):
        self._dict = {}

    def keys(self):
        for version in self._dict.keys():
            yield DebianPackageVersion(version)

    def items(self):
        for version, pkg_obj in self._dict.items():
            yield DebianPackageVersion(version), pkg_obj

    def __iter__(self):
        for version in self._dict.keys():
            yield DebianPackageVersion(version)

    def __getitem__(self, key):
        return self._dict[str(key)]

    def __setitem__(self, key, value):
        self._dict[str(key)] = value

    def __contains__(self, key):
        return str(key) in self._dict

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def setdefault(self, key, default=None):
        return self._dict.setdefault(key, default)

#end class

class DebianPackageCache:

    SOURCE = 1
    BINARY = 2

    def __init__(self, release, arch="amd64", components=None, cache_dir=None,
            security_enabled=True, updates_enabled=False, keyring=None):
        self.release = release
        self.arch = arch

        if not components:
            components = ["main", "contrib", "non-free"]
        self.components = components

        if not cache_dir:
            cache_dir = os.path.realpath(
                os.path.join(UserInfo.cache_dir(), "debian")
            )

        self._cache_dir = cache_dir
        self._keyring = keyring

        self.sources_list = [
            (
                "debian",
                "http://ftp.debian.org/debian/dists/{}"
                    .format(release)
            )
        ]

        if security_enabled:
            self.sources_list.append(
                (
                    "debian-security",
                    "http://security.debian.org/debian-security/dists/{}-security"  # noqa:
                        .format(release)
                )
            )
        #end if

        if updates_enabled:
            self.sources_list.append(
                (
                    "debian-updates",
                    "http://ftp.debian.org/debian/dists/{}-updates"
                        .format(release)
                )
            )
        #end if

        self.source = {}
        self.binary = {}
    #end function

    def open(self):
        self._parse_package_list()

    def update(self, what=SOURCE|BINARY):  # noqa:
        pkg_types = []

        if what & self.SOURCE:
            pkg_types.append("source")
        if what & self.BINARY:
            pkg_types.extend(["binary-{}".format(self.arch), "binary-all"])

        LOGGER.info(
            'updating package cache for release "{}" (this may take a while).'
            .format(self.release)
        )

        for suite, base_url in self.sources_list:
            inrelease = self._load_inrelease_file(suite, base_url)

            for component, type_ in itertools.product(
                    self.components, pkg_types):
                cache_dir = os.path.join(self._cache_dir, "dists",
                    self.release, suite, component, type_)

                if not os.path.isdir(cache_dir):
                    os.makedirs(cache_dir)

                source_url = None

                for ext in [".gz", ".xz"]:
                    if type_ == "source":
                        filename = "Sources" + ext
                        source_path = f"{component}/source/{filename}"
                        target_path = os.path.join(cache_dir, filename)
                    else:
                        filename = "Packages" + ext
                        source_path = f"{component}/{type_}/{filename}"
                        target_path = os.path.join(cache_dir, filename)
                    #end if

                    try:
                        sha256sum = inrelease.hash_for_filename(source_path)
                        source_url = "{}/{}".format(
                            base_url, inrelease.by_hash_path(source_path)
                        )
                    except KeyError:
                        continue
                #end for

                if not source_url:
                    raise BoltError(
                        'unable to locate index file for "{}" in "{}" '
                        'suite'.format(type_, suite)
                    )

                new_tag = sha256sum[:16]

                # Check if resource has changed.
                if not os.path.islink(target_path):
                    old_tag = ""
                else:
                    old_tag = os.path.basename(os.readlink(target_path))

                if old_tag == new_tag:
                    continue

                digest = hashlib.sha256()

                # Download file into symlinked blob.
                try:
                    Downloader().download_named_tag(
                        source_url,
                        target_path,
                        new_tag,
                        digest=digest,
                        permissions=0o0644
                    )
                except BoltError as e:
                    raise BoltError(
                        "failed to retrieve {}: {}".format(source_url, str(e))
                    )
                #end try

                # Remove old blob.
                if old_tag:
                    os.unlink(
                        os.path.join(os.path.dirname(target_path), old_tag)
                    )
                #end if

                # Verify signature trail through sha256sum.
                if digest.hexdigest() != sha256sum:
                    raise BoltError(
                        "wrong hash for '{}'.".format(source_url)
                    )
                #end if
            #end for
        #end for

        self._parse_package_list(what=what)
    #end function

    # PRIVATE

    def _parse_package_list(self, what=SOURCE|BINARY):  # noqa:
        pkg_types = []

        if what & self.SOURCE:
            pkg_types.append("source")
            self.source.clear()
        if what & self.BINARY:
            pkg_types.extend(["binary-{}".format(self.arch), "binary-all"])
            self.binary.clear()

        LOGGER.info(
            '(re)loading package cache for release "{}", please hold on.'
            .format(self.release)
        )

        for (suite, base_url), component, type_ in itertools.product(
                self.sources_list, self.components, pkg_types):
            found = False

            for ext in [".gz", ".xz"]:
                if type_ == "source":
                    meta_gz = "Sources" + ext
                    cache = self.source
                else:
                    meta_gz = "Packages" + ext
                    cache = self.binary
                #end if

                meta_file = os.path.join(self._cache_dir, "dists",
                    self.release, suite, component, type_, meta_gz)

                if os.path.exists(meta_file):
                    found = True
                    break
            #end for

            if not found:
                continue

            with ArchiveFileReader(meta_file, raw=True) as archive:
                try:
                    next(iter(archive))
                except StopIteration:
                    # The archive is empty.
                    continue

                buf = archive.read_data().decode("utf-8")

                pool_base = re.match(
                    r"^(?P<pool_base>https?://.*?)/dists/.*$", base_url
                ).group("pool_base")

                for chunk in re.split(r"\n\n+", buf, flags=re.MULTILINE):
                    chunk = chunk.strip()
                    if not chunk:
                        continue

                    meta_data = DebianPackageMetaData(
                        chunk, base_url=pool_base)

                    meta_data["Suite"]     = suite
                    meta_data["Component"] = component

                    pkg_name    = meta_data["Package"]
                    pkg_version = meta_data["Version"]

                    cache\
                        .setdefault(pkg_name, DebianPackageDict())\
                        .setdefault(pkg_version, meta_data)
                #end for
            #end with
        #end for

        return (self.source, self.binary)
    #end function

    def _load_inrelease_file(self, suite, base_url):
        cache_dir = os.path.join(self._cache_dir, "dists", self.release, suite)
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)

        downloader = Downloader()

        source = "{}/{}".format(base_url, "InRelease")
        target = os.path.join(cache_dir, "InRelease")

        if not os.path.islink(target):
            old_tag = ""
        else:
            old_tag = os.path.basename(os.readlink(target))

        new_tag = downloader.tag(source)
        if old_tag != new_tag:
            downloader.download_named_tag(
                source, target, new_tag, permissions=0o0644
            )
            if old_tag:
                os.unlink(os.path.join(cache_dir, old_tag))
        #end if

        inrelease = InReleaseFile.load(os.path.join(cache_dir, new_tag))

        if self._keyring:
            if not os.path.exists(self._keyring):
                raise BoltError(
                    "keyring file '{}' not found, cannot check '{}' signature."
                    .format(self._keyring, target)
                )
            #end if

            if not inrelease.valid_signature(keyring=self._keyring):
                raise BoltError(
                    "unable to verify the authenticity of '{}'"
                    .format(target)
                )
            #end if
        #end if

        return inrelease
    #end function

#end class
