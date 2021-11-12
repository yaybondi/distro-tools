# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
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
import random
import sys
import threading
import time
import traceback

LOGGER = logging.getLogger(__name__)

class WorkerThread(threading.Thread):

    def __init__(self, name, interval):
        super().__init__(name=name)
        self._interval = interval
        self._stop_event = threading.Event()
    #end function

    def run(self):
        LOGGER.info('thread "{}" is starting up.'.format(self.name))

        while not self._stop_event.is_set():
            next_start = time.time() + random.uniform(
                self._interval * 0.9, self._interval * 1.1
            )

            try:
                self.work()
            except Exception as e:
                _, exc_value, exc_tb = sys.exc_info()
                frame = traceback.TracebackException(
                    type(exc_value), exc_value, exc_tb, limit=None
                ).stack[-1]

                filename = os.path.basename(frame.filename)
                msg = \
                    'ACHTUNG *CRASH* in "{}", thread "{}" line "{}": ' \
                    '{} {}'.format(
                        filename,
                        self.name,
                        frame.lineno,
                        type(e).__name__,
                        e
                    )

                LOGGER.error(msg)
            #end try

            self._stop_event.wait(timeout=max(0.0, next_start - time.time()))
        #end while

        LOGGER.info('thread "{}" is shutting down.'.format(self.name))
    #end function

    def work(self):
        raise NotImplementedError("work method not implemented on subclass.")

    def stop(self, *args, **kwargs):
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

#end class
