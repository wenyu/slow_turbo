import time
from datetime import datetime, timedelta
from multiprocessing import Queue
from queue import Empty

import logging
L = logging.getLogger(__name__)

class RepeatUntilTask:
    def __init__(self, termination_condition=lambda: False):
        self.termination_condition = termination_condition
        self.stop_requested = False
        self.started = False
        self.finished = False
        self._health_check = None

    def run(self):
        if self.started:
            return
        self.started = True
        L.info("Setting up task.")
        self._before()
        L.info("Running task.")
        L.debug("Stop requested: %s  Condition: %s", self.stop_requested, str(self.termination_condition))
        while not self.stop_requested and not self.termination_condition():
            if self._health_check:
                try:
                    while not self._health_check.empty():
                        if self._health_check.get_nowait():
                            L.debug("Health check ACK'ed.")
                except Empty:
                    break
            self._loop_body()
            L.debug("Stop requested: %s  Condition: %s", self.stop_requested, str(self.termination_condition))

        L.info("Finishing task.")
        self._after()
        L.info("Task finished.")
        self.finished = True

    def stop(self):
        self.stop_requested = True

    def _before(self):
        pass

    def _loop_body(self):
        pass

    def _after(self):
        pass


class Times:
    def __init__(self, times=1):
        self.times = times

    def __call__(self, *args, **kwargs):
        if self.times <= 0:
            return True
        self.times -= 1
        return False

    def __str__(self):
        return "Condition: %d times left." % self.times


class UntilEpoch:
    def __init__(self, expiring_epoch=0):
        self.expiration_time = expiring_epoch

    def __call__(self, *args, **kwargs):
        return time.time() > self.expiration_time

    def __str__(self):
        return "Condition: Expiring %d, currently %d." % (self.expiration_time, time.time())


def For(h=0, m=0, s=0):
    return UntilEpoch(time.time() + h * 3600 + m * 60 + s)


def UntilNextHM(h=4, m=0):
    now = datetime.now()
    expiration = datetime(now.year, now.month, now.day, h, m)

    if expiration <= now:
        expiration += timedelta(days=1)

    return UntilEpoch(expiration.timestamp())


def UntilNext(time_HM="04:00"):
    h, m = time_HM.split(":")
    return UntilNextHM(int(h), int(m))


def ForEternity():
    def __call__(self, *args, **kwargs):
        return False

    def __str__(self):
        return "Condition: for eternity."
