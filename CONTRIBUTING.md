# Contributing

Issues and pull requests are welcome for data corrections, broken links,
accessibility improvements, documentation, and build reproducibility.

## Local setup

```bash
python -m pip install -r scripts/requirements-build.txt
python scripts/build_all.py
python scripts/verify_project.py
python scripts/serve.py
```

Open `http://127.0.0.1:8808/index.html` after starting the local server.

Generated HTML in `site/` should be rebuilt from scripts rather than edited by
hand. Do not commit videos, downloaded PDFs, credentials, or temporary logs.
For data changes, include the source URL and explain the affected season and
case numbers.
