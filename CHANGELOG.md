# Changelog

## Unreleased

- Docs: new pages for the admin, the samples and demo, the management commands and
  troubleshooting; "how formatting works" in `docs/formatting.md`; where document data comes
  from in `docs/concepts.md`. `docs/index.md` lists every page in reading order.
- Demo: a documentation page at `/docs/` renders the repository's Markdown files.
- Removed `docs/SETUP.md`, an outdated copy of `SETUP.md`.

## 0.2.0 — 2026-11-10

**Pure-pip install and right-to-left support.**

- **PDF via Typst by default.** The `typst` wheel bundles the compiler, so PDF output needs no
  system libraries on any OS. The editor's HTML is converted to Typst (tables with header rows
  and merged cells, lists, quotes, colours, images, header/footer blocks, page X of Y). Document
  text only ever becomes Typst string literals.
- **WeasyPrint is now optional:** `pip install "django-templates-pro[weasyprint]"` and
  `TEMPLATES_PRO["PDF_ENGINE"] = "weasyprint"`.
- **Bundled fonts:** Noto Sans and Noto Sans Hebrew (SIL OFL 1.1). New settings
  `TYPST_FONT_PATHS` and `TYPST_IGNORE_SYSTEM_FONTS`.
- **Themes have a Typst style** next to their CSS; project themes add one with
  `THEMES[key]["typst"]` (`docs/rendering.md#themes`).
- **Text direction per template** (`DocumentTemplate.direction`: auto / ltr / rtl, migration
  `0002`). *Auto* is RTL for Hebrew, Arabic, Persian, Urdu… locales. It applies in the editor
  (live), HTML (`dir`), PDF, DOCX (bidi paragraphs, tables, section, complex-script runs) and
  previews. Each paragraph follows its first letter's direction.
- Widget options `direction`, `direction_field`, `locale_field`.
- HTML themes use `text-align: start` and have RTL rules.
- `typst` and `python-docx` are regular dependencies. The `[pdf]`, `[docx]` and `[all]` extras
  are kept but empty.
- **Starter content for pip installs:** the optional app `templates_pro.samples` registers four
  sample template types (`sample_invoice`, `sample_letter`, `sample_order`, `sample_certificate`),
  and `manage.py templates_pro_samples` loads six templates, seven blocks and ten constants
  (`--overwrite` resets them, `--remove` deletes them). Everything has a `sample-` slug; existing
  constants are never changed (`docs/quickstart.md`).
- Demo: Hebrew RTL invoice, Hebrew page footer, an Israeli customer (he_IL, ILS), and a Typst
  style for the project theme.
- Fixed: the demo read sample files with the system code page on Windows (now UTF-8).

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
