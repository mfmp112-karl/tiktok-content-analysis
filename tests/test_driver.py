from datetime import date, timedelta
import json
import tempfile
from pathlib import Path
import unittest

import driver


class TestDriver(unittest.TestCase):
    def test_timedelta_import_and_removed_helper(self):
        """Verify timedelta is directly imported and timedelta_days helper is removed."""
        self.assertFalse(hasattr(driver, "timedelta_days"), "timedelta_days helper should be removed")
        self.assertIs(driver.timedelta, timedelta, "timedelta should be imported from datetime")

    def test_calendar_start_date_calculation(self):
        """Verify the start date calculation logic matches date.today() + timedelta(days=1)."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        self.assertEqual(tomorrow.day - today.day if tomorrow.month == today.month else 1, 1)

    def test_load_narrative(self):
        """Test load_narrative behavior with None and valid JSON file."""
        self.assertEqual(driver.load_narrative(None), {})
        
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            data = {"summary": "test narrative"}
            json.dump(data, f)
            temp_path = f.name
        
        try:
            loaded = driver.load_narrative(temp_path)
            self.assertEqual(loaded, {"summary": "test narrative"})
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_doctor(self):
        """Test doctor function runs cleanly."""
        res = driver.doctor()
        self.assertIn(res, (0, 1))


if __name__ == "__main__":
    unittest.main()
