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
import shlex
import tempfile

from boltlinux.error import BoltError
from boltlinux.osimage.subprocess import Subprocess

class Script:

    class Error(BoltError):
        pass

    def __init__(self, interp, script, chroot=False):
        self.interp = interp
        self.script = script
        self.chroot = chroot
    #end function

    def apply(self, sysroot, env=None, **options):
        if self.chroot and "BOLT_SYSROOT" in env:
            del env["BOLT_SYSROOT"]

        tmp_prefix = os.path.join(sysroot, "tmp", "igen-")

        interp = self.interp.split()[0]
        if self.chroot:
            interp = sysroot + os.path.abspath(interp)
        if not os.path.exists(interp):
            raise Script.Error("interpreter not found: {}".format(interp))

        with tempfile.TemporaryDirectory(prefix=tmp_prefix) as tmpdir:
            script_file = os.path.join(tmpdir, "script")

            with open(script_file, "w+", encoding="utf-8") as f:
                f.write("#!{}\n".format(self.interp))
                f.write(self.script)
                os.fchmod(f.fileno(), 0o755)

            if self.chroot:
                script_file = script_file[len(sysroot):]

            Subprocess.run(
                sysroot,
                script_file,
                [script_file],
                env=env,
                chroot=self.chroot
            )
        #end with
    #end function

#end class

class PackageBatch:

    def __init__(self, packages):
        self.batch = packages

    def apply(self, sysroot, env=None, **options):
        if "BOLT_SYSROOT" in env:
            del env["BOLT_SYSROOT"]

        if not self.batch:
            return

        active_mode  = self.batch[0][0]
        active_batch = []
        iterator     = iter(self.batch)
        finished     = False

        while True:
            try:
                mode, package = next(iterator)
            except StopIteration:
                finished = True

            if mode != active_mode or finished:
                self._apply_batch(sysroot, env, active_mode, active_batch)

                if finished:
                    break

                active_mode  = mode
                active_batch = []
            #end if

            active_batch.append(package)
        #end for
    #end function

    def _apply_batch(self, sysroot, env, mode, packages):
        if not packages:
            return

        mode = "install" if mode == "+" else "remove"

        opkg_cmd = shlex.split(
            "opkg --offline-root '{}' {} {}".format(
                sysroot, mode, ' '.join(packages)
            )
        )

        Subprocess.run(sysroot, opkg_cmd[0], opkg_cmd, env=env)
    #end function

#end class

class SpecfileParser:

    class SyntaxError(BoltError):
        pass

    def __init__(self, fp):
        self.source = fp
        self.lineno = 0
        self.parts  = []
    #end function

    @staticmethod
    def load(fp):
        parser = SpecfileParser(fp)
        return parser._parse_wrapper()
    #end function

    def _parse_wrapper(self):
        try:
            self._parse()
        except StopIteration:
            pass
        return self.parts
    #end function

    def _parse(self):
        while True:
            self.lineno, line = self.lineno + 1, next(self.source)

            stripped = line.strip()
            if not stripped:
                continue

            if line[0] in ['+', '-']:
                self.parts.append(self._load_package_batch(line))
            elif line.startswith("#!"):
                where  = "host"

                m = re.match(
                    r"^#!(?:\((?P<where>[^)]+)\))?(?P<interp>.*)$",
                    line.rstrip()
                )

                if not m:
                    raise SpecfileParser.SyntaxError(
                        'error on line {}: malformed shebang.'
                        .format(self.lineno)
                    )
                #end if

                where = m.group("where") or "host"

                if where not in ["host", "chroot"]:
                    raise SpecfileParser.SyntaxError(
                        'error on line {}: unknown location "{}".'
                        .format(self.lineno, where)
                    )
                #end if

                self.parts.append(self._load_script(where, m.group("interp")))
            elif line.startswith("="):
                pass
            else:
                raise SpecfileParser.SyntaxError(
                    'error on line {}: syntax error.'.format(self.lineno)
                )
        #end for

        return self.parts
    #end function

    def _load_script(self, where, interp):
        start_line = self.lineno
        lines = []

        while True:
            self.lineno, line = self.lineno + 1, next(self.source, None)

            if line is None or line.startswith("="):
                end_line = self.lineno - 1

                return (
                    start_line, end_line, Script(
                        interp, "\n".join(lines), chroot=(where == "chroot")
                    )
                )
            #end if

            lines.append(line)
        #end while
    #end function

    def _load_package_batch(self, line):
        start_line = self.lineno
        packages = []

        while True:
            if line is None or line.startswith("="):
                return (start_line, self.lineno - 1, PackageBatch(packages))

            line = line.strip()

            if line:
                m = re.match(r"^(?P<mode>[-+])\s*(?P<package>\S+)\s*$", line)
                if not m:
                    raise SpecfileParser.SyntaxError(
                        "syntax error on line {}.".format(self.lineno)
                    )
                packages.append((m.group("mode"), m.group("package")))

            self.lineno, line = self.lineno + 1, next(self.source, None)
        #end while
    #end function

#end class
