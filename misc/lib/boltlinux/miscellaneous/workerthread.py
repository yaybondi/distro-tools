# -*- encoding: utf-8 -*-
#
# Proprietary
#
# Copyright (c) 2021 Tobias Koch <tobias.koch@gmail.com>
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

#end class
