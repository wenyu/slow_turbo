from .agent import JoyconAgent
from .joycon_robot_tasks import _EXPORTS
from .repeat_until_task import *

for func in _EXPORTS:
    locals()[func.__name__] = func
