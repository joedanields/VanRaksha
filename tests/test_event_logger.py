import tempfile
import unittest
from pathlib import Path

from logger.event_logger import EventLogger


class EventLoggerTests(unittest.TestCase):
    def test_log_and_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            logger = EventLogger(str(db))
            logger.log_event({"species": "tiger", "threat_score": 88, "alert_level": "CRITICAL"})
            recent = logger.get_recent(10)
            self.assertEqual(len(recent), 1)
            stats = logger.get_stats()
            self.assertEqual(stats["total_events"], 1)
            self.assertEqual(stats["by_species"]["tiger"], 1)


if __name__ == "__main__":
    unittest.main()
