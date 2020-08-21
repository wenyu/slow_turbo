#!/usr/bin/sudo /usr/bin/python3

import logging
from impl import *

logging.basicConfig(level=logging.DEBUG)
t = MeteorWatchingTask(UntilNext("4:00"))
t.run()