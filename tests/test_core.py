from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from astroall.camera import CanonSD, CameraError, require_raw_jpeg, shutter_seconds
from astroall.solve import Position, drift_report, separation_arcsec, solve_jpeg
from astroall.storage import JpegCache


class Widget:
    def __init__(self, value, choices=()):
        self.value, self.choices = value, choices

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_choices(self):
        return self.choices


class Config:
    def __init__(self, values):
        self.values = values

    def get_child_by_name(self, name):
        return self.values[name]


class FakeFile:
    def __init__(self, content=b"\xff\xd8test\xff\xd9"):
        self.content = content

    def save(self, path):
        Path(path).write_bytes(self.content)


class FakeCamera:
    def __init__(self):
        self.config = Config({"capturetarget": Widget("Internal RAM", ["Internal RAM", "Memory card"]),
                              "imageformat": Widget("RAW + Medium Fine JPEG"),
                              "shutterspeed": Widget("30"), "autoexposuremode": Widget("Manual")})
        self.downloads = []
        self.captures = 0
        self.names = ["IMG_0001.CR3", "IMG_0001.JPG", "IMG_0002.JPG"]
        self.size = len(FakeFile().content)

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def get_abilities(self):
        return SimpleNamespace(model="Canon EOS R50")

    def capture(self, mode):
        self.captures += 1
        return SimpleNamespace(folder="/store_00010001/DCIM/100CANON", name="IMG_0001.CR3")

    def folder_list_files(self, folder):
        return [(name, "") for name in self.names]

    def file_get_info(self, folder, name):
        return SimpleNamespace(file=SimpleNamespace(size=self.size))

    def file_get(self, folder, name, kind):
        self.downloads.append(name)
        return FakeFile()

    def wait_for_event(self, timeout):
        return None, None


GP = SimpleNamespace(GP_CAPTURE_IMAGE=0, GP_FILE_TYPE_NORMAL=1)


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = JpegCache(self.temp.name)
        self.camera = FakeCamera()
        self.adapter = CanonSD(self.camera, GP)

    def test_raw_stays_on_card_only_exact_jpeg_downloaded(self):
        result = self.adapter.capture_jpeg(self.cache)
        self.assertEqual(self.camera.downloads, ["IMG_0001.JPG"])
        self.assertEqual(result["sd_raw"], "IMG_0001.CR3")
        self.assertEqual(self.camera.config.values["capturetarget"].value, "Memory card")
        self.assertTrue(Path(result["jpeg"]).is_file())

    def test_unknown_card_choice_does_not_trigger(self):
        self.camera.config.values["capturetarget"].choices = ["Internal RAM", "1"]
        with self.assertRaises(CameraError):
            self.adapter.capture_jpeg(self.cache)
        self.assertEqual(self.camera.captures, 0)

    def test_spanish_card_label_is_verified_without_numeric_assumptions(self):
        self.camera.config.values['capturetarget'].choices=['RAM interna','Tarjeta de memoria']
        self.adapter.capture_jpeg(self.cache)
        self.assertEqual(self.camera.config.values['capturetarget'].value,'Tarjeta de memoria')
        self.assertEqual(self.camera.downloads,['IMG_0001.JPG'])

    def test_oversized_jpeg_is_not_downloaded(self):
        self.camera.size = 17 * 1024 * 1024
        with self.assertRaises(ValueError):
            self.adapter.capture_jpeg(self.cache)
        self.assertEqual(self.camera.downloads, [])

    def test_missing_pair_fails_after_one_trigger_without_retry(self):
        self.camera.names = ["IMG_0001.CR3", "IMG_0002.JPG"]
        with self.assertRaises(CameraError):
            self.adapter.capture_jpeg(self.cache, timeout=0)
        self.assertEqual(self.camera.downloads, [])
        self.assertEqual(self.camera.captures, 1)

    def test_jpeg_only_mode_does_not_trigger(self):
        self.camera.config.values["imageformat"].value = "Medium Fine JPEG"
        with self.assertRaises(CameraError):
            self.adapter.capture_jpeg(self.cache)
        self.assertEqual(self.camera.captures, 0)

    def test_bulb_not_claimed_as_supported(self):
        with self.assertRaises(CameraError):
            shutter_seconds("Bulb")
        self.assertEqual(shutter_seconds("1/4"), .25)
        require_raw_jpeg("cRAW + Medium JPEG")
        require_raw_jpeg("RAW + M")
        require_raw_jpeg("cRAW + cM")
        with self.assertRaises(CameraError):
            require_raw_jpeg("RAW + 0xFF")


class StorageTests(unittest.TestCase):
    def test_cache_remains_bounded_and_does_not_touch_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = JpegCache(temp, budget=16, max_file=8)
            raw = Path(temp) / "do-not-touch.CR3"
            raw.write_bytes(b"RAW")
            for _ in range(6):
                cache.save(FakeFile(), 8)
            self.assertLessEqual(sum(p.stat().st_size for p in Path(temp).glob("*.jpg")), 16)
            self.assertEqual(raw.read_bytes(), b"RAW")

    def test_truncated_file_leaves_no_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = JpegCache(temp)
            with self.assertRaises(OSError):
                cache.save(FakeFile(), 12)
            self.assertEqual(list(Path(temp).iterdir()), [])


class DriftTests(unittest.TestCase):
    def test_ra_wrap_around_and_no_motor_command(self):
        result = drift_report(Position(359.99, 0), Position(.01, 0))
        self.assertAlmostEqual(result["error_arcsec"], 72, places=2)
        self.assertTrue(result["recenter_suggested"])
        self.assertFalse(result["mount_command_sent"])

    def test_pole_and_identity(self):
        self.assertLess(separation_arcsec(Position(0, 90), Position(180, 90)), .001)
        self.assertEqual(separation_arcsec(Position(20, -30), Position(20, -30)), 0)

    def test_invalid_coordinates_fail(self):
        for ra, dec in [(360, 0), (0, 91), (float("nan"), 0)]:
            with self.assertRaises(ValueError):
                Position(ra, dec)


class SolverTests(unittest.TestCase):
    def test_failed_solver_never_returns_position(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp)/"test.jpg"
            image.write_bytes(b"\xff\xd8")
            (Path(temp)/"index-4110.fits").touch()
            with patch("astroall.solve.shutil.which", return_value="solve-field"), \
                 patch("astroall.solve.subprocess.run", return_value=SimpleNamespace(returncode=1)):
                with self.assertRaises(RuntimeError):
                    solve_jpeg(image, 5, [temp], work_root=Path(temp)/"work")

    def test_solver_requires_success_marker_and_parses_degree_units(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp)/"test.jpg"
            image.write_bytes(b"\xff\xd8")
            (Path(temp)/"index-4110.fits").touch()
            def fake_run(cmd, **kwargs):
                Path(cmd[cmd.index("--solved")+1]).write_bytes(b"\x01")
                kwargs["stdout"].write("Field center: (RA,Dec) = (359.99, -22.5) deg.\n")
                self.assertFalse(kwargs.get("shell", False))
                self.assertEqual(kwargs["timeout"], 90)
                return SimpleNamespace(returncode=0)
            with patch("astroall.solve.shutil.which", return_value="solve-field"), \
                 patch("astroall.solve.subprocess.run", side_effect=fake_run):
                position = solve_jpeg(image, 5, [temp], work_root=Path(temp)/"work")
            self.assertEqual(position, Position(359.99, -22.5))
            self.assertEqual(list((Path(temp)/"work").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
