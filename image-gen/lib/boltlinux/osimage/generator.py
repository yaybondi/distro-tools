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

import collections
import logging
import os
import re
import shutil
import textwrap

from boltlinux.error import BoltError
from boltlinux.miscellaneous.userinfo import UserInfo
from boltlinux.miscellaneous.platform import Platform
from boltlinux.osimage.specfile import SpecfileParser

LOGGER = logging.getLogger(__name__)

class ImageGenerator:

    OPKG_OPTIONS_TEMPLATE = textwrap.dedent(
        """\
        dest root /

        option signature_type usign
        option no_install_recommends
        option force_removal_of_dependent_packages
        option force_postinstall

        {opt_check_sig}
        """
    )  # noqa

    OPKG_FEEDS_TEMPLATE = textwrap.dedent(
        """\
        src/gz main {repo_base}/{release}/core/{arch}/{libc}/main
        src/gz main-debug {repo_base}/{release}/core/{arch}/{libc}/main-debug
        """)  # noqa

    OPKG_ARCH_TEMPLATE = textwrap.dedent(
        """\
        arch {arch} 1
        arch all 1
        """
    )  # noqa

    DIRS_TO_CREATE = [
        "dev",
        "etc",
        "etc/opkg",
        "etc/opkg/usign",
        "proc",
        "run",
        "sys",
        "tmp",
        "usr",
        "usr/bin",
        "var",
    ]

    class Error(BoltError):
        pass

    def __init__(self, release, arch, libc="musl", verify=True,
            copy_qemu=False, repo_base=None, cache_dir=None):
        self._release   = release
        self._arch      = arch
        self._libc      = libc
        self._verify    = verify
        self._copy_qemu = copy_qemu
        self._repo_base = repo_base or "http://archive.boltlinux.org/dists"
        self._cache_dir = cache_dir or UserInfo.cache_dir()

        if not self._cache_dir:
            raise ImageGenerator.Error(
                "unable to determine cache directory location."
            )

        opt_check_sig = "option check_signature" if self._verify else ""

        self.context = {
            "release":
                self._release,
            "libc":
                self._libc,
            "arch":
                self._arch,
            "host_arch":
                Platform.uname("-m"),
            "machine":
                self._arch,
            "target_type":
                Platform.target_for_machine(self._arch),
            "opt_check_sig":
                opt_check_sig,
            "repo_base":
                self._repo_base
        }
    #end function

    def bootstrap(self, sysroot, specfile):
        if not os.path.isdir(sysroot):
            raise ImageGenerator.Error("no such directory: {}".format(sysroot))

        sysroot = os.path.realpath(sysroot)

        self.prepare(sysroot)
        self.customize(sysroot, specfile)
        self.cleanup(sysroot)
    #end function

    def prepare(self, sysroot):
        for dirname in self.DIRS_TO_CREATE:
            os.makedirs(os.path.join(sysroot, dirname), exist_ok=True)

        var_run_symlink = os.path.join(sysroot, "var", "run")
        if not os.path.exists(var_run_symlink):
            os.symlink("../run", var_run_symlink)

        if self._copy_qemu:
            self._copy_qemu_to_sysroot(sysroot)

        self._write_opkg_config(sysroot)
    #end function

    def customize(self, sysroot, specfile):
        LOGGER.info("--------")
        LOGGER.info("loading specfile {}".format(specfile))
        LOGGER.info("--------")

        with open(specfile, "r", encoding="utf-8") as f:
            parts = SpecfileParser.load(f)

        env = self._prepare_environment(sysroot)

        for start_line, end_line, p in parts:
            what = re.sub(r"([a-z])([A-Z])", r"\1 \2", p.__class__.__name__)
            what = what.lower()

            LOGGER.info(
                "applying {} from line {} to {}.".format(
                    what, start_line, end_line
                )
            )

            p.apply(sysroot, env=env)
        #end for
    #end function

    def cleanup(self, sysroot):
        pass

    # HELPERS

    def _prepare_environment(self, sysroot):
        env = {}

        entries_to_keep = {
            "DISPLAY",
            "SSH_CONNECTION",
            "SSH_CLIENT",
            "SSH_TTY",
            "USER",
            "TERM",
            "HOME",
        }

        for key in list(os.environ.keys()):
            if not (key.startswith("BOLT_") or key in entries_to_keep):
                continue
            env[key] = os.environ[key]

        env["BOLT_SYSROOT"] = sysroot

        return env
    #end function

    def _copy_qemu_to_sysroot(self, sysroot):
        qemu_user_static = ""

        prefix_map = collections.OrderedDict([
            ("aarch64",
                "qemu-aarch64-static"),
            ("arm",
                "qemu-arm-static"),
            ("mips64el",
                "qemu-mips64el-static"),
            ("mipsel",
                "qemu-mipsel-static"),
            ("powerpc64el",
                "qemu-ppc64le-static"),
            ("powerpc64le",
                "qemu-ppc64le-static"),
            ("ppc64le",
                "qemu-ppc64le-static"),
            ("powerpc",
                "qemu-ppc-static"),
            ("riscv64",
                "qemu-riscv64-static"),
            ("s390x",
                "qemu-s390x-static"),
        ])

        for prefix, qemu_binary in prefix_map.items():
            if self._arch.startswith(prefix):
                qemu_user_static = qemu_binary
                break

        if not qemu_user_static:
            return

        qemu_exe = Platform.find_executable(qemu_user_static)
        if not qemu_exe:
            raise ImageGenerator.Error(
                'could not find QEMU executable "{}".'.format(qemu_user_static)
            )

        target_dir = os.path.dirname(
            os.path.join(sysroot, qemu_exe.lstrip("/"))
        )
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        shutil.copy2(qemu_exe, target_dir)
    #end function

    def _write_opkg_config(self, sysroot):
        conffile_list = ["arch.conf", "options.conf", "feeds.conf"]

        template_list = [
            self.OPKG_ARCH_TEMPLATE,
            self.OPKG_OPTIONS_TEMPLATE,
            self.OPKG_FEEDS_TEMPLATE
        ]

        for conffile, template in zip(conffile_list, template_list):
            conffile = os.path.join(sysroot, "etc", "opkg", conffile)
            with open(conffile, "w+", encoding="utf-8") as f:
                f.write(template.format(**self.context))
    #end function

#end class
