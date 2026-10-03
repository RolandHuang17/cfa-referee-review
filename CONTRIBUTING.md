# Contributing

Issues and pull requests are welcome for data corrections, broken links,
accessibility improvements, documentation, and build reproducibility.

## Local setup

```bash
python -m pip install -r requirements-build.txt
python scripts/build_all.py
python tests/test_integrity.py
python scripts/serve.py
```

Open `http://127.0.0.1:8808/index.html` after starting the local server.

Generated HTML in `site/` should be rebuilt from scripts rather than edited by
hand. Do not commit videos, downloaded PDFs, credentials, or temporary logs —
machine-local material belongs in `data/local/`, which is ignored by git.
For data changes, include the source URL and explain the affected season and
case numbers.

Issues and pull requests use the templates under `.github/`; please fill in the
self-check list rather than deleting it. Participation is governed by
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Notable changes are recorded in
[CHANGELOG.md](CHANGELOG.md).
