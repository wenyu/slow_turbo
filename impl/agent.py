import asyncio
import logging
from threading import Thread

from .joycontrol.controller import Controller
from .joycontrol.protocol import controller_protocol_factory
from .joycontrol.server import create_hid_server

L = logging.getLogger(__name__)
CTL_PSM, ITR_PSM = 17, 19

class JoyconAgent(object):
    def __init__(self):
        self._controller_state = None
        self._transport, self._protocol = None, None

        spi_flash = [0xFF] * 524287
        # L-stick factory calibration
        spi_flash[0x603D:0x6046] = [0x00, 0x07, 0x70, 0x00, 0x08, 0x80, 0x00, 0x07, 0x70]
        # R-stick factory calibration
        spi_flash[0x6046:0x604F] = [0x00, 0x08, 0x80, 0x00, 0x07, 0x70, 0x00, 0x07, 0x70]
        # Color Tweak.
        spi_flash[0x6050:0x6055] = [0x00, 0x80, 0xFF, 0x3F, 0x30, 0x80]
        spi_flash = bytes(spi_flash)

        self._loop = asyncio.get_event_loop()

        self.__controller_state_preparer = create_hid_server(
                controller_protocol_factory(Controller.PRO_CONTROLLER, spi_flash))

    async def _prepare_controller_state(self):
        self._transport, self._protocol = await self.__controller_state_preparer
        assert self._protocol
        controller_state = self._protocol.get_controller_state()
        assert controller_state
        L.info("Controller connected.")
        await asyncio.sleep(1)

        button_state = controller_state.button_state
        while not self._protocol.sig_set_player_lights.is_set():
            button_state.set_button("l")
            button_state.set_button("r")
            await controller_state.send()
            await asyncio.sleep(3)
            button_state.set_button("l", pushed=False)
            button_state.set_button("r", pushed=False)
            await controller_state.send()
            await asyncio.sleep(1)

        L.info("Controller is assigned for playing.")
        self._controller_state = controller_state
        self._button_state = self._controller_state.button_state
        self._l_stick_state = self._controller_state.l_stick_state
        self._r_stick_state = self._controller_state.r_stick_state
        await asyncio.sleep(1)
        L.info("Buttons available: %s", self._button_state.get_available_buttons())

    def _button_press_setter(self, btn):
        def set_to_state(pressed):
            nonlocal btn
            L.info("Button: %s  Pressed: %s", btn.upper(), pressed)
            self._button_state.set_button(btn, pushed=pressed)
            self._loop.run_until_complete(self._controller_state.send())
        return set_to_state

    def _stick_direction_setter(self, btn, dir):
        if btn == "l_stick":
            stick = self._l_stick_state
        else:
            stick = self._r_stick_state
        getattr(stick, "set_" + dir)()
        L.info("Move %s to %s.", btn, dir)
        self._loop.run_until_complete(self._controller_state.send())

    def _commit(self):
        self._loop.run_until_complete(self._controller_state.send())

    def reset_buttons(self):
        for btn in self._button_state.get_available_buttons():
            self._button_state.set_button(btn, pushed=False)
        self._l_stick_state.set_center()
        self._r_stick_state.set_center()
        L.info("Reset all inputs.")
        self._loop.run_until_complete(self._controller_state.send())

    def sleep(self, interval):
        self._loop.run_until_complete(asyncio.sleep(interval))

    def connect(self):
        if self._controller_state:
            L.warning("Controller already connected.")
            return
        self._loop.run_until_complete(self._prepare_controller_state())

    def pairing_action(self, wait_time=5):
        self.reset_buttons()
        self.sleep(0.25)
        self.l_down
        self.r_down
        for _ in range(3):
            self.a
        self.a_down
        self.sleep(max(0, wait_time-3))
        self.reset_buttons()
        self.sleep(2)

    def return_to_game(self):
        self.reset_buttons()
        self.press("HOME", 0.3)
        self.sleep(1)
        self.press("DOWN", 0.2)
        self.press("DOWN", 0.2)
        self.press("UP")
        self.l_stick_left
        self.sleep(2)
        self.l_stick_center
        self.press("A")
        self.sleep(1)

    def hibernate(self):
        self.reset_buttons()
        self.press("HOME", 3)
        self.press("A")

    def press(self, btn, interval=0.25, gap=0.125):
        btn = btn.lower()
        self._button_press_setter(btn)(True)
        self.sleep(interval - gap)
        self._button_press_setter(btn)(False)
        self.sleep(gap)

    def cleanup(self):
        self._loop.run_until_complete(self._transport.close())

    def __getattr__(self, item):
        key = item.lower()
        if key in self._button_state.get_available_buttons():
            self.press(key)
            return

        segs = key.split("_")

        if segs[0] == "set":  # set_XXXX
            btn_name = key[4:]
            return self._button_press_setter(btn_name)

        elif segs[1] == "stick":  # {l,r}_stick_{up,down,left,right,center}
            btn_name = key[:7]
            direction = segs[2]
            return self._stick_direction_setter(btn_name, direction)

        elif segs[-1] == "up":  # XXXX_up
            self._button_press_setter(key[:-3])(False)
            return

        elif segs[-1] == "down":  # XXXX_down
            self._button_press_setter(key[:-5])(True)
            return


        return super().__getattribute__(item)
