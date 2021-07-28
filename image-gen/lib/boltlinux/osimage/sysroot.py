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

import logging
import os
import shlex
import signal
import subprocess
import time

from boltlinux.error import BoltError

LOGGER = logging.getLogger(__name__)

class Sysroot:

    class Error(BoltError):
        pass

    MOUNTPOINTS = ["dev", "proc", "sys"]

    def __init__(self, sysroot):
        self.sysroot = os.path.realpath(sysroot)

    def __enter__(self):
        for mountpoint in self.MOUNTPOINTS:
            src = os.sep + mountpoint
            dst = self.sysroot + src

            if self._is_mounted(dst):
                LOGGER.warning('"{dst}" is already mounted.'.format(dst=dst))
            else:
                self._bind_mount(src, dst)
        #end for

        return self
    #end function

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate_processes()

        for mountpoint in self.MOUNTPOINTS:
            src = os.sep + mountpoint
            dst = self.sysroot + src

            if not self._is_mounted(dst):
                LOGGER.warning('"{dst}" is not mounted.'.format(dst=dst))
            else:
                self._umount(dst)
        #end for

        return False
    #end function

    def terminate_processes(self):
        found = True

        while found:
            found = False

            for entry in os.listdir("/proc"):
                try:
                    pid = int(entry)

                    proc_root = os.path.normpath(
                        os.path.realpath("/proc/{}/root".format(entry))
                    )

                    proc_entry = "/proc/{}".format(entry)

                    if self.sysroot == proc_root:
                        found = True

                        os.kill(-pid, signal.SIGTERM)
                        for i in range(10):
                            os.lstat(proc_entry)
                            time.sleep(0.05 * 1.1**i)

                        os.kill(-pid, signal.SIGKILL)
                        for i in range(10):
                            os.lstat(proc_entry)
                            time.sleep(0.05 * 1.1**i)
                    #end if
                except (ValueError, ProcessLookupError, PermissionError,
                            FileNotFoundError):
                    pass
            #end for
        #end while
    #end function

    # HELPERS

    def _is_mounted(self, path):
        with open("/proc/mounts", "r", encoding="utf-8") as f:
            buf = f.read()

        for line in buf.splitlines():
            _, mountpoint, _, _, _, _ = line.strip().split()
            if os.path.realpath(mountpoint) == os.path.realpath(path):
                return True
        #end for

        return False
    #end function

    def _bind_mount(self, src, dst):
        proc = subprocess.run(
            shlex.split("mount -o bind {src} {dst}".format(src=src, dst=dst)),
            check = False
        )
        if proc.returncode != 0:
            LOGGER.warning(
                'failed to mount "{src}" on "{dst}".'.format(src=src, dst=dst)
            )
    #end function

    def _umount(self, path):
        proc = subprocess.run(
            shlex.split("umount {path}".format(path=path)),
            check = False
        )
        if proc.returncode != 0:
            LOGGER.warning('failed to umount "{path}".'.format(path=path))
    #end function

#end class
