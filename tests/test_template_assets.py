import io
from pathlib import Path
import subprocess
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "data" / "petpet"
REQUIRED_FRAMES = {f"data/petpet/frame{index}.png" for index in range(5)}


class TemplateAssetTests(unittest.TestCase):
    def check_ignore(self, paths):
        # Tracked files normally bypass ignore checks, hiding broken asset rules.
        return subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin", "-z"],
            cwd=ROOT,
            input=("\0".join(paths) + "\0").encode("utf-8"),
            capture_output=True,
        )

    def test_required_frames_are_present_and_tracked(self):
        tracked = subprocess.check_output(
            ["git", "ls-files", "--", "data/petpet/frame*.png"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        self.assertTrue(REQUIRED_FRAMES.issubset(tracked))
        for name in sorted(REQUIRED_FRAMES):
            with self.subTest(frame=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertTrue((ROOT / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_existing_and_future_frames_are_not_ignored(self):
        frames = REQUIRED_FRAMES | {"data/petpet/frame5.png", "data/petpet/frame20.png"}
        frames.update(path.relative_to(ROOT).as_posix() for path in TEMPLATE_DIR.glob("frame*.png"))
        result = self.check_ignore(sorted(frames))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_runtime_data_and_generated_assets_remain_ignored(self):
        paths = [
            "data/runtime.json",
            "data/plugins/example/config.json",
            "data/petpet.zip",
            "data/petpet/demo.gif",
            "data/petpet/frame0.gif",
            "data/petpet/preview.png",
            "data/petpet/cache/frame0.png",
            "nested/data/runtime.json",
        ]
        result = self.check_ignore(paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, ("\0".join(paths) + "\0").encode("utf-8"))

    def test_source_archive_contains_all_template_frames(self):
        archive_bytes = subprocess.check_output(
            ["git", "archive", "--format=zip", "HEAD"],
            cwd=ROOT,
        )
        frames = REQUIRED_FRAMES | {
            path.relative_to(ROOT).as_posix() for path in TEMPLATE_DIR.glob("frame*.png")
        }
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            for name in sorted(frames):
                with self.subTest(frame=name):
                    self.assertIn(name, archive.namelist())
                    self.assertEqual(archive.read(name), (ROOT / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
