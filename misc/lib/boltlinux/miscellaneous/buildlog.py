# -*- encoding: utf-8 -*-
#
# Proprietary
#
# Copyright (c) 2022 Tobias Koch <tobias.koch@gmail.com>
#

import os
import select

from boltlinux.error import BoltError
from boltlinux.miscellaneous.workerthread import WorkerThread

class BuildLog:

    class Error(BoltError):
        pass

    class LogForwarder(WorkerThread):

        def __init__(self, stdout_read, stderr_read, stdout_write,
                stderr_write, logfilefd, callbacks):
            super().__init__(name="log-shovel", interval=30.0)

            self._stdout_read  = stdout_read
            self._stdout_write = stdout_write
            self._stderr_read  = stderr_read
            self._stderr_write = stderr_write
            self._logfilefd    = logfilefd
            self._callbacks    = callbacks
        #end function

        def work(self):
            p = select.poll()

            os.set_blocking(self._stderr_read, False)

            if self._stdout_read:
                os.set_blocking(self._stdout_read, False)
                p.register(self._stdout_read, select.POLLIN)

            if self._stderr_read:
                os.set_blocking(self._stderr_read, False)
                p.register(self._stderr_read, select.POLLIN)

            while not self._stop_event.is_set():
                fds = p.poll(500)

                for fd, _ in fds:
                    try:
                        bytes_ = os.read(fd, 4096)
                    except OSError:
                        continue

                    if not bytes_:
                        continue

                    if fd == self._stderr_read:
                        if self._stderr_write:
                            os.write(self._stderr_write, bytes_)
                        elif self._stdout_write:
                            os.write(self._stdout_write, bytes_)
                    else:
                        if self._stdout_write:
                            os.write(self._stdout_write, bytes_)
                        elif self._stderr_write:
                            os.write(self._stderr_write, bytes_)
                    #end if

                    if self._logfilefd:
                        os.write(self._logfilefd, bytes_)

                    for cb in self._callbacks:
                        cb(bytes_)
                #end for
            #end while

            for fd in [self._stdout_read, self._stderr_read, self._logfilefd]:
                try:
                    if fd is not None:
                        os.close(fd)
                except OSError:
                    pass
            #end for
        #end function

        def __enter__(self):
            self.start()

        def __exit__(self, type_, value, traceback):
            self.stop()
            self.join()

    #end class

    def __init__(self, logfile=None, preserve=True, callbacks=None):
        self._logfile      = logfile
        self._preserve     = preserve
        self._logfilefd    = None
        self._stdout_orig  = None
        self._stdout_read  = None
        self._stdout_write = None
        self._stderr_orig  = None
        self._stderr_read  = None
        self._stderr_write = None
        self._log_shovel   = None
        self._callbacks    = callbacks if callbacks else []
    #end function

    def __enter__(self):
        if self._logfile:
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
            if not self._preserve:
                flags |= os.O_TRUNC

            try:
                self._logfilefd = os.open(self._logfile, flags)
            except OSError as e:
                raise BuildLog.Error(
                    'failed to open logfile "{}": {}'.format(
                        self._logfile, str(e)
                    )
                )
            #end try
        #end if

        self._stdout_read, self._stdout_write = os.pipe()
        self._stderr_read, self._stderr_write = os.pipe()
        self._stdout_orig = os.dup(1)
        self._stderr_orig = os.dup(2)

        self._log_shovel = BuildLog.LogForwarder(
            self._stdout_read,
            self._stderr_read,
            self._stdout_orig,
            self._stderr_orig,
            self._logfilefd,
            self._callbacks
        )
        self._log_shovel.start()

        # Redirect stdout and stderr to the pipes
        os.dup2(self._stdout_write, 1)
        os.dup2(self._stderr_write, 2)

        return self
    #end function

    def __exit__(self, type_, value, traceback):
        # Restore stdout and stderr
        os.dup2(self._stdout_orig, 1)
        os.dup2(self._stderr_orig, 2)

        self._log_shovel.stop()
        self._log_shovel.join()

        fds_to_close = [
            self._stdout_orig,
            self._stdout_write,
            self._stderr_orig,
            self._stderr_write,
        ]

        for fd in fds_to_close:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            #end if
        #end for

        self._logfilefd = None
    #end function

#end class
