from datetime import datetime
from multiprocessing import Queue, Process, Manager
from threading import Thread, Event, currentThread
from queue import Empty, Full
from time import sleep

import logging
L = logging.getLogger(__name__)
_M = Manager()
_HEALTH_CHECK_INTERVAL = 6
_HEALTH_CHECK_MAX_MISS = 5
_HEALTH_CHECK_INITIAL_GRACE_PERIODS = 7
_HEALTH_CHECK_CLEAN_UP_GRACE_PERIODS = 20

from impl import *

class Controller:
    def __init__(self, async_exec_queue=None):
        self.current_job = None
        self.available_tasks = {
            "auto_press_A": AutoPressATask,
            "meteor_watching": MeteorWatchingTask,
            "meteor_watching_also_sleep": MeteorWatchingAlsoSleepTask,
        }
        self.factory = TerminationConditionFactory()
        self._async_exec_queue = async_exec_queue

    def get_status(self):
        self._maybe_update_status()
        return {
            "options": self._get_available_tasks_conditions(),
            "busy": bool(self.current_job),
            "task_description": self.current_job.description if self.current_job else "None",
        }

    def _maybe_update_status(self):
        if not self.current_job:
            return

        if not self.current_job.is_alive():
            self.current_job = None

    def _get_available_tasks_conditions(self):
        return {
            "tasks": list(self.available_tasks.keys()),
            "conditions": self.factory.get_options(),
        }

    def stop(self):
        if self.current_job:
            self.current_job.stop()
        self._maybe_update_status()

    def _create_task(self, task_name, termination_string):
        self._maybe_update_status()
        if self.current_job:
            return False, "Currently busy."

        try:
            task_base = self.available_tasks[task_name]
            condition, cond_desc = self.factory.from_string(termination_string)
            desc = "Task: {} | Condition: {} | Created: {}".format(task_name, cond_desc, datetime.now().isoformat())
            self.current_job = Job(task_base, condition, desc, self._async_exec_queue)
            self.current_job.start()
            return True, desc
        except Exception as e:
            L.error("Task creation failure.", exc_info=e)
            return False, str(e)

    def start(self, task_name, termination_string):
        success, msg = self._create_task(task_name, termination_string)
        return success, {
            "success": success,
            "msg": msg,
        }

class Job:
    def __init__(self, task_base, condition, description, async_exec_queue=None):
        self.task_base = task_base
        self.condition = condition
        self.description = description
        self.task = None
        self._exec_queue, self._result_queue = async_exec_queue
        self._setup_health_check()

    def _health_check(self):
        while not self._health_stop:
            if self._health_restart_or_wait.wait(_HEALTH_CHECK_INTERVAL):
                self._health_restart_or_wait.clear()
                try:
                    while not self._health_queue.empty():
                        self._health_queue.get_nowait()
                except Empty:
                    pass
                self._restart()
                continue

            if not self._health_enabled:
                continue

            if self._health_initial_grace_periods > 0:
                L.info("Health check grace period.")
                self._health_initial_grace_periods -= 1
                continue

            try:
                L.info("Health check ping.")
                self._health_queue.put_nowait(True)
            except Full:
                if self.condition():
                    L.warning("The job is complete.")
                    if self._health_clean_up_grace_periods > 0 and self.task and self.task.is_alive():
                        L.info("Grace period left: %d.", self._health_clean_up_grace_periods)
                        self._health_clean_up_grace_periods -= 1
                    else:
                        L.warning("Stopping job.")
                        self.stop()
                elif self.task:
                    if self.task.is_alive():
                        L.error("Process stuck, restarting.")
                    else:
                        L.error("Process stopped unexpectedly, restarting.")
                    self._health_restart_or_wait.set()
                else:
                    L.error("Task is not set. The job is stopped? Stopping health check.")
                    self._health_enabled = False

    def _tear_down_health_check(self):
        if self._health_restart_or_wait:
            self._health_restart_or_wait.clear()

        self._health_enabled = False
        self._health_stop = True
        if self._health_thread and currentThread() != self._health_thread:
            self._health_thread.join()

    def _setup_health_check(self):
        self._health_queue = _M.Queue(maxsize=_HEALTH_CHECK_MAX_MISS)
        self._health_enabled = False
        self._health_stop = False
        self._health_initial_grace_periods = _HEALTH_CHECK_INITIAL_GRACE_PERIODS
        self._health_clean_up_grace_periods = _HEALTH_CHECK_CLEAN_UP_GRACE_PERIODS
        self._health_restart_or_wait = Event()
        self._health_thread = Thread(target=self._health_check)
        self._health_thread.setDaemon(True)
        self._health_thread.start()

    @staticmethod
    def _start_task(target):
        task = Process(target=target.run, args=())
        task.start()
        Job.__last_task = task

    def _restart(self, start=True, stop=True):
        if stop and self.task:
            self.task.kill()
            self.task = None
            self._health_enabled = False

        if start and not self.task:
            target = self.task_base(self.condition)
            target._health_check = self._health_queue
            if self._exec_queue:
                self._exec_queue.put_nowait((Job._start_task, (target,)))
                self._result_queue.get(timeout=10)
            else:
                self._start_task()
            self.task = Job.__last_task
            self._health_initial_grace_periods = _HEALTH_CHECK_INITIAL_GRACE_PERIODS
            self._health_clean_up_grace_periods = _HEALTH_CHECK_CLEAN_UP_GRACE_PERIODS
            self._health_enabled = True

    def start(self):
        L.info("Job is starting.")
        assert not self._health_stop
        self._health_enabled = True
        self._health_restart_or_wait.set()

    def stop(self):
        self._health_enabled = False
        self._health_stop = True
        self._health_restart_or_wait.clear()
        self._restart(start=False, stop=True)
        self._tear_down_health_check()
        L.info("Job stopped.")

    def is_alive(self):
        if self.task and self.task.is_alive():
            return True

        return not self._health_stop

    def get_status(self):
        return {
            "desc": self.description,
            "alive": self.is_alive(),
        }


class TerminationConditionFactory:
    def __init__(self):
        self.options = {
            "for": (For, 3, "Run task for a specific period."),
            "until": (UntilNextHM, 2, "Run task until a specific time. Check your timezone settings."),
#            "times": (Times, 1, "Run task for a specific number of times."),
            "eternity": (ForEternity, 0, "Run task until the app crash.")
        }

    def from_string(self, s):
        try:
            method_name, remainder = s.split("-")
            method, _, desc = self.options[method_name]
            args = [int(x) for x in remainder.split(".")] if remainder else []
            return method(*args), desc
        except:
            return (lambda: True), "Condition parse failure."

    def get_options(self):
        result = []
        for k, v in self.options.items():
            result.append({
                "name": k,
                "args": v[1],
                "desc": v[2],
            })
        return result


def setup_main_thread_function_call_queue(aux_main):
    exec_queue = Queue(maxsize=10)
    result_queue = Queue(maxsize=10)
    t = Thread(name="Auxiliary-main", target=aux_main, args=((exec_queue, result_queue),))
    t.start()
    while True:
        try:
            f, args = exec_queue.get(timeout=120)
            L.info("Run task in main idle.")
            result_queue.put_nowait(f(*args))
        except Empty:
            L.info("Main thread is idle for last two minutes.")
        except Full:
            L.warning("Main thread response queue is full.")
