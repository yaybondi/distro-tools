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

import locale
import os
import re
import subprocess

from boltlinux.error import BoltError

class Platform:

    @staticmethod
    def find_executable(executable_name):
        search_path = os.environ.get("PATH", "").split(os.pathsep)  + [
            "/bin", "/sbin", "/usr/bin", "/usr/sbin"
        ]

        for path in search_path:
            location = os.path.join(path, executable_name)
            if os.path.exists(location):
                return location
        #end for

        return None
    #end function

    @staticmethod
    def uname(*args):
        uname = Platform.find_executable("uname")
        if not uname:
            raise BoltError("unable to find the uname executable.")

        return subprocess.run(
            [uname, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout \
         .decode(locale.getpreferredencoding(False)) \
         .strip()
    #end function

    @staticmethod
    def target_for_machine(machine, libc):
        vendor = "musl" if libc == "musl" else "gnu"

        if machine.startswith("aarch64"):
            template = "aarch64-linux-{}"
        elif machine.startswith("armv4t"):
            template = "armv4-linux-{}eabi"
        elif machine.startswith("armv6"):
            template = "armv6-linux-{}eabihf"
        elif machine.startswith("armv7a"):
            template = "armv7a-linux-{}eabihf"
        elif re.match(r"^i\d86.*$", machine):
            template = "i686-linux-{}"
        elif machine.startswith("mips64el"):
            template = "mips64el-linux-{}"
        elif re.match(r"^mips\d*el.*$", machine):
            template = "mipsel-linux-{}"
        elif re.match(r"^powerpc64(?:le|el).*$", machine):
            template = "powerpc64le-linux-{}"
        elif machine.startswith("powerpc"):
            template = "powerpc-linux-{}"
        elif machine.startswith("s390x"):
            template = "s390x-linux-{}"
        elif machine.startswith("riscv64"):
            template = "riscv64-linux-{}"
        elif re.match(r"^x86[-_]64$", machine):
            template = "x86_64-linux-{}"

        return template.format(vendor)
    #end function

#end class
