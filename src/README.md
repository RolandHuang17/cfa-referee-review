# Source layout

- `theme.css` — the single authoritative design system inlined into every
  generated page by `scripts/lib/theme.py`: design tokens (warm-paper light theme,
  warm-charcoal dark theme, `[data-theme]` switch), shared components
  (topbar/buttons/chips/badges/team badges/modals), and the serif display
  typeface stack for editorial headings.
- `learning-records.js` merges per-record edits for local notes, highlights and bookmarks. The page builders inline it for offline use.
- `study-calendar.js` supplies the local calendar date used by study history and streaks.
- The homepage template and its page-specific assets live in this directory; `scripts/build_portal.py` combines these with the case index and inlines them into `index.html`.
- The other page-specific layout CSS and templates live inside the builders in
  `scripts/` (build_page / build_stats / build_rules); they may
  only consume tokens and shared components from `theme.css`, never redefine
  them.

Colors, spacing, or component changes belong here in `theme.css`; layout
changes belong in the builders.
