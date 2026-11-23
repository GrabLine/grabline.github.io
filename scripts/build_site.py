"""Build the public Pages artifact using the latest desktop release (and, if given, the latest Android release)."""

import argparse
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

ANDROID_DOWNLOADS = "/GrabLine/grabline-android/releases/download/"


def content_lastmod(release: dict) -> str:
    """Use source/release content dates, so scheduled rebuilds stay stable."""
    source_date = subprocess.check_output(
        [
            "git",
            "log",
            "-1",
            "--format=%cs",
            "--",
            "index.html",
            "assets",
            "404.html",
            "GrabLine",
            "robots.txt",
            "sitemap.xml",
            "scripts/build_site.py",
            ".github/workflows/pages.yml",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    dates = [date.fromisoformat(source_date)]
    if release.get("published_at"):
        dates.append(date.fromisoformat(release["published_at"][:10]))
    return max(dates).isoformat()


def android_latest(release: dict) -> dict:
    """The Android APKs of a release, for the page's direct download buttons."""
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError("The latest Android release must have a version tag")
    apks = []
    for asset in release.get("assets", []):
        name = asset.get("name")
        if not isinstance(name, str) or not name.lower().endswith(".apk"):
            continue  # SHA256SUMS.txt and the like stay on the release page
        url = asset.get("browser_download_url", "")
        parsed = urlsplit(url)
        size = asset.get("size")
        if (
            parsed.scheme != "https"
            or parsed.netloc != "github.com"
            or not parsed.path.startswith(ANDROID_DOWNLOADS)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size <= 0
        ):
            raise ValueError("Android release contains an invalid APK entry")
        apks.append({"name": name, "size": size, "browser_download_url": url})
    if not apks:
        raise ValueError("The latest Android release has no APK")
    return {"tag_name": tag, "assets": apks}


def build_site(
    release_path: Path,
    output: Path,
    lastmod: str | None,
    android_release_path: Path | None = None,
) -> dict:
    release = json.loads(release_path.read_text(encoding="utf-8-sig"))
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError("The latest release must have a version tag")
    lastmod = lastmod or content_lastmod(release)
    date.fromisoformat(lastmod)
    assets = []
    for asset in release.get("assets", []):
        name = asset.get("name")
        url = asset.get("browser_download_url", "")
        parsed = urlsplit(url)
        if (
            not isinstance(name, str)
            or not name
            or parsed.scheme != "https"
            or parsed.netloc != "github.com"
            or not parsed.path.startswith("/GrabLine/GrabLine/releases/download/")
        ):
            raise ValueError("Release contains an invalid asset name or download URL")
        assets.append({"name": name, "browser_download_url": url})
    if not assets:
        raise ValueError("The latest release has no downloadable assets")
    if output.resolve() == ROOT:
        raise ValueError("The output must be separate from the source checkout")

    android = None
    if android_release_path is not None:
        android = android_latest(
            json.loads(android_release_path.read_text(encoding="utf-8-sig"))
        )

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html, count = re.subn(
        r'("softwareVersion"\s*:\s*")[^"]*(")',
        lambda match: match[1] + tag[1:] + match[2],
        html,
    )
    if count != 1:
        raise ValueError("Expected one softwareVersion in the site JSON-LD")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    sitemap = re.sub(
        r"<lastmod>[^<]*</lastmod>", f"<lastmod>{lastmod}</lastmod>", sitemap
    )

    output.mkdir(parents=True, exist_ok=True)
    for filename in ("404.html", "robots.txt", "favicon.ico"):
        shutil.copy2(ROOT / filename, output / filename)
    for directory in ("assets", "GrabLine"):
        shutil.copytree(ROOT / directory, output / directory, dirs_exist_ok=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    latest = {"tag_name": tag, "assets": assets}
    (output / "latest.json").write_text(
        json.dumps(latest, indent=2) + "\n", encoding="utf-8"
    )
    if android is not None:
        (output / "android-latest.json").write_text(
            json.dumps(android, indent=2) + "\n", encoding="utf-8"
        )
    return latest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--lastmod", help="Override the source/release content date")
    parser.add_argument("--android-release-json", type=Path, help="Latest grabline-android release")
    arguments = parser.parse_args()
    result = build_site(
        arguments.release_json,
        arguments.output,
        arguments.lastmod,
        arguments.android_release_json,
    )
    print(f"Built {result['tag_name']} with {len(result['assets'])} release assets")
