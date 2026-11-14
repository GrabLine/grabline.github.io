# GrabLine website

The website for [GrabLine](https://github.com/GrabLine/GrabLine), published at
https://grabline.github.io/. Desktop and browser-extension code stays in the
main GrabLine repository. This repository preserves the original `website/`
directory's history, filtered from development commit
`613aeb181890860b4ed58cd2c72c5cf82fa4476a` in a separate fresh clone.

## Build and check

Python 3.12 or later is sufficient; there are no Python package dependencies.

```sh
python -m unittest discover -s tests -v
gh api repos/GrabLine/GrabLine/releases/latest > release.json
python scripts/build_site.py --release-json release.json
python -m http.server --directory _site 8000
```

`release.json` is temporary build input; do not commit it. The builder generates
`_site/latest.json`, stamps the sitemap date and sets JSON-LD `softwareVersion`
from the release tag. A new app release needs no manual website version bump.

The Pages workflow runs after a main push, manual dispatch, `release-published`
repository dispatch and a weekly Monday fallback. GitHub can disable scheduled
workflows after 60 days without repository activity; release dispatch is the
primary automatic update path. Its fine-grained token belongs in the desktop
repository's `WEBSITE_DISPATCH_TOKEN` secret, never in this repository.

The desktop release workflow warns and continues if that optional token is
missing or dispatch fails. Deploy manually from Actions in that case. The
workflow first fetches the latest published desktop release, so dispatch payloads
cannot replace the download URLs.

## Old links

`/GrabLine/` redirects to `/`, preserving query strings and fragments. `404.html`
redirects `/GrabLine/<path>` to `/<path>` before showing an unrelated not-found
page. An old asset URL initially returns HTTP 404 with this HTML fallback;
JavaScript-capable browsers then navigate to the asset. This is browser
compatibility, not an HTTP 301 redirect for API/download clients.

## License and support

The site retains the parent project's AGPL-3.0-or-later license. See
[LICENSE](LICENSE). Report website bugs in the
[GrabLine issue tracker](https://github.com/GrabLine/GrabLine/issues) with the
`area:website` label; questions belong in
[Q&A](https://github.com/GrabLine/GrabLine/discussions/categories/q-a).
