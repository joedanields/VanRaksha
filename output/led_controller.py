"""LED and buzzer alert controller."""
from __future__ import annotations

import logging
import time

from threat.alert_level import AlertLevel

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover
    GPIO = None

import config


class LEDController:
    """Control physical or simulated LED patterns for threat levels."""

    COMMANDS = {
        AlertLevel.SAFE: b"G",
        AlertLevel.CAUTION: b"Y",
        AlertLevel.HIGH: b"O",
        AlertLevel.CRITICAL: b"R",
    }

    def __init__(self, mode: str = "gpio"):
        self.logger = logging.getLogger(__name__)
        self.mode = mode
        self.serial_conn = None

        if self.mode == "serial" and serial:
            try:
                self.serial_conn = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
            except Exception:
                self.mode = "mock"
        elif self.mode == "gpio" and GPIO is None:
            self.mode = "mock"

    def set_alert(self, alert_level: AlertLevel):
        """Trigger configured LED pattern for current alert level."""
        if self.mode == "serial" and self.serial_conn:
            self.serial_conn.write(self.COMMANDS[alert_level])
            return

        if self.mode == "gpio" and GPIO:
            self._gpio_pattern(alert_level)
            return

        colors = {
            AlertLevel.SAFE: "\033[92mSAFE\033[0m",
            AlertLevel.CAUTION: "\033[93mCAUTION\033[0m",
            AlertLevel.HIGH: "\033[38;5;208mHIGH\033[0m",
            AlertLevel.CRITICAL: "\033[91mCRITICAL\033[0m",
        }
        self.logger.info("[LED MOCK] %s", colors[alert_level])

    def _gpio_pattern(self, alert_level: AlertLevel):  # pragma: no cover
        if alert_level == AlertLevel.HIGH:
            time.sleep(0.5)
        elif alert_level == AlertLevel.CRITICAL:
            time.sleep(0.1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    LEDController(mode="mock").set_alert(AlertLevel.CAUTION)
