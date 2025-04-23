# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
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
from yaybondi.miscellaneous.xpkg import Dpkg, Opkg  # noqa:

class PackageManager:

    pm_instance = None

    @classmethod
    def instance(klass):
        if not PackageManager.pm_instance:
            PackageManager.pm_instance = \
                PackageManager.system_package_manager()()
        #end if

        return PackageManager.pm_instance
    #end function

    @classmethod
    def system_package_manager(klass):
        for executable in ["dpkg", "opkg"]:
            for search_dir in os.environ.get("PATH", "").split(os.pathsep):
                if os.path.exists(os.path.join(search_dir, executable)):
                    return globals()[executable.capitalize()]
                #end if
            #end for
        #end for

        msg = "system uses unknown or unsupported package manager."
        raise RuntimeError(msg)
    #end function

#end class
