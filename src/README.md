# Source layout

- `theme.css` — the single authoritative design system inlined into every
  generated page by `scripts/theme.py`: design tokens (warm-paper light theme,
  warm-charcoal dark theme, `[data-theme]` switch), shared components
  (topbar/buttons/chips/badges/team badges/modals), and the serif display
  typeface stack for editorial headings.
- Page-specific layout CSS and templates live inside the builders in
  `scripts/` (build_portal / build_page / build_stats / build_rules); they may
  only consume tokens and shared components from `theme.css`, never redefine
  them.

Colors, spacing, or component changes belong here in `theme.css`; layout
changes belong in the builders.
