import logging
import os
import sys
import subprocess
from subprocess import PIPE, STDOUT
import time
import asyncio

logging.basicConfig(level=logging.DEBUG)

from impl.agent import JoyconAgent

agent = JoyconAgent()
agent.connect()
print("connected")
agent.pairing_action()
agent.return_to_game()

T = 0.6

WALK = [
    lambda: agent.l_stick_right,
    lambda: agent.l_stick_up,
    lambda: agent.l_stick_left,
    lambda: agent.l_stick_down,
]

DIR = 0
STEP = 0

def water():
    agent.press('A')
    agent.sleep(3.7)

def walk(dir):
    dir()
    agent.sleep(T)
    agent.l_stick_center

while True:
    STEP = 1 + DIR // 2
    dir = WALK[DIR % 4]
    dir()
    agent.sleep(0.07)
    agent.l_stick_center
    for i in range(STEP):
        water()
        walk(dir)
    DIR += 1

agent.cleanup()
