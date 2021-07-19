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

import getopt
import os
import sys
import textwrap

from boltlinux.archive.config.distroinfo import DistroInfo
from boltlinux.error import BoltError
from boltlinux.miscellaneous.platform import Platform
from boltlinux.osimage.chroot import Chroot
from boltlinux.osimage.generator import ImageGenerator
from boltlinux.osimage.util import ImageGeneratorUtils

EXIT_OK = 0
EXIT_ERROR = 1

class ImageGenCli:

    class Error(BoltError):
        pass

    def execute_command(self, command, *args):
        getattr(self, command)(*args)

    def bootstrap(self, *args):
        usage = textwrap.dedent(
            """
            USAGE:

              bolt-image bootstrap [OPTIONS] <sysroot> <specfile> ...

            OPTIONS:

              -h, --help       Print this help message.
              -r, --release    The name of the release (e.g. ollie).
              -a, --arch       The target architecture.

              --repo-base      Repository base URL not including the release
                               name.
              --copy-qemu      Copy the appropriate QEMU interpreter to the
                               chroot (should not be necessary).
              --no-verify      Do not verify package list signatures.
            """
        )

        try:
            opts, args = getopt.getopt(
                args, "hr:a:", ["help", "release=", "arch=", "repo-base=",
                    "copy-qemu", "no-verify"]
            )
        except getopt.GetoptError as e:
            raise ImageGenCli.Error(
                "error parsing command line: {}".format(str(e))
            )

        distro_info = DistroInfo()

        kwargs = {
            "release":
                distro_info.latest_release(),
            "arch":
                Platform.uname("-m"),
            "repo_base":
                "http://archive.boltlinux.org/dists",
            "copy_qemu":
                False,
            "verify":
                True,
        }

        for o, v in opts:
            if o in ["-h", "--help"]:
                print(usage)
                sys.exit(EXIT_OK)
            elif o in ["-r", "--release"]:
                kwargs["release"] = v
            elif o in ["-a", "--arch"]:
                kwargs["arch"] = v
            elif o == "--repo-base":
                kwargs["repo_base"] = v
            elif o == "--copy-qemu":
                kwargs["copy_qemu"] = True
            elif o == "--no-verify":
                kwargs["verify"] = False
        #end for

        if len(args) < 2:
            print(usage)
            sys.exit(EXIT_ERROR)

        release, arch = kwargs["release"], kwargs["arch"]

        if not distro_info.release_exists(release):
            raise ImageGenCli.Error(
                'release "{}" not found, run `bolt-distro-info refresh -r`.'
                .format(release)
            )

        if not distro_info.is_supported_arch(release, arch):
            raise ImageGenCli.Error(
                'release "{}" does not support architecture "{}".'
                .format(release, arch)
            )

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        for specfile in args[1:]:
            if not os.path.isfile(specfile):
                raise ImageGenCli.Error("no such file: {}".format(specfile))

        image_gen = ImageGenerator(**kwargs)
        image_gen.prepare(sysroot)

        with Chroot(sysroot):
            for specfile in args[1:]:
                image_gen.customize(sysroot, specfile)
    #end function

    def customize(self, *args):
        usage = textwrap.dedent(
            """
            USAGE:

              bolt-image customize [OPTIONS] <sysroot> <specfile> ...

            OPTIONS:

              -h, --help       Print this help message.
            """
        )

        try:
            opts, args = getopt.getopt(args, "h", ["help"])
        except getopt.GetoptError as e:
            raise ImageGenCli.Error(
                "error parsing command line: {}".format(str(e))
            )

        for o, v in opts:
            if o in ["-h", "--help"]:
                print(usage)
                sys.exit(EXIT_OK)
        #end for

        if len(args) < 2:
            print(usage)
            sys.exit(EXIT_ERROR)

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        for specfile in args[1:]:
            if not os.path.isfile(specfile):
                raise ImageGenCli.Error("no such file: {}".format(specfile))

        kwargs = {
            "release":
                ImageGeneratorUtils.determine_target_release(sysroot),
            "arch":
                ImageGeneratorUtils.determine_target_arch(sysroot),
        }

        image_gen = ImageGenerator(**kwargs)

        with Chroot(sysroot):
            for specfile in args[1:]:
                image_gen.customize(sysroot, specfile)
    #end function

    def cleanup(self, *args):
        usage = textwrap.dedent(
            """
            USAGE:

              bolt-image cleanup [OPTIONS] <sysroot>

            OPTIONS:

              -h, --help       Print this help message.
            """
        )

        try:
            opts, args = getopt.getopt(args, "h", ["help"])
        except getopt.GetoptError as e:
            raise ImageGenCli.Error(
                "error parsing command line: {}".format(str(e))
            )

        for o, v in opts:
            if o in ["-h", "--help"]:
                print(usage)
                sys.exit(EXIT_OK)
        #end for

        if len(args) != 1:
            print(usage)
            sys.exit(EXIT_ERROR)

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        kwargs = {
            "release":
                ImageGeneratorUtils.determine_target_release(sysroot),
            "arch":
                ImageGeneratorUtils.determine_target_arch(sysroot),
        }

        image_gen = ImageGenerator(**kwargs)
        image_gen.cleanup(sysroot=args[0])
    #end function

    def package(self, *args):
        pass

#end class
