from .repeat_until_task import *
from .agent import JoyconAgent

class _BasicTask(RepeatUntilTask):
    def _before(self):
        self.agent = JoyconAgent()
        self.agent.connect()
        self.agent.pairing_action()
        self.agent.return_to_game()

    def _after(self):
        self.agent.cleanup()


class _AlsoSleepMixin(RepeatUntilTask):
    def _after(self):
        self.agent.reset_buttons()
        self.agent.minus
        self.agent.sleep(1)
        self.agent.b
        self.agent.a
        self.agent.sleep(5)
        self.agent.a
        self.agent.sleep(3)
        self.agent.a
        self.agent.sleep(60)
        self.agent.hibernate()
        super()._after()

class AutoPressATask(_BasicTask):
    def _loop_body(self):
        self.agent.press("A", 0.2)


class MeteorWatchingTask(_BasicTask):
    def _head_up(self):
        self.agent.r_stick_up
        self.agent.sleep(0.15)
        self.agent.r_stick_center
        self.agent.sleep(0.15)

    def _before(self):
        super()._before()
        self.agent.B
        self.agent.B
        self.agent.B
        self.agent.B
        self._head_up()
        self.agent.DOWN
        self.agent.DOWN
        self._head_up()
        self.i = 0

    def _loop_body(self):
        if not self.i:
            self.agent.B
            self.agent.DOWN
            self._head_up()
            self.agent.B
            self.agent.DOWN
            self._head_up()

        if not (self.i & 0xF):
            self._head_up()
            self._head_up()

        self.agent.press("A", 1, 0.5)
        self.i = 0xFF & (self.i + 1)


class MeteorWatchingAlsoSleepTask(_AlsoSleepMixin, MeteorWatchingTask):
    pass


_EXPORTS = [
    AutoPressATask,
    MeteorWatchingTask,
    MeteorWatchingAlsoSleepTask,
]
