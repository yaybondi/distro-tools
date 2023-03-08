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

from boltlinux.distro.config.error import DistroInfoError
from boltlinux.distro.config.v1.distroinfo import (
    DistroInfo as DistroInfoV1
)

class DistroInfo:

    def __init__(self, api_version=1, **kwargs):
        if api_version == 1:
            self.implementation = DistroInfoV1()
        else:
            raise DistroInfoError(
                'unknown API version "{}"'.format(api_version)
            )

    def refresh(self, **kwargs):
        return self.implementation.refresh(**kwargs)

    def list(self, **kwargs):
        return self.implementation.list(**kwargs)

    def find(self, **kwargs):
        return self.implementation.find(**kwargs)

    def get_git_url_and_ref(self, **kwargs):
        return self.implementation.get_git_url_and_ref(**kwargs)

    def pick_mirror(self, **kwargs):
        return self.implementation.pick_mirror(**kwargs)

    def release_exists(self, name):
        return name in self.list(supported=True, unsupported=True)

    def is_supported_release(self, name):
        return name in self.list(supported=True)

    def is_supported_libc(self, release, libc):
        arch_list = self.find(release=release) \
            .get("supported-architectures", {}) \
            .get(libc)
        return arch_list is not None
    #end function

    def is_supported_arch(self, release, arch, libc="musl"):
        return arch in self\
            .find(release=release) \
            .get("supported-architectures", {}) \
            .get(libc, [])
    #end function

    def latest_release(self):
        try:
            return list(self.list(supported=True).keys())[-1]
        except IndexError:
            return None

#end class
