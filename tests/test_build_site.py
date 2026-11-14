"""Exercise the deploy command against real site files and release metadata."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildSiteTests(unittest.TestCase):
    def run_build(self, release, destination, source=ROOT, lastmod="2026-11-14"):
        release_path = destination.parent / "release.json"
        release_path.write_text(json.dumps(release), encoding="utf-8")
        command = [
            sys.executable,
            str(source / "scripts" / "build_site.py"),
            "--release-json",
            str(release_path),
            "--output",
            str(destination),
        ]
        if lastmod:
            command.extend(["--lastmod", lastmod])
        return subprocess.run(
            command,
            cwd=source,
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

    def test_rebuild_uses_content_dates_instead_of_the_build_clock(self):
        release = {
            "tag_name": "v9.8.7",
            "published_at": "2026-10-20T10:00:00Z",
            "assets": [
                {
                    "name": "test.zip",
                    "browser_download_url": (
                        "https://github.com/GrabLine/GrabLine/releases/download/v9.8.7/test.zip"
                    ),
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(
                    ".git", "_site", "__pycache__", ".ruff_cache"
                ),
            )

            def git(*args, day="2026-10-10"):
                environment = dict(os.environ)
                environment.update(
                    {
                        "GIT_AUTHOR_DATE": day + "T12:00:00+00:00",
                        "GIT_COMMITTER_DATE": day + "T12:00:00+00:00",
                    }
                )
                subprocess.run(
                    [
                        "git",
                        "-c",
                        "user.name=Site tests",
                        "-c",
                        "user.email=tests@example.invalid",
                        *args,
                    ],
                    cwd=source,
                    env=environment,
                    check=True,
                    capture_output=True,
                )

            git("init")
            git("add", ".")
            git("commit", "-m", "Initial content")
            # A maintenance-only commit must not make the page appear newer.
            with (source / "README.md").open("a", encoding="utf-8") as handle:
                handle.write("\nMaintenance documentation.\n")
            git("add", "README.md")
            git("commit", "-m", "Update docs", day="2026-10-30")
            for name in ("first", "repeat"):
                destination = base / name
                result = self.run_build(release, destination, source, lastmod=None)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(
                    "<lastmod>2026-10-20</lastmod>",
                    (destination / "sitemap.xml").read_text(encoding="utf-8"),
                )

            with (source / "index.html").open("a", encoding="utf-8") as handle:
                handle.write("\n<!-- Updated page content -->\n")
            git("add", "index.html")
            git("commit", "-m", "Update page", day="2026-10-25")
            destination = base / "content-update"
            result = self.run_build(release, destination, source, lastmod=None)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "<lastmod>2026-10-25</lastmod>",
                (destination / "sitemap.xml").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
