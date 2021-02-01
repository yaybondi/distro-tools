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

from boltlinux.archive.config.distroinfo import DistroInfo
from boltlinux.archive.config.error import DistroInfoError

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

                  bolt-distro-info refresh [OPTIONS]

                OPTIONS:

                  -h, --help              Print this help message.
                  -r, --releases          Update release info.
                  -m, --mirrors           Update mirrors list.
                  --overwrite-existing    Overwrite existing entries.
                """
            ))

        try:
            opts, args = getopt.getopt(
                args, "hmr", [
                    "help", "mirrors", "overwrite-existing", "releases"
                ]
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
            "overwrite_existing":
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
            elif o == "--overwrite-existing":
                kwargs["overwrite_existing"] = True
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

                  bolt-distro-info list [OPTIONS]

                OPTIONS:

                  -h, --help           Print this help message.
                  -s, --supported      Show supported releases.
                  -u, --unsupported    Show old, unsupported releases.

                Per default supported and unsupported releases are listed.
                """
            ))

        try:
            opts, args = getopt.getopt(
                args, "hsu", ["help", "supported", "unsupported"]
            )
        except getopt.GetoptError as e:
            raise DistroInfoError(
                "error parsing command line: {}".format(str(e))
            )

        supported   = False
        unsupported = False

        for o, v in opts:
            if o in ["-h", "--help"]:
                print_usage()
                sys.exit(EXIT_OK)
            elif o in ["-s", "--supported"]:
                supported = True
            elif o in ["-u", "--unsupported"]:
                unsupported = True

        if not (supported or unsupported):
            supported = unsupported = True

        if args:
            print_usage()
            sys.exit(EXIT_ERROR)

        dists = DistroInfo(**config).list(
            supported=supported, unsupported=unsupported
        )

        if dists:
            print("\n".join(dists.keys()))
    #end function

    def show(self, *args):
        config = copy.deepcopy(self.config)

        def print_usage():
            print(textwrap.dedent(
                """
                USAGE:

                  bolt-distro-info show [OPTIONS] <release-name>

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
