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

from boltlinux.distro.config.distroinfo import DistroInfo
from boltlinux.error import BoltError
from boltlinux.miscellaneous.platform import Platform
from boltlinux.osimage.sysroot import Sysroot
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
        def print_usage(specfile_list=None):
            print(textwrap.dedent(
                """
                USAGE:

                  bolt-image bootstrap [OPTIONS] <sysroot> <specfile> ...

                OPTIONS:

                  -h, --help       Print this help message.
                  -r, --release    The name of the release (e.g. ollie).
                  -a, --arch       The target architecture.
                  -l, --libc       The C runtime to use ("musl" or "glibc").

                  --repo-base      Repository base URL not including the release
                                   name.
                  --copy-qemu      Copy the appropriate QEMU interpreter to the
                                   chroot (should not be necessary).
                  --no-verify      Do not verify package list signatures.
                """  # noqa
            ))

            if specfile_list:
                print("INTERNAL SPECS:\n")
                for spec in specfile_list:
                    print("  * {}".format(spec))
                print("")
        #end inline function

        try:
            opts, args = getopt.getopt(
                args, "a:hl:r:", [
                    "arch=",
                    "copy-qemu",
                    "help",
                    "libc=",
                    "no-verify",
                    "release=",
                    "repo-base="
                ]
            )
        except getopt.GetoptError as e:
            raise ImageGenCli.Error(
                "error parsing command line: {}".format(str(e))
            )

        distro_info = DistroInfo()

        kwargs = {
            "release":
                distro_info.latest_release(),
            "libc":
                "musl",
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
                print_usage()
                sys.exit(EXIT_OK)
            elif o in ["-r", "--release"]:
                kwargs["release"] = v.strip()
            elif o in ["-a", "--arch"]:
                kwargs["arch"] = v.strip().replace("-", "_")
            elif o in ["-l", "--libc"]:
                kwargs["libc"] = v.strip()
            elif o == "--repo-base":
                kwargs["repo_base"] = v.strip()
            elif o == "--copy-qemu":
                kwargs["copy_qemu"] = True
            elif o == "--no-verify":
                kwargs["verify"] = False
        #end for

        release, libc, arch = kwargs["release"], kwargs["libc"], kwargs["arch"]

        if not distro_info.release_exists(release):
            raise ImageGenCli.Error(
                'release "{}" not found, run `bolt-distro-info refresh -r`.'
                .format(release)
            )

        if not distro_info.is_supported_libc(release, libc):
            raise ImageGenCli.Error(
                'release "{}" does not support C runtime library "{}".'
                .format(release, libc)
            )

        if not distro_info.is_supported_arch(release, arch, libc=libc):
            raise ImageGenCli.Error(
                'release "{}" does not support architecture "{}".'
                .format(release, arch)
            )

        if len(args) == 0:
            print_usage(
                ImageGeneratorUtils.list_internal_specs(release, libc, arch)
            )
            sys.exit(EXIT_ERROR)

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        if len(args) < 2:
            print_usage(
                ImageGeneratorUtils.list_internal_specs(release, libc, arch)
            )
            sys.exit(EXIT_ERROR)

        specfile_list = ImageGeneratorUtils.collect_specfiles(
            release, libc, arch, *args[1:]
        )

        if os.geteuid() != 0:
            raise ImageGenCli.Error(
                "image generation needs to be done as root."
            )

        image_gen = ImageGenerator(**kwargs)
        image_gen.prepare(sysroot)

        with Sysroot(sysroot):
            for specfile in specfile_list:
                image_gen.customize(sysroot, specfile)
    #end function

    def customize(self, *args):
        def print_usage(specfile_list=None):
            print(textwrap.dedent(
                """
                USAGE:

                  bolt-image customize [OPTIONS] <sysroot> <specfile> ...

                OPTIONS:

                  -h, --help       Print this help message.
                """
            ))

            if specfile_list:
                print("INTERNAL SPECS:\n")
                for spec in specfile_list:
                    print("  * {}".format(spec))
                print("")
        #end inline function

        try:
            opts, args = getopt.getopt(args, "h", ["help"])
        except getopt.GetoptError as e:
            raise ImageGenCli.Error(
                "error parsing command line: {}".format(str(e))
            )

        for o, v in opts:
            if o in ["-h", "--help"]:
                print_usage()
                sys.exit(EXIT_OK)

        if len(args) == 0:
            print_usage()
            sys.exit(EXIT_ERROR)

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        kwargs = {
            "release":
                ImageGeneratorUtils.determine_target_release(sysroot),
            "libc":
                ImageGeneratorUtils.determine_target_libc(sysroot),
            "arch":
                ImageGeneratorUtils.determine_target_arch(sysroot),
        }

        release, libc, arch = kwargs["release"], kwargs["libc"], kwargs["arch"]

        if len(args) < 2:
            print_usage(
                ImageGeneratorUtils.list_internal_specs(release, libc, arch)
            )
            sys.exit(EXIT_ERROR)

        specfile_list = ImageGeneratorUtils.collect_specfiles(
            release, libc, arch, *args[1:]
        )

        if os.geteuid() != 0:
            raise ImageGenCli.Error(
                "image generation needs to be done as root."
            )

        image_gen = ImageGenerator(**kwargs)

        with Sysroot(sysroot):
            for specfile in specfile_list:
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
            "libc":
                ImageGeneratorUtils.determine_target_libc(sysroot),
            "arch":
                ImageGeneratorUtils.determine_target_arch(sysroot),
        }

        if os.geteuid() != 0:
            raise ImageGenCli.Error(
                "image generation needs to be done as root."
            )

        image_gen = ImageGenerator(**kwargs)
        image_gen.cleanup(sysroot=args[0])
    #end function

    def package(self, *args):
        def print_usage(format_list=None):
            print(textwrap.dedent(
                """
                USAGE:

                  bolt-image package [OPTIONS] <sysroot> <format> [ARGS]

                OPTIONS:

                  -h, --help       Print this help message.

                  Type

                    bolt-image package <sysroot>

                  to see a list of supported image formats.
                """
            ))

            if format_list:
                print("FORMATS:\n")
                for format_ in format_list:
                    print("  * {}".format(format_))
                print(textwrap.indent(textwrap.dedent(
                    """
                    Type

                      bolt-image package <sysroot> <format> --help

                    for additional usage instructions specific to a given
                    image format.
                    """
                ), "  "))
        #end inline function

        if len(args) == 0:
            print_usage()
            sys.exit(EXIT_ERROR)

        if args[0] in ["-h", "--help"]:
            print_usage()
            sys.exit(EXIT_OK)

        sysroot = args[0]

        if not os.path.isdir(sysroot):
            raise ImageGenCli.Error("no such directory: {}".format(sysroot))

        kwargs = {
            "release":
                ImageGeneratorUtils.determine_target_release(sysroot),
            "libc":
                ImageGeneratorUtils.determine_target_libc(sysroot),
            "arch":
                ImageGeneratorUtils.determine_target_arch(sysroot),
        }

        release, libc, arch = kwargs["release"], kwargs["libc"], kwargs["arch"]

        if len(args) < 2:
            print_usage(
                ImageGeneratorUtils.list_package_scripts(release, libc, arch)
            )
            sys.exit(EXIT_ERROR)

        format_ = args[1]

        if os.geteuid() != 0:
            raise ImageGenCli.Error(
                "image generation needs to be done as root."
            )

        image_gen = ImageGenerator(**kwargs)
        image_gen.package(format_, sysroot, *args[2:])
    #end function

#end class
