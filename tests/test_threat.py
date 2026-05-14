import unittest

from threat.alert_level import AlertLevel, get_alert_level
from threat.species_index import get_danger_score


class ThreatLogicTests(unittest.TestCase):
    def test_get_danger_score_defaults_to_unknown(self):
        self.assertEqual(get_danger_score("mystery"), 5)

    def test_alert_level_mapping(self):
        self.assertEqual(get_alert_level(20), AlertLevel.SAFE)
        self.assertEqual(get_alert_level(40), AlertLevel.CAUTION)
        self.assertEqual(get_alert_level(60), AlertLevel.HIGH)
        self.assertEqual(get_alert_level(90), AlertLevel.CRITICAL)


if __name__ == "__main__":
    unittest.main()
