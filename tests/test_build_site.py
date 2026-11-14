"""Exercise the deploy command against real site files and release metadata."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildSiteTests(unittest.TestCase):
    def run_build(self, release, destination):
        release_path = destination.parent / "release.json"
        release_path.write_text(json.dumps(release), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_site.py"),
                "--release-json",
                str(release_path),
                "--output",
                str(destination),
                "--lastmod",
                "2026-11-14",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_release_metadata_drives_the_published_site(self):
        assets = [
            {
                "name": "Grabline-Setup-9.8.7.exe",
                "browser_download_url": (
                    "https://github.com/GrabLine/GrabLine/releases/download/"
                    "v9.8.7/Grabline-Setup-9.8.7.exe"
                ),
                "unneeded_api_field": "excluded",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "site"
            result = self.run_build(
                {"tag_name": "v9.8.7", "assets": assets}, destination
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (destination / "index.html").read_text(encoding="utf-8")
            schema = re.search(
                r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
            )
            self.assertIsNotNone(schema)
            self.assertEqual(json.loads(schema.group(1))["softwareVersion"], "9.8.7")
            self.assertIn('href="https://grabline.github.io/"', html)
            self.assertNotIn("grabline.github.io/GrabLine/", html)
            latest = json.loads(
                (destination / "latest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                latest,
                {
                    "tag_name": "v9.8.7",
                    "assets": [
                        {
                            key: value
                            for key, value in assets[0].items()
                            if key != "unneeded_api_field"
                        }
                    ],
                },
            )
            sitemap = (destination / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("<lastmod>2026-11-14</lastmod>", sitemap)
            self.assertIn("<loc>https://grabline.github.io/</loc>", sitemap)
            self.assertTrue((destination / "assets" / "og.png").is_file())
            self.assertTrue((destination / "GrabLine" / "index.html").is_file())
            self.assertFalse((destination / ".git").exists())
            self.assertFalse((destination / "scripts").exists())

    def test_invalid_release_cannot_publish_a_site(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "site"
            result = self.run_build(
                {"tag_name": "not-a-version", "assets": []}, destination
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
