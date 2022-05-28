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
from boltlinux.miscellaneous.packagemanager import PackageManager

class Platform:

    CONFIG_GUESS   = '/usr/share/misc/config.guess'
    LIBC_NAME_FILE = "/usr/share/misc/libc.name"

    @staticmethod
    def config_guess():
        preferred_encoding = locale.getpreferredencoding(False)
        gcc = Platform.find_executable("gcc")

        if gcc:
            return subprocess.run([gcc, "-dumpmachine"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL)\
                            .stdout\
                            .decode(preferred_encoding)\
                            .strip()
        #end if

        if os.path.exists(Platform.CONFIG_GUESS):
            result = subprocess.run([Platform.CONFIG_GUESS],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL)\
                            .stdout\
                            .decode(preferred_encoding)\
                            .strip()
            m = re.match(r"^([^-]+)(?:-([^-]+))?-([^-]+)-([^-]+)$", result)
            if m:
                arch, platform, libc = \
                    m.group(1, 3) + (Platform.libc_vendor(),)
        #end if

        return ""
    #end function

    @staticmethod
    def find_executable(executable_name, fallback=None):
        search_path = os.environ.get("PATH", "").split(os.pathsep) + [
            "/tools/bin",
            "/tools/sbin",
            "/usr/local/bin",
            "/usr/local/sbin",
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin"
        ]

        for path in search_path:
            location = os.path.join(path, executable_name)
            if os.path.exists(location):
                return location
        #end for

        return fallback
    #end function

    @staticmethod
    def build_flags():
        build_flags = {}

        if "linux" in Platform.kernel_name().lower() and \
                os.path.exists("/etc/debian_version"):
            return Platform._dpkg_build_flags()

        build_flags["CFLAGS"] = "-g -O2 -fstack-protector-strong " \
            "-Wformat -Werror=format-security"
        build_flags["CXXFLAGS"] = "-g -O2 -fstack-protector-strong " \
            "-Wformat -Werror=format-security"
        build_flags["CPPFLAGS"] = \
            "-Wdate-time -D_FORTIFY_SOURCE=2"
        build_flags["LDFLAGS"] = \
            "-Wl,-z,relro"

        return build_flags
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

        template = None

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
        elif re.match(r"^(?:powerpc64|ppc64)(?:le|el).*$", machine):
            template = "powerpc64le-linux-{}"
        elif machine.startswith("powerpc") or machine.startswith("ppc"):
            template = "powerpc-linux-{}"
        elif machine.startswith("s390x"):
            template = "s390x-linux-{}"
        elif machine.startswith("riscv64"):
            template = "riscv64-linux-{}"
        elif re.match(r"^x86[-_]64$", machine):
            template = "x86_64-linux-{}"

        if not template:
            raise BoltError(
                'failed to determine target triplet for machine "{}"'
                .format(machine)
            )

        return template.format(vendor)
    #end function

    @staticmethod
    def kernel_name():
        return Platform.uname("-s")

    @staticmethod
    def machine_name():
        return Platform \
            .target_for_machine(Platform.uname("-m"), "musl") \
            .split("-")[0]

    @staticmethod
    def libc_vendor():
        result = ""

        if os.path.exists(Platform.LIBC_NAME_FILE):
            with open(Platform.LIBC_NAME_FILE, "r", encoding="utf-8") as f:
                result = f.read().strip()
        else:
            result = Platform.uname("-o").lower().split("/")[0]

        if result == "glibc":
            result = "gnu"

        return result
    #end function

    @staticmethod
    def is_bolt():
        result = Platform._key_value_file_lookup("ID", "/etc/os-release")
        return result.lower() == "bolt"

    @staticmethod
    def target_machine():
        result = Platform._key_value_file_lookup(
            "TARGET_MACHINE", "/etc/target"
        )

        if not result:
            result = PackageManager.instance().main_architecture()
        if not result:
            result = Platform.config_guess().split("-")[0]
        return result
    #end function

    @staticmethod
    def target_type():
        result = Platform._key_value_file_lookup("TARGET_TYPE", "/etc/target")
        if not result:
            result = Platform.config_guess()
        return result
    #end function

    @staticmethod
    def tools_machine():
        result = Platform._key_value_file_lookup("TOOLS_TYPE", "/etc/target")
        if result:
            result = result.split("-", 1)[0]
        if not result:
            result = Platform.machine_name()
        return result
    #end function

    @staticmethod
    def tools_type():
        result = Platform._key_value_file_lookup("TOOLS_TYPE", "/etc/target")
        if not result:
            result = "{}-tools-linux-{}".format(
                Platform.machine_name(), Platform.libc_vendor()
            )
        return result
    #end function

    # HELPERS

    @staticmethod
    def _key_value_file_lookup(attr_name, filename="/etc/target"):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as fp:
                for line in fp:
                    try:
                        k, v = [x.strip() for x in line.split("=", 1)]
                    except ValueError:
                        continue
                    if k == attr_name:
                        return v
                #end for
            #end with
        #end if

        return None
    #end function

    @staticmethod
    def _dpkg_build_flags():
        build_flags = {}
        dpkg_buildflags = Platform.find_executable("dpkg-buildflags")

        if not dpkg_buildflags:
            return build_flags

        preferred_encoding = locale.getpreferredencoding(False)

        for flag in subprocess.run([dpkg_buildflags, "--list"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\
                        .stdout.decode(preferred_encoding).splitlines():
            flag = flag.strip()

            if not flag:
                continue

            value = subprocess.run([dpkg_buildflags, "--get", flag],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\
                            .stdout.decode(preferred_encoding).strip()

            value = re.sub(r"\s*-fdebug-prefix-map=\S+\s*", " ", value)
            build_flags[flag] = value
        #end for

        return build_flags
    #end function

#end class
