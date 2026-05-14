"""Night/day model switcher."""
from __future__ import annotations

import logging
from datetime import datetime


class NightSwitch:
    """Switches between day and night model paths by hour window."""

    def __init__(self, day_model_path: str, night_model_path: str | None, night_start_hour: int = 18, night_end_hour: int = 6):
        self.logger = logging.getLogger(__name__)
        self.day_model_path = day_model_path
        self.night_model_path = night_model_path
        self.night_start_hour = night_start_hour
        self.night_end_hour = night_end_hour

    def is_night(self) -> bool:
        """True if current hour is in configured night range."""
        now = datetime.now().hour
        if self.night_start_hour <= self.night_end_hour:
            return self.night_start_hour <= now < self.night_end_hour
        return now >= self.night_start_hour or now < self.night_end_hour

    def get_active_model_path(self) -> str:
        """Return day or night model path based on current time."""
        if not self.night_model_path:
            self.logger.warning("Night model not configured — using day model 24/7")
            return self.day_model_path
        return self.night_model_path if self.is_night() else self.day_model_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    switch = NightSwitch("day.pt", None)
    logging.getLogger(__name__).info("Night switch self-test: %s", switch.get_active_model_path())
