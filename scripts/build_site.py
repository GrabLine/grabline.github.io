"""Build the public Pages artifact using the latest desktop release."""

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def build_site(release_path: Path, output: Path, lastmod: str) -> dict:
    release = json.loads(release_path.read_text(encoding="utf-8-sig"))
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError("The latest release must have a version tag")
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
    return latest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--lastmod", default=date.today().isoformat())
    arguments = parser.parse_args()
    result = build_site(arguments.release_json, arguments.output, arguments.lastmod)
    print(f"Built {result['tag_name']} with {len(result['assets'])} release assets")
