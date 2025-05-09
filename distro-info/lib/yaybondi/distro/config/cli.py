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

import copy
import getopt
import json
import sys
import textwrap

from yaybondi.distro.config.distroinfo import DistroInfo
from yaybondi.distro.config.error import DistroInfoError

EXIT_OK    = 0
EXIT_ERROR = 1

class Cli:

    def __init__(self, config):
        self.config = config

    def refresh(self, *args):
        config = copy.deepcopy(self.config)

        def print_usage():
            print(textwrap.dedent(
                """
                USAGE:

                  bondi-distro-info refresh [OPTIONS]

                OPTIONS:

                  -h, --help              Print this help message.
                  -r, --releases          Update release info.
                  -m, --mirrors           Update mirrors list.
                """
            ))

        try:
            opts, args = getopt.getopt(
                args, "hmr", ["help", "mirrors", "releases"]
            )
        except getopt.GetoptError as e:
            raise DistroInfoError(
                "error parsing command line: {}".format(str(e))
            )

        kwargs = {
            "releases":
                False,
            "mirrors":
                False,
        }

        for o, v in opts:
            if o in ["-h", "--help"]:
                print_usage()
                sys.exit(EXIT_OK)
            elif o in ["-r", "--releases"]:
                kwargs["releases"] = True
            elif o in ["-m", "--mirrors"]:
                kwargs["mirrors"] = True
        #end for

        if args:
            print_usage()
            sys.exit(EXIT_ERROR)

        if not (kwargs["releases"] or kwargs["mirrors"]):
            raise DistroInfoError("specify at least one of -r or -m.")

        DistroInfo(**config).refresh(**kwargs)
    #end function

    def list(self, *args):
        config = copy.deepcopy(self.config)

        def print_usage():
            print(textwrap.dedent(
                """
                USAGE:

                  bondi-distro-info list [OPTIONS]

                OPTIONS:

                  -h, --help           Print this help message.
                  -s, --supported      Show supported releases.
                  -u, --unsupported    Show old, unsupported releases.
                  --include-unstable   Also list the unstable distribution.

                Per default supported and unsupported releases are listed and the unstable
                distribution is excluded.
                """  # noqa
            ))

        try:
            opts, args = getopt.getopt(
                args, "hsu", [
                    "help", "supported", "unsupported", "include-unstable"
                ]
            )
        except getopt.GetoptError as e:
            raise DistroInfoError(
                "error parsing command line: {}".format(str(e))
            )

        show_supported   = False
        show_unsupported = False
        show_unstable    = False

        for o, v in opts:
            if o in ["-h", "--help"]:
                print_usage()
                sys.exit(EXIT_OK)
            elif o in ["-s", "--supported"]:
                show_supported = True
            elif o in ["-u", "--unsupported"]:
                show_unsupported = True
            elif o == "--include-unstable":
                show_unstable = True

        if not (show_supported or show_unsupported):
            show_supported = show_unsupported = True

        if args:
            print_usage()
            sys.exit(EXIT_ERROR)

        dists = DistroInfo(**config).list(
            supported=show_supported,
            unsupported=show_unsupported,
            unstable=show_unstable
        )

        for metadata in dists:
            version_codename = metadata.get("version_codename", "")

            if metadata.get("status") == "unstable":
                print("{} (unstable)".format(version_codename))
            else:
                print(version_codename)
        #end for
    #end function

    def show(self, *args):
        config = copy.deepcopy(self.config)

        def print_usage():
            print(textwrap.dedent(
                """
                USAGE:

                  bondi-distro-info show [OPTIONS] <release-name>

                OPTIONS:

                  -h, --help           Print this help message.
                """
            ))

        try:
            opts, args = getopt.getopt(args, "h", ["help"])
        except getopt.GetoptError as e:
            raise DistroInfoError(
                "error parsing command line: {}".format(str(e))
            )

        for o, v in opts:
            if o in ["-h", "--help"]:
                print_usage()
                sys.exit(EXIT_OK)

        if len(args) != 1:
            print_usage()
            sys.exit(EXIT_ERROR)

        print(
            json.dumps(
                DistroInfo(**config).find(release=args[0]),
                ensure_ascii=False,
                indent=4
            )
        )
    #end function

#end class
