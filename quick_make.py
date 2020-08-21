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

ITEM_TIME = 12.5
start = time.time()

while time.time() - start < ITEM_TIME * 40:
    agent.press("A", 0.2)

agent.cleanup()
