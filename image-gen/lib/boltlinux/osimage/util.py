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

    DIR_TEMPLATES = [
        "/common",
        "/{release}",
        "/{release}/{libc}",
        "/{release}/{libc}/{arch}"
    ]

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
    def determine_target_libc(sysroot):
        ImageGeneratorUtils.raise_unless_sysroot_exists(sysroot)

        musl_libc_list = sysroot + "/var/lib/opkg/info/musl-libc.list"
        if os.path.exists(musl_libc_list):
            return "musl"

        return "glibc"
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

    @staticmethod
    def raise_unless_valid_script_identifier(scriptname):
        if not re.match(r"^[-a-zA-Z0-9_.]+$", scriptname):
            raise ImageGeneratorUtils.Error(
                "invalid identifier: {}".format(scriptname)
            )
    #end function

    @staticmethod
    def find_internal_specs(specname, release, libc, arch):
        ImageGeneratorUtils.raise_unless_valid_script_identifier(specname)

        basedir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "customize"
        )

        specfiles = []

        for subdir_template in ImageGeneratorUtils.DIR_TEMPLATES:
            subdir = subdir_template.format(
                release=release, libc=libc, arch=arch
            )

            candidate_specfile = basedir + subdir + os.sep + specname
            if os.path.isfile(candidate_specfile):
                specfiles.append(candidate_specfile)
        #end for

        return specfiles
    #end function

    @staticmethod
    def list_internal_specs(release, libc, arch):
        basedir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "customize"
        )

        specfiles = set()

        for subdir_template in ImageGeneratorUtils.DIR_TEMPLATES:
            subdir = subdir_template.format(
                release=release, libc=libc, arch=arch
            )

            specfile_dir = basedir + subdir
            if not os.path.isdir(specfile_dir):
                continue

            for entry in os.listdir(specfile_dir):
                if os.path.isfile(specfile_dir + os.sep + entry):
                    specfiles.add(entry)
        #end for

        return list(sorted(specfiles))
    #end function

    @staticmethod
    def find_package_script(format_, release, libc, arch):
        ImageGeneratorUtils.raise_unless_valid_script_identifier(format_)

        basedir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "package"
        )

        for subdir_template in reversed(ImageGeneratorUtils.DIR_TEMPLATES):
            subdir = subdir_template.format(
                release=release, libc=libc, arch=arch
            )

            package_script = basedir + subdir + os.sep + format_
            if os.path.isfile(package_script):
                return package_script
        #end for

        return None
    #end function

    @staticmethod
    def list_package_scripts(release, libc, arch):
        basedir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "package"
        )

        package_scripts = set()

        for subdir_template in reversed(ImageGeneratorUtils.DIR_TEMPLATES):
            subdir = subdir_template.format(
                release=release, libc=libc, arch=arch
            )

            script_dir = basedir + subdir
            if not os.path.isdir(script_dir):
                continue

            for entry in os.listdir(script_dir):
                if os.path.isfile(script_dir + os.sep + entry):
                    package_scripts.add(entry)
        #end for

        return list(sorted(package_scripts))
    #end function

#end class
