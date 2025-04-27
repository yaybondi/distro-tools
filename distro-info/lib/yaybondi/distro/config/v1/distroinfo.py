# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2021 Tobias Koch <tobias.koch@gmail.com>
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

import collections
import contextlib
import fcntl
import json
import os
import re
import urllib.request

from yaybondi.miscellaneous.downloader import Downloader
from yaybondi.miscellaneous.userinfo import UserInfo
from yaybondi.distro.config.error import \
        DistroInfoError, ReleaseNotFoundError

class DistroInfo:

    base_url = "http://archive.yaybondi.com/config/v1"

    def refresh(self, releases=False, mirrors=False,
            overwrite_existing=False, **kwargs):
        items_to_fetch = []

        if releases:
            items_to_fetch.append("releases")
        if mirrors:
            items_to_fetch.append("mirrors")

        os.makedirs(UserInfo.config_folder(), exist_ok=True)
        downloader = Downloader()

        for item in items_to_fetch:
            filename  = "{}.json".format(item)
            src_url   = '/'.join([self.base_url, filename])
            dest_file = os.path.join(UserInfo.config_folder(), filename)

            downloader.download_tagged_file(src_url, dest_file)
        #end for
    #end function

    def list(
        self,
        supported=False,
        unsupported=False,
        unstable=False,
        *kwargs
    ):
        releases = self._load_json_file("releases")
        result   = collections.OrderedDict()

        for release_name, release_data in releases.items():
            distro_status = release_data.get("status", "supported")

            is_supported = distro_status == "supported"
            is_unstable  = distro_status == "unstable"

            if (
                (supported   and is_supported) or
                (unstable    and is_unstable)  or
                (unsupported and not (is_supported or is_unstable))
            ):
                result[release_name] = release_data
        #end for

        return result
    #end function

    def find(self, release, **kwargs):
        releases = self._load_json_file("releases")

        if release not in releases:
            raise ReleaseNotFoundError(
                "release '{}' not found, need to refresh?".format(release)
            )

        mirrors = self._load_json_file("mirrors")

        for repo_id, repo_dict in \
                releases[release].get("repositories", {}).items():
            repo_mirrors = repo_dict.get("mirrors", [])

            for i in range(len(repo_mirrors)):
                mirror_id = repo_mirrors[i]

                if mirror_id not in mirrors:
                    raise DistroInfoError(
                        "encountered unknown mirror id '{}'."
                        .format(mirror_id)
                    )

                repo_mirrors[i] = mirrors[mirror_id]
            #end for
        #end for

        return releases[release]
    #end function

    def get_git_url_and_ref(self, release, repo_name, **kwargs):
        repo_info = self.find(release).get("repositories", {}).get(repo_name)

        if not repo_info:
            raise DistroInfoError(
                "could not find information for release '{}' and repo '{}'."
                .format(release, repo_name)
            )
        #end if

        rules_url = repo_info.get("rules")
        if not rules_url:
            raise DistroInfoError(
                "could not find package rules for release '{}' and repo '{}'."
                .format(release, repo_name)
            )
        #end if

        m = re.match(
            r"""^
                (?P<url>
                    (?:(?P<proto>[^:]+)://)?
                    (?:[^/@]+@)?
                    (?:[^/@]+/)*
                    (?:[^@]+)
                )
                (?:@(?P<ref>\S+))?
            """,
            rules_url, re.VERBOSE
        )

        return (m.group("url"), m.group("ref") or "master")
    #end function

    def pick_mirror(self, release, repo_name, **kwargs):
        repo_info = self.find(release).get("repositories", {}).get(repo_name)
        if not repo_info:
            raise DistroInfoError(
                "could not find information for release '{}' and repo '{}'."
                .format(release, repo_name)
            )
        #end if

        try:
            return next(iter(repo_info.get("mirrors", [])[0].values()))[0]
        except IndexError:
            raise DistroInfoError(
                "repo '{}' for release '{}' has no mirror information listed."
                .format(repo_name, release)
            )
        #end try
    #end function

    # HELPER

    def _load_json_file(self, which):
        result = collections.OrderedDict()

        json_file = os.path.join(
            UserInfo.config_folder(), "{}.json".format(which)
        )

        if not os.path.exists(json_file):
            self.refresh(**{which: True})

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                result = json.load(
                    f, object_pairs_hook=collections.OrderedDict
                )
            #end with
        except DistroInfoError:
            raise
        except Exception as e:
            raise DistroInfoError(
                "error loading '{}': {}".format(json_file, str(e))
            )

        return result
    #end function

#end class
