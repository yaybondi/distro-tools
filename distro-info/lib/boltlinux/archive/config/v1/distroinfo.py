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
import urllib.request

from boltlinux.miscellaneous.userinfo import UserInfo
from boltlinux.archive.config.error import \
        DistroInfoError, ReleaseNotFoundError

class DistroInfo:

    base_url = "http://archive.boltlinux.org/config/v1"

    def __init__(self):
        self._dict = {}

    def refresh(self, releases=False, mirrors=False,
            overwrite_existing=False, **kwargs):
        items_to_fetch = []

        if releases:
            items_to_fetch.append("releases")
        if mirrors:
            items_to_fetch.append("mirrors")

        # Reset _dict so that fetching is not being short-cut.
        self._dict.clear()

        for item in items_to_fetch:
            os.makedirs(UserInfo.config_folder(), exist_ok=True)

            filename  = "{}.json".format(item)
            src_url   = '/'.join([self.base_url, filename])
            data      = self._fetch_json(src_url)
            dest_file = os.path.join(UserInfo.config_folder(), filename)

            # Run the appropriate merge helper.
            getattr(self, "_merge_{}".format(item))(
                data, dest_file, overwrite_existing=overwrite_existing
            )
    #end function

    def list(self, supported=False, unsupported=False, *kwargs):
        releases = self._load_json_file("releases")
        result   = collections.OrderedDict()

        for release_name, release_data in releases.items():
            is_supported = \
                release_data.get("status", "supported") in [None, "supported"]
            if supported and is_supported:
                result[release_name] = release_data
            if unsupported and not is_supported:
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

    def get_git_url(self, release, repo_name, **kwargs):
        repo_info = self.find(release).get("repositories", {}).get(repo_name)
        if not repo_info:
            raise DistroInfoError(
                "could not find information for release '{}' and repo '{}'."
                .format(release, repo_name)
            )
        #end if

        pkg_rules = repo_info.get("rules")
        if not pkg_rules:
            raise DistroInfoError(
                "could not find package rules for release '{}' and repo '{}'."
                .format(release, repo_name)
            )
        #end if

        return pkg_rules
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

    def _fetch_json(self, url, connection_timeout=30):
        try:
            with urllib.request.urlopen(url, timeout=connection_timeout) \
                    as response:
                return json.loads(
                    response.read().decode("utf-8"),
                    object_pairs_hook=collections.OrderedDict
                )
        except urllib.error.URLError as e:
            raise DistroInfoError(
                "error retrieving '{}': {}"
                .format(url, str(e))
            )
        except UnicodeDecodeError as e:
            raise DistroInfoError(
                "failed to decode contents of '{}': {}"
                .format(url, str(e))
            )
    #end function

    @contextlib.contextmanager
    def _lock_file(self, file_):
        try:
            fcntl.flock(file_.fileno(), fcntl.LOCK_EX)
            yield file_
        finally:
            try:
                fcntl.flock(file_.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
    #end function

    def _merge_releases(self, data, filename, overwrite_existing=False):
        releases = collections.OrderedDict()

        try:
            with open(filename, "r", encoding="utf-8") as f, \
                    self._lock_file(f) as f:
                releases = json.load(
                    f, object_pairs_hook=collections.OrderedDict
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            raise DistroInfoError(
                "failed to load '{}': {}".format(filename, str(e))
            )

        if overwrite_existing or not releases:
            releases = data
        else:
            for release_name, release_data in data.items():
                status = release_data.get("status", "supported")
                releases\
                    .setdefault(release_name, release_data)["status"] = status

        flags = os.O_RDWR | os.O_CREAT
        try:
            with os.fdopen(os.open(filename, flags), 'r+', encoding="utf-8") \
                    as f, self._lock_file(f) as f:
                os.ftruncate(f.fileno(), 0)
                json.dump(releases, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise DistroInfoError(
                "failed to store '{}': {}".format(filename, str(e))
            )

        self._dict["releases"] = releases
    #end function

    def _merge_mirrors(self, data, filename, overwrite_existing=False):
        mirrors = collections.OrderedDict()

        try:
            with open(filename, "r", encoding="utf-8") as f, \
                    self._lock_file(f) as f:
                mirrors = json.load(
                    f, object_pairs_hook=collections.OrderedDict
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            raise DistroInfoError(
                "failed to load '{}': {}".format(filename, str(e))
            )

        if overwrite_existing or not mirrors:
            mirrors = data
        else:
            for mirror_id, mirror_dict in data.items():
                if mirror_id not in mirrors:
                    mirrors[mirror_id] = mirror_dict
                else:
                    regions = mirrors[mirror_id]

                    for region_id, mirror_list in mirror_dict.items():
                        if region_id not in regions:
                            regions[region_id] = mirror_list
                        else:
                            url_set = set(regions[region_id])
                            for url in mirror_list:
                                url_set.add(url)
                            regions[region_id] = list(url_set)
                    #end for
                #end if
            #end for
        #end if

        flags = os.O_RDWR | os.O_CREAT
        try:
            with os.fdopen(os.open(filename, flags), 'r+', encoding="utf-8") \
                    as f, self._lock_file(f) as f:
                os.ftruncate(f.fileno(), 0)
                json.dump(mirrors, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise DistroInfoError(
                "failed to store '{}': {}".format(filename, str(e))
            )

        self._dict["mirrors"] = mirrors
    #end function

    def _load_json_file(self, which):
        if which in self._dict:
            return self._dict[which]

        result = collections.OrderedDict()

        json_file = os.path.join(
            UserInfo.config_folder(), "{}.json".format(which)
        )

        if not os.path.exists(json_file):
            self.refresh(**{which: True})

        try:
            with open(json_file, "r", encoding="utf-8") as f, \
                    self._lock_file(f) as f:
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

        self._dict[which] = result
        return result
    #end function

#end class
