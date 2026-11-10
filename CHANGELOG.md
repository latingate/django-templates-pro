# Changelog

## 0.1.0 — 2026-11-10

First release.

- Template types with schemas (`Var`, `Group`, `ListOf`), autodiscovered from `doctemplate_types.py`.
- TipTap 3 editor widget: variables, constants, dynamic values, shared blocks, repeat sections,
  repeated table rows, conditions, per-chip formatting, `{{` picker, live preview.
  Presets `full` / `simple` / `minimal`; skins `default` / `dark` / `paper` / `compact`; custom toolbars.
- Compiler from editor HTML to sandboxed Jinja2 with an allowlist sanitiser.
- Babel formatting for dates, times, numbers, money, percent, text and booleans; locale and currency
  hooks per object.
- Renderers: HTML, PDF (WeasyPrint, running header/footer, page numbers), DOCX (python-docx), TXT.
- Themes: classic, modern, minimal, corporate, none; project themes via settings.
- Admin for templates, blocks ("used by"), constants and generated documents.
- `services.render / render_to_response / generate / preview_document`.
- Safe URL fetcher for PDF/DOCX images; system checks; `templates_pro_validate` command.
- Demo project with five templates, six blocks and sample data.
