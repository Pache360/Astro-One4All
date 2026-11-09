from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from astroall.oat import identify, read_hash_reply
from astroall.timekeeping import clock_snapshot


class SerialStub:
    def __init__(self):
        self.commands, self.buffer = [], bytearray()

    def write(self, command):
        self.commands.append(command)
        self.buffer.extend({b":GVP#": b"OpenAstroTracker#", b":GVN#": b"v1.13.19#"}[command])

    def flush(self):
        pass

    def read(self, size):
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result


class IdentityTests(unittest.TestCase):
    def test_installed_version_is_reply_not_prepared_hex_version(self):
        serial = SerialStub()
        result = identify(serial)
        self.assertEqual(serial.commands, [b":GVP#", b":GVN#"])
        self.assertEqual(result["reported_version"], "v1.13.19")
        self.assertEqual(result["replies"][":GVP#"], "OpenAstroTracker#")

    def test_incomplete_response_times_out_without_adding_commands(self):
        serial = SerialStub()
        serial.buffer.extend(b"incomplete")
        with patch("astroall.oat.time.monotonic", side_effect=[0, 0, 4]):
            with self.assertRaises(TimeoutError):
                read_hash_reply(serial)
        self.assertEqual(serial.commands, [])


class TimeTests(unittest.TestCase):
    def test_local_display_does_not_change_utc_or_invent_site(self):
        result = clock_snapshot({"timezone": "America/Mexico_City", "longitude": None}, when=datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc))
        self.assertEqual(result["utc"], "2026-11-03T03:00:00+00:00")
        self.assertEqual(result["local"], "2026-11-02T21:00:00-06:00")
        self.assertIsNone(result["sidereal_hours"])
        self.assertIsNone(result["ha_hours"])

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            clock_snapshot({"timezone": "UTC"}, when=datetime(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()
