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
import shlex
import shutil
import tempfile
import textwrap

from yaybondi.error import BondiError
from yaybondi.miscellaneous.platform import Platform
from yaybondi.osimage.specfile import SpecfileParser
from yaybondi.osimage.subprocess import Subprocess
from yaybondi.osimage.util import ImageGeneratorUtils

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
    )

    OPKG_FEEDS_TEMPLATE = textwrap.dedent(
        """\
        src/gz main {repo_base}/{release}/core/{arch}/{libc}/main
        """
    )

    OPKG_ARCH_TEMPLATE = textwrap.dedent(
        """\
        arch {arch} 1
        arch all 1
        """
    )

    DIRS_TO_CREATE = [
        (0o0755, "/dev"),
        (0o0755, "/etc"),
        (0o0755, "/etc/opkg"),
        (0o0755, "/etc/opkg/usign"),
        (0o0755, "/proc"),
        (0o0755, "/run"),
        (0o0755, "/sys"),
        (0o1777, "/tmp"),
        (0o0755, "/usr"),
        (0o0755, "/usr/bin"),
        (0o0755, "/var"),
    ]

    DIRS_TO_CLEAN = [
        "/tmp",
        "/var/tmp",
    ]

    ETC_PASSWD = textwrap.dedent(
        """\
        root:x:0:0:root:/root:/bin/sh
        daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
        bin:x:2:2:bin:/bin:/usr/sbin/nologin
        sys:x:3:3:sys:/dev:/usr/sbin/nologin
        sync:x:4:65534:sync:/bin:/bin/sync
        games:x:5:60:games:/usr/games:/usr/sbin/nologin
        man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
        lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
        mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
        news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
        uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
        proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
        www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
        backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
        list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
        irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
        nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
        """
    )

    ETC_GROUP = textwrap.dedent(
        """\
        root:x:0:
        daemon:x:1:
        bin:x:2:
        sys:x:3:
        adm:x:4:
        tty:x:5:
        disk:x:6:
        lp:x:7:
        mail:x:8:
        news:x:9:
        uucp:x:10:
        man:x:12:
        proxy:x:13:
        kmem:x:15:
        dialout:x:20:
        fax:x:21:
        voice:x:22:
        cdrom:x:24:
        floppy:x:25:
        tape:x:26:
        sudo:x:27:
        audio:x:29:
        dip:x:30:
        www-data:x:33:
        backup:x:34:
        operator:x:37:
        list:x:38:
        irc:x:39:
        src:x:40:
        shadow:x:42:
        utmp:x:43:
        video:x:44:
        sasl:x:45:
        plugdev:x:46:
        staff:x:50:
        games:x:60:
        users:x:100:
        nogroup:x:65534:
        """
    )

    ETC_HOSTS = textwrap.dedent(
        """\
        127.0.0.1 localhost

        ::1     localhost ip6-localhost ip6-loopback
        ff02::1 ip6-allnodes
        ff02::2 ip6-allrouters
        """
    )

    class Error(BondiError):
        pass

    def __init__(
        self,
        release,
        arch,
        libc="musl",
        verify=True,
        repo_base=None,
        **kwargs
    ):
        self._release   = release
        self._arch      = arch
        self._libc      = libc
        self._verify    = verify
        self._repo_base = repo_base or "http://archive.yaybondi.com/dists"

        opt_check_sig = "option check_signature" if self._verify else ""
        uname_m = Platform.uname("-m")

        tools_type = Platform.target_for_machine(uname_m, self._libc)
        if "tools" not in tools_type.split("-"):
            tools_type = tools_type.replace("-", "-tools-", 1)

        self.context = {
            "release":
                self._release,
            "libc":
                self._libc,
            "arch":
                self._arch,
            "host_arch":
                uname_m,
            "machine":
                self._arch,
            "target_type":
                Platform.target_for_machine(self._arch, self._libc),
            "tools_type":
                tools_type,
            "opt_check_sig":
                opt_check_sig,
            "repo_base":
                self._repo_base
        }
    #end function

    def prepare(self, sysroot):
        if not os.path.isdir(sysroot):
            raise ImageGenerator.Error("no such directory: {}".format(sysroot))

        LOGGER.info("preparing system root.")

        sysroot = os.path.realpath(sysroot)

        for mode, dirname in self.DIRS_TO_CREATE:
            full_path = sysroot + dirname
            os.makedirs(full_path, exist_ok=True)
            os.chmod(full_path, mode)
        #end for

        var_run_symlink = sysroot + "/var/run"
        if not os.path.exists(var_run_symlink):
            os.symlink("../run", var_run_symlink)

        self._write_config_files(sysroot)

        files_to_copy = [
            "/etc/hosts",
            "/etc/resolv.conf",
        ]

        for file_ in files_to_copy:
            shutil.copy2(file_, sysroot + file_)

        with tempfile.TemporaryDirectory() as tmpdir:
            opkg_cmd = shlex.split(
                "opkg --tmp-dir '{}' --offline-root '{}' update"
                .format(tmpdir, sysroot)
            )
            Subprocess.run(sysroot, opkg_cmd[0], opkg_cmd)
        #end with
    #end function

    def customize(self, sysroot, specfile):
        if not os.path.isdir(sysroot):
            raise ImageGenerator.Error("no such directory: {}".format(sysroot))
        if not os.path.isfile(specfile):
            raise ImageGenerator.Error("no such file: {}".format(specfile))

        LOGGER.info("================")
        LOGGER.info("loading specfile {}".format(specfile))
        LOGGER.info("================")

        sysroot = os.path.realpath(sysroot)

        with open(specfile, "r", encoding="utf-8") as f:
            parts = SpecfileParser.load(f)

        env = self._prepare_environment(sysroot)

        for start_line, end_line, p in parts:
            what = re.sub(
                r"([a-z])([A-Z])", r"\1 \2",
                p.__class__.__name__
            ).lower()

            LOGGER.info(
                "applying {} from line {} to {}.".format(
                    what, start_line, end_line
                )
            )

            p.apply(sysroot, env=env)
        #end for
    #end function

    def cleanup(self, sysroot):
        if not os.path.isdir(sysroot):
            raise ImageGenerator.Error("no such directory: {}".format(sysroot))

        sysroot = os.path.realpath(sysroot)

        if os.path.exists(sysroot + "/usr/bin/opkg"):
            opkg_cmd = shlex.split(
                "opkg --offline-root '{}' clean".format(sysroot)
            )

            Subprocess.run(sysroot, opkg_cmd[0], opkg_cmd, check=False)
        #end if

        self._write_config_files(sysroot)
        try:
            os.unlink(sysroot + "/etc/resolv.conf")
        except OSError:
            pass

        for directory in self.DIRS_TO_CLEAN:
            full_path = sysroot + directory

            stat = os.lstat(full_path)
            shutil.rmtree(full_path)

            os.makedirs(full_path)
            os.chown(full_path, stat.st_uid, stat.st_gid)
            os.chmod(full_path, stat.st_mode)
        #end for
    #end function

    def package(self, format_, sysroot, *args):
        script = ImageGeneratorUtils.find_package_script(
            format_, self._release, self._libc, self._arch
        )

        if not script:
            raise ImageGenerator.Error(
                'could not find a package script for format "{}"'
                .format(format_)
            )
        #end if

        env = self._prepare_environment(sysroot)

        args = list(args)
        args.insert(0, script)
        args.append(sysroot)

        os.execve(script, args, env)
    #end function

    # HELPERS

    def _prepare_environment(self, sysroot):
        env = {}

        entries_to_keep = {
            "BUILD_BOX_WRAPPER_A883DAFC",
            "DISPLAY",
            "SSH_CONNECTION",
            "SSH_CLIENT",
            "SSH_TTY",
            "USER",
            "TERM",
            "HOME",
            "PYTHONPATH",
            "PYTHONUNBUFFERED",
        }

        for key in list(os.environ.keys()):
            if not (key.startswith("BONDI_") or key in entries_to_keep):
                continue
            env[key] = os.environ[key]

        # These cannot be overridden by user.
        env["BONDI_SYSROOT"]   = sysroot
        env["BONDI_RELEASE"]   = self.context["release"]
        env["BONDI_ARCH"]      = self.context["arch"]
        env["BONDI_LIBC"]      = self.context["libc"]
        env["BONDI_HOST_ARCH"] = self.context["host_arch"]

        return env
    #end function

    def _write_config_files(self, sysroot):
        conffile_list = [
            "/etc/opkg/arch.conf",
            "/etc/opkg/options.conf",
            "/etc/opkg/feeds.conf",
            "/etc/passwd",
            "/etc/group",
            "/etc/hosts",
        ]

        template_list = [
            self.OPKG_ARCH_TEMPLATE,
            self.OPKG_OPTIONS_TEMPLATE,
            self.OPKG_FEEDS_TEMPLATE,
            self.ETC_PASSWD,
            self.ETC_GROUP,
            self.ETC_HOSTS,
        ]

        for conffile, template in zip(conffile_list, template_list):
            with open(sysroot + conffile, "w+", encoding="utf-8") as f:
                f.write(template.format(**self.context))
    #end function

#end class
