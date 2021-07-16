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

import os
import re

from boltlinux.error import BoltError

class ImageGeneratorUtils:

    class Error(BoltError):
        pass

    @staticmethod
    def raise_unless_sysroot_exists(sysroot):
        if not os.path.isdir(sysroot):
            raise ImageGeneratorUtils.Error(
                'folder "{}" does not exist or is not a folder.'
                .format(sysroot)
            )
    #end function

    @staticmethod
    def determine_target_release(sysroot):
        ImageGeneratorUtils.raise_unless_sysroot_exists(sysroot)

        os_release = sysroot + "/etc/os-release"

        if os.path.exists(os_release):
            with open(os_release, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(
                        r"^\s*VERSION_CODENAME\s*=\s*(?P<release>\S+)\s*$",
                        line
                    )
                    if m:
                        return m.group("release")
                #end for
            #end with
        #end if

        raise ImageGeneratorUtils.Error(
            "unable to determine target release."
        )
    #end function

    @staticmethod
    def determine_target_arch(sysroot):
        ImageGeneratorUtils.raise_unless_sysroot_exists(sysroot)

        arch_conf = sysroot + "/etc/opkg/arch.conf"

        if os.path.exists(arch_conf):
            with open(arch_conf, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"^\s*arch\s+(?P<arch>\S+)\s+\d+\s*$", line)
                    if m:
                        if m.group("arch") not in ["all", "tools"]:
                            return m.group("arch")
                #end for
            #end with
        #end if

        raise ImageGeneratorUtils.Error(
            "unable to determine target architecture."
        )
    #end function

#end class
