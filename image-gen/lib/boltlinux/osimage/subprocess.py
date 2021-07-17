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

import fcntl
import locale
import logging
import os
import select
import sys

from boltlinux.error import BoltError

LOGGER = logging.getLogger(__name__)

class Subprocess:

    class Error(BoltError):
        pass

    @staticmethod
    def run(sysroot, executable, args, env=None, chroot=False):
        err_r, err_w = os.pipe()

        child_pid, pty_m = os.forkpty()

        if not child_pid:
            try:
                null_fd = os.open(os.devnull, os.O_RDONLY)

                if chroot:
                    try:
                        os.chroot(sysroot)
                    except Exception as e:
                        raise Subprocess.Error(
                            'failed to chroot to "{}": {}'.format(
                                sysroot, str(e)
                            )
                        )
                #end if

                if env is None:
                    env = {}

                os.dup2(err_w, sys.stderr.fileno())
                os.close(err_r)
                os.dup2(null_fd, sys.stdin.fileno())

                try:
                    os.execvpe(executable, args, env)
                except Exception as e:
                    raise Subprocess.Error(
                        'could not execute {}: {}.'.format(
                            os.path.basename(executable), str(e)
                        )
                    )
            except Exception as e:
                LOGGER.error(str(e))

            os._exit(-1)
        else:
            os.close(err_w)

            fd_list = [pty_m, err_r]

            for fd in fd_list:
                fcntl.fcntl(
                    fd,
                    fcntl.F_SETFL,
                    fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
                )
            #end for

            encoding = locale.getpreferredencoding(do_setlocale=False)

            child_stdout = open(pty_m, "r", encoding=encoding, buffering=1)
            child_stderr = open(err_r, "r", encoding=encoding, buffering=1)

            status = 0
            exit_next = False

            while True:
                r, w, x = select.select([child_stdout, child_stderr], [], [])

                if child_stdout in r:
                    try:
                        for line in child_stdout:
                            sys.stdout.write(line)
                    except OSError:
                        pass
                #end if

                if child_stderr in r:
                    try:
                        for line in child_stderr:
                            if sys.stderr.isatty():
                                sys.stderr.write("\033[31m" + line + "\033[0m")
                            else:
                                sys.stderr.write(line)
                    except OSError:
                        pass
                #end if

                if exit_next:
                    break

                wpid, status = os.waitpid(child_pid, os.WNOHANG)

                if (wpid, status) == (0, 0):
                    continue
                if not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                    continue

                exit_next = True
            #end while

            if os.WIFSIGNALED(status):
                raise Subprocess.Error(
                    "subprocess terminated by signal {}.".format(
                        os.WTERMSIG(status)
                    )
                )
            elif os.WEXITSTATUS(status) != 0:
                raise Subprocess.Error(
                    "subprocess terminated with exit status {}.".format(
                        os.WEXITSTATUS(status)
                    )
                )
            #end if
        #end if
    #end function

#end class
