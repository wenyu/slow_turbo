import logging
from controller import Controller, setup_main_thread_function_call_queue
from impl import *
from time import sleep

logging.basicConfig(level=logging.DEBUG)

def main(Q):
    c = Controller(Q)

    class DummyTask(RepeatUntilTask):
        def _before(self):
            print("Start")
            self.i = 3

        def _loop_body(self):
            print(self.i)
            print(self.termination_condition)
            if not self.i:
                sleep(100)
                return
            self.i -= 1
            sleep(1)

        def _after(self):
            print("End")

    c.available_tasks["dummy"] = DummyTask
    print(c.get_status())
    print(c.start("meteor_watching", "for-0.12.0"))
    sleep(200)

setup_main_thread_function_call_queue(main)