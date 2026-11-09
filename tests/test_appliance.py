import math
import unittest
import xml.etree.ElementTree as ET

from astroall.indi import IndiClient, IndiError
from astroall.night import red_ramps
from astroall.optics import field_width
from astroall.polar import estimate_from_vectors, estimate_polar, horizon_vector


class IndiTests(unittest.TestCase):
    def client(self):
        client = IndiClient()
        client.parser = ET.XMLPullParser(events=("start", "end"))
        client.parser.feed("<stream>")
        client.depth, client.root = 0, None
        return client

    def test_fragmented_unicode_messages_and_bounded_xml_tree(self):
        client = self.client()
        definition = '<defNumberVector device="OAT" name="EQUATORIAL_EOD_COORD" state="Ok" perm="rw"><defNumber name="RA">5</defNumber><defNumber name="DEC">20</defNumber></defNumberVector>'
        for i in range(0, len(definition), 7):
            client.ingest(definition[i:i+7].encode())
        for n in range(200):
            client.ingest(f'<setNumberVector device="OAT" name="EQUATORIAL_EOD_COORD" state="Busy"><oneNumber name="RA">{n/10}</oneNumber></setNumberVector>'.encode())
        prop = client.get("OAT", "EQUATORIAL_EOD_COORD")
        self.assertEqual(prop["values"]["DEC"], "20")
        self.assertEqual(prop["state"], "Busy")
        self.assertEqual(len(client.root), 0)

    def test_blob_cannot_enter_mount_cache(self):
        client = self.client()
        with self.assertRaises(IndiError):
            client.ingest(b'<setBLOBVector device="camera" name="CCD1"><oneBLOB name="CCD1">AAAA</oneBLOB></setBLOBVector>')
        self.assertEqual(client.properties, {})

    def test_no_goto_to_disconnected_device(self):
        client = self.client()
        client.ingest(b'<defSwitchVector device="OAT" name="CONNECTION"><defSwitch name="CONNECT">Off</defSwitch></defSwitchVector>')
        with self.assertRaises(IndiError):
            client.goto_eod("OAT", 5, 20)


class NightTests(unittest.TestCase):
    def test_only_red_channel_remains_and_original_is_preserved(self):
        original = [[0, 32768, 65535]] * 3
        red, green, blue = red_ramps(original)
        self.assertEqual(green, [0, 0, 0])
        self.assertEqual(blue, [0, 0, 0])
        self.assertGreater(red[2], red[1])
        self.assertEqual(original[0][-1], 65535)


class OpticsTests(unittest.TestCase):
    def test_zooms_and_ultrawide(self):
        self.assertGreater(field_width(22.3, 18), field_width(22.3, 45))
        self.assertGreater(field_width(22.3, 10), 90)
        self.assertAlmostEqual(field_width(22.3, 250), 5.1074, places=3)


class PolarTests(unittest.TestCase):
    def circle(self, axis_az, axis_alt):
        axis = horizon_vector(axis_az, axis_alt)
        east = (-math.sin(math.radians(axis_az)), math.cos(math.radians(axis_az)), 0)
        vertical = (axis[1]*east[2]-axis[2]*east[1], axis[2]*east[0]-axis[0]*east[2], axis[0]*east[1]-axis[1]*east[0])
        # Independent points from a known rotation axis and 40-degree cone.
        result = []
        for phase in (0, 30, 60):
            p = math.radians(phase)
            result.append(tuple(math.cos(math.radians(40))*axis[i] + math.sin(math.radians(40))*(math.cos(p)*east[i]+math.sin(p)*vertical[i]) for i in range(3)))
        return result

    def test_known_northern_axis_recovers_altitude_and_azimuth_error(self):
        result = estimate_from_vectors(self.circle(2, 22), 20)
        self.assertAlmostEqual(result["alt_adjustment_deg"], -2, places=7)
        self.assertAlmostEqual(result["az_adjustment_deg"], -2, places=7)

    def test_southern_hemisphere_chooses_upper_south_axis(self):
        result = estimate_from_vectors(self.circle(180, 35), -35)
        self.assertAlmostEqual(result["polar_error_arcmin"], 0, places=3)

    def test_duplicate_or_insufficient_points_rejected(self):
        with self.assertRaises(ValueError):
            estimate_from_vectors([horizon_vector(0, 20)]*3, 20)
        with self.assertRaises(ValueError):
            estimate_polar([], 20, -100)


if __name__ == "__main__":
    unittest.main()
