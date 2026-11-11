# Security

Templates are written by people you may not fully trust: staff, customers,
tenants. The package assumes template authors are untrusted and defends in
layers.

## 1. No template syntax from users

The editor stores HTML. The compiler (`core/compiler.py`) is the only place
that produces Jinja source, and it does so as follows:

- Text is entity-encoded, including `{` and `}`, so text a user types such as
  `{{ 7*7 }}` or `{% … %}` is printed literally, never executed.
- Variable paths, constant keys, aliases and block slugs must match strict
  identifier/slug patterns.
- Format specs and condition values become `\u`-escaped string literals,
  parsed as JSON at render time. They cannot close a Jinja expression.
- Variables compile to dict subscripts (`invoice["number"]`), never attribute access.

## 2. A locked-down sandbox

Compiled templates run in `SafeEnvironment`, a Jinja2
`ImmutableSandboxedEnvironment` subclass:

- Attribute access is allowed **only** on loop helpers and date/time values.
  Every `__class__` / `__globals__` / `.items()` style escape is blocked.
- Mutating built-ins (`list.append`, `dict.update`) is blocked.
- Autoescaping is on, so values containing `<script>` are printed as text.
- Loops are capped at 10,000 items, output at `MAX_OUTPUT_CHARS`, and
  template execution at `RENDER_TIMEOUT` seconds.

## 3. Plain-data contexts

`build_context()` must return plain data. `ensure_plain()` rejects model
instances, QuerySets, callables and other objects with a clear error. Even a
sandbox bypass could therefore only see what you deliberately passed in.

**Only pass what templates should see.** Every key in the context is
reachable by anyone who can edit templates of that type. Don't include
password hashes, tokens or other customers' data.

## 4. HTML sanitising

The compiler is also an allowlist sanitiser. It drops `script`, `style`,
`iframe` and friends together with their content, keeps only known tags and
attributes, filters inline styles to safe properties (no `url()`,
`expression`, `@import`), restricts links to `http(s)`, `mailto`, `tel`, `#`
and relative URLs, allows images only from `http(s)`, relative paths and
raster `data:` URIs, and adds `rel="noopener noreferrer"` to `target=_blank`
links. Stored bodies are sanitised on save.

## 5. Typst PDF generation

The default PDF engine turns the sanitised HTML into Typst source, which is
itself a programming language, so the same rule as for Jinja applies:

- **Document text only ever becomes Typst string literals** (`#"..."`, with
  `\` and `"` escaped). Text a user types, such as `#read("/etc/passwd")`,
  `]#panic()[` or `$x$`, is printed literally.
- Values emitted as code (colours, sizes, column widths, spans, page setup)
  are produced by the converter after strict validation. Anything else is
  dropped.
- Each PDF compiles in a fresh temporary folder that holds only the generated
  file and its images. Typst cannot read outside that root and has no network
  access.
- Theme Typst styles come from your settings (developer-written), never from
  template authors.

## URL fetching

PDF and DOCX rendering fetch images (and, with the WeasyPrint engine, CSS
`url()` in themes or extra CSS).
To prevent SSRF and local file disclosure, the default fetcher
(`templates_pro.fetchers.safe_url_fetcher`) only allows:

- `data:` URIs
- files under `STATIC_URL` (via staticfiles finders / `STATIC_ROOT`)
- files under `MEDIA_URL` (via the default storage, which works with S3-style storages)
- remote URLs that start with an entry in `ALLOWED_URL_PREFIXES`

`file://`, internal hosts and `..` paths are refused. Refused resources are
skipped, and the document still renders.

Replace the policy with `URL_FETCHER = "myapp.fetch.my_fetcher"`; it receives
a URL and returns `{"string": bytes, "mime_type": str}`.

## Permissions

- The admin uses the standard model permissions. Give template editors
  `change_documenttemplate` and `change_templateblock`, and keep `extra_css`
  in mind: CSS can't run code, but it can restyle or hide content.
- Preview endpoints require login and `PREVIEW_PERMISSION` (default
  `templates_pro.change_documenttemplate`).
- Your own pages that save user-written templates should call
  `full_clean()`, or `compile_html()` and check `.errors`.

## Reporting

Please report vulnerabilities privately to the maintainer rather than in a
public issue.
