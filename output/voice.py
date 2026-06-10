"""Voice alert output module."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from threat.alert_level import AlertLevel

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

try:
    from gtts import gTTS
except ImportError:  # pragma: no cover
    gTTS = None


class VoiceAlert:
    """Generate and play spoken threat alerts with cooldown controls."""

    # Generic templates for all species (used as fallback).
    TEMPLATES = {
        AlertLevel.CAUTION: "Attention. A {species} has been detected {direction}. Please stay on the marked path and remain calm.",
        AlertLevel.HIGH: "Warning. A {species} is approaching from {direction}. Move away slowly. Do not run. Alert forest officers if possible.",
        AlertLevel.CRITICAL: "Emergency alert. A {species} is very close, {direction}. Move immediately to the nearest shelter. Walk calmly. Do not run. Forest officers have been notified.",
    }

    # Tiger-specific templates — HIGH RISK messaging.
    TEMPLATES_TIGER = {
        AlertLevel.CAUTION: "HIGH RISK alert. A tiger has been detected {direction}. This is extremely dangerous. Move away slowly and stay calm.",
        AlertLevel.HIGH: "HIGH RISK — Tiger warning! A tiger is approaching from {direction}. Do not run. Move away slowly and alert forest officers immediately.",
        AlertLevel.CRITICAL: "CRITICAL — HIGH RISK. A tiger is very close, {direction}. Move immediately to the nearest shelter. Do not run. Forest officers have been notified.",
    }

    # Deer-specific templates — LOW RISK messaging.
    TEMPLATES_DEER = {
        AlertLevel.CAUTION: "LOW RISK. A deer has been detected {direction}. Please maintain your distance and do not disturb the animal.",
        AlertLevel.HIGH: "LOW RISK warning. A deer is close from {direction}. Keep calm, maintain distance, and do not make sudden movements.",
        AlertLevel.CRITICAL: "LOW RISK — Deer very close, {direction}. Please back away slowly and give the animal space to move.",
    }

    # Map species name → custom template set.
    _SPECIES_TEMPLATES = {
        "tiger": TEMPLATES_TIGER,
        "deer": TEMPLATES_DEER,
    }

    def __init__(self, language: str = "en", use_online: bool = False, cooldown_seconds: int = 30):
        self.logger = logging.getLogger(__name__)
        self.language = language if language in {"en", "hi", "ta"} else "en"
        self.use_online = use_online
        self.cooldown_seconds = cooldown_seconds
        self.last_alerts: dict[tuple[str, str], datetime] = {}
        self.lock = threading.Lock()
        self.audio_dir = Path(__file__).resolve().parent / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.engine = pyttsx3.init() if pyttsx3 and not use_online else None

    def _message(self, species: str, alert_level: AlertLevel, direction: str, distance_m: int | None) -> str | None:
        if alert_level == AlertLevel.SAFE:
            return None
        template_set = self._SPECIES_TEMPLATES.get(species.lower(), self.TEMPLATES)
        template = template_set.get(alert_level)
        if not template:
            return None
        message = template.format(species=species, direction=direction)
        if distance_m is not None and distance_m >= 0:
            message = f"{message} Approximate distance: {distance_m} meters."
        return message

    def speak(
        self,
        species: str,
        alert_level: AlertLevel,
        direction: str = "nearby",
        distance_m: int | None = None,
        camera_zone: str = "default",
    ) -> bool:
        """Trigger non-blocking voice playback for eligible alerts."""
        message = self._message(species, alert_level, direction, distance_m)
        if not message:
            return False

        key = (species.lower(), camera_zone.lower(), alert_level.name)
        now = datetime.now(timezone.utc)
        with self.lock:
            last = self.last_alerts.get(key)
            if last and now - last < timedelta(seconds=self.cooldown_seconds):
                return False
            self.last_alerts[key] = now

        threading.Thread(target=self._play_message, args=(message, species, alert_level), daemon=True).start()
        return True

    def _play_message(self, message: str, species: str, alert_level: AlertLevel) -> None:
        try:
            if self.use_online and gTTS and pygame:
                filename = f"{species}_{alert_level.name}_{self.language}.mp3".replace(" ", "_").lower()
                path = self.audio_dir / filename
                if not path.exists():
                    tts = gTTS(text=message, lang=self.language)
                    tts.save(str(path))
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.play()
            elif self.engine:
                self.engine.say(message)
                self.engine.runAndWait()
            else:
                self.logger.warning("No TTS engine available")
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Voice playback failed: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    voice = VoiceAlert(use_online=False)
    logging.getLogger(__name__).info("Voice self-test: %s", voice.speak("tiger", AlertLevel.CAUTION, "ahead"))
