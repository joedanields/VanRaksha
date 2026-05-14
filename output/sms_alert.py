"""SMS alert dispatcher."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import config
from threat.alert_level import AlertLevel

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover
    Client = None


class SMSAlert:
    """Dispatch alert messages via Twilio or GSM with cooldown protection."""

    def __init__(self, provider: str = "twilio"):
        self.logger = logging.getLogger(__name__)
        self.provider = provider
        self.lock = threading.Lock()
        self.cooldowns: dict[tuple[str, str], datetime] = {}
        self.cooldown = timedelta(minutes=config.SMS_COOLDOWN_MINUTES)

        self.twilio_client = None
        if provider == "twilio" and Client and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    def send(self, species: str, alert_level: AlertLevel, camera_zone: str, score: float) -> bool:
        """Schedule non-blocking SMS send for HIGH/CRITICAL alerts."""
        if alert_level not in (AlertLevel.HIGH, AlertLevel.CRITICAL):
            return False

        key = (species.lower(), camera_zone.lower())
        now = datetime.now(timezone.utc)
        with self.lock:
            if key in self.cooldowns and now - self.cooldowns[key] < self.cooldown:
                return False
            self.cooldowns[key] = now

        message = (
            f"[VanRaksha AI] ALERT: {alert_level.name}\n"
            f"Zone: {camera_zone}\n"
            f"Species: {species}\n"
            f"Threat Score: {score}/100\n"
            f"Time: {datetime.now(timezone.utc).strftime('%H:%M %d-%m-%Y')}\n"
            "Action required. Please respond."
        )
        threading.Thread(target=self._dispatch, args=(message,), daemon=True).start()
        return True

    def _dispatch(self, message: str) -> None:
        try:
            if self.provider == "twilio" and self.twilio_client:
                self._send_twilio(message)
            elif self.provider == "gsm" and serial:
                self._send_gsm(message)
            else:
                self.logger.info("[SMS MOCK] %s", message)
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Failed to send SMS: %s", exc)

    def _send_twilio(self, message: str) -> None:
        for number in config.OFFICER_PHONE_LIST:
            self.twilio_client.messages.create(body=message, from_=config.TWILIO_FROM_NUMBER, to=number)

    def _send_gsm(self, message: str) -> None:  # pragma: no cover
        ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
        ser.write(b"AT\r")
        time.sleep(0.2)
        ser.write(b"AT+CMGF=1\r")
        time.sleep(0.2)
        for number in config.OFFICER_PHONE_LIST:
            ser.write(f'AT+CMGS="{number}"\r'.encode())
            time.sleep(0.2)
            ser.write(message.encode() + b"\x1A")
            time.sleep(0.5)
        ser.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sms = SMSAlert(provider="mock")
    logging.getLogger(__name__).info("SMS self-test: %s", sms.send("tiger", AlertLevel.HIGH, "Zone-A", 88.1))
