# CFA Referee Review — One-stop Referee Learning Platform

[中文文档](README.md) · This is the concise English overview.

A fully offline-capable static site that archives **all 81 issues of the Chinese Football
Association's official referee reviews (2024–2026 seasons, 612 cases with video)**,
re-organized by a unified teaching taxonomy, plus:

- **Per-team impact stats** (stats-2026/2025/2024.html) — every officially confirmed
  wrong call, score-correction analysis, both victim/beneficiary views.
- **Official unified-caliber briefings** (scale.html) — 104 typical scenarios across
  three seasons with official videos and decision matrices.
- **Laws of the Game 2026/27 in Simplified Chinese** (rules.html) — converted from the
  official IFAB traditional-Chinese PDF, with highlighting and per-chapter notes.
- **International referee-review library** — official sources translated into Chinese:
  UEFA Clear Line (83 cases), IFAB VAR protocol (full text + FAQ), Spain's RFEF
  Criterios Arbitrales, USA PRO weekly reviews (207 articles), CONMEBOL VAR cases,
  Croatia's HNS weekly analyses, plus a global directory of 23 official resources.
- **Quiz mode** (quiz.html) — 701 questions with spaced repetition
  (Leitner scheduler), wrong-answer book, and Anki TSV export.

## Key properties

- **Zero runtime dependencies**: every page is a self-contained HTML file — double-click
  `index.html` and it works offline. A lite text-only mode covers fully-online use.
- **Reproducible pipeline**: Python (stdlib only) scrapes → parses → classifies →
  builds. `python scripts/build_all.py` regenerates the whole site in seconds.
- **Data contracts**: `schemas/` holds JSON Schemas for the core datasets; integrity
  tests guard counts, cross-references, and translation-layer alignment.
- **Discoverable**: sitemap/robots/Atom feed; PWA service worker makes the hosted
  version readable offline.

## Links

- Live site: <https://rolandhuang17.github.io/cfa-referee-review/>
- Update feed: <https://rolandhuang17.github.io/cfa-referee-review/feed.xml>
- Data source: Chinese Football Association official website (裁判评议结果发布);
  Laws of the Game from The IFAB. See [NOTICE.md](NOTICE.md) for copyright notes.

## Get it

```bash
git clone https://github.com/RolandHuang17/cfa-referee-review.git
cd cfa-referee-review
python scripts/build_all.py          # restore full site (a few seconds)
# optional ~30GB of videos (resumable):
python scripts/download_videos_parallel.py 2026
```

Or grab the lite site bundle (a few MB, no videos) from
[Releases](https://github.com/RolandHuang17/cfa-referee-review/releases) —
unzip and double-click `index.html`.

Contributions welcome — translations ([guide](docs/translation-guide.md)),
data corrections, and accessibility improvements. See
[CONTRIBUTING.md](CONTRIBUTING.md).
