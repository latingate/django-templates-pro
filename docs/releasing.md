# Releasing a new version

How to publish a new version of `django-templates-pro` to
[PyPI](https://pypi.org/project/django-templates-pro/). Commands are for macOS/Linux,
run from the repository root with the virtual environment active
(`source .venv/bin/activate`); Windows differences are noted.

## Checklist

1. [Pick the version number](#1-pick-the-version-number)
2. [Update the version and the changelog](#2-update-the-version-and-the-changelog)
3. [Rebuild the editor bundle](#3-rebuild-the-editor-bundle-only-if-frontend-changed) (only if `frontend/` changed)
4. [Run the checks](#4-run-the-checks)
5. [Commit, push and wait for CI](#5-commit-push-and-wait-for-ci)
6. [Build and inspect the package](#6-build-and-inspect-the-package)
7. [Smoke-test the wheel](#7-smoke-test-the-wheel)
8. [Tag the release](#8-tag-the-release)
9. [Upload to PyPI](#9-upload-to-pypi)
10. [Check the published release](#10-check-the-published-release)

## One-time setup

**Tools:**

```bash
pip install -e ".[dev]" build twine
```

**PyPI token.** Create a token at <https://pypi.org/manage/account/token/> with the
scope **Project: django-templates-pro** (not "Entire account": a project token can only
upload this package, so a leaked token cannot touch your other projects). The token is
shown only once. Save it in `~/.pypirc` (Windows: `%USERPROFILE%\.pypirc`) so `twine`
does not ask every time:

```ini
[pypi]
username = __token__
password = pypi-AgEI...your-token...
```

Keep the file private (`chmod 600 ~/.pypirc`) and never commit it. Without the file,
`twine upload` asks for the token and you paste it.

**GitHub push rights for workflows.** Pushing a change to `.github/workflows/` with
the `gh` login needs the `workflow` scope, once: `gh auth refresh -h github.com -s workflow`.

## 1. Pick the version number

The project follows [semantic versioning](https://semver.org/) in its 0.x form:

| Change | Example | Bump |
|---|---|---|
| bug fixes, docs, demo changes | 0.3.0 → 0.3.1 | patch |
| new features, or a change to the public API ([CLAUDE.md](../CLAUDE.md) lists it) | 0.3.1 → 0.4.0 | minor |
| the API is stable and promised | 0.x → 1.0.0 | major |

**PyPI never accepts the same version twice**, even after you delete a release. If
something is wrong after an upload, fix it and release the next patch version.

## 2. Update the version and the changelog

- `src/templates_pro/__init__.py`: `__version__ = "0.3.1"`. It is the only place
  the version is written; `pyproject.toml` reads it from there.
- `CHANGELOG.md`: rename `## Unreleased` to `## 0.3.1 — YYYY-MM-DD` (today's date) and
  check that every user-visible change is listed. Start a new empty `## Unreleased`
  section after the release if you like.

If the release adds a migration, check that it imports on Django 4.2
([development.md](development.md)).

## 3. Rebuild the editor bundle (only if `frontend/` changed)

The built editor is committed and shipped in the wheel; users never run Node.

```bash
cd frontend && npm run build && npm run contract && cd ..
```

Commit the changed files in `src/templates_pro/static/templates_pro/editor/` and
`tests/fixtures/`. CI fails if the committed bundle is out of date.

## 4. Run the checks

```bash
pytest
ruff check .
nox            # optional locally: every Python × Django combination (CI runs them too)
```

## 5. Commit, push and wait for CI

```bash
git add -A
git commit -m "Release 0.3.1"
git push origin master
gh run watch        # or open the Actions tab on GitHub
```

Wait until every CI job is green. CI tests Python 3.10–3.14 × Django 4.2–6.1 (minus
the combinations Django does not support), lints, and checks the editor bundle.

If `git push` is rejected because GitHub has commits you do not have (for example
pushed from another computer), run `git pull --rebase origin master`, run the tests
again, and push.

## 6. Build and inspect the package

```bash
rm -rf dist                 # Windows (PowerShell): Remove-Item -Recurse -Force dist
python -m build             # creates dist/*.whl and dist/*.tar.gz
twine check dist/*          # both must say PASSED
```

Look inside the wheel (Windows: open it as a zip file):

```bash
unzip -l dist/*.whl | grep -E "editor/|demo/project/manage.py|_docs/README.md"
unzip -l dist/*.whl | grep -E "sqlite3|__pycache__|\.pyc$"      # must print nothing
```

The wheel must contain the editor bundle (`static/templates_pro/editor/`), the demo
project (`templates_pro/demo/project/`) and its documentation (`.../project/_docs/`),
and no database or cache files. Everything in `example/` that is committed ships, so
delete leftovers (old images, scratch files) before building.

## 7. Smoke-test the wheel

Install it into a new, empty virtual environment and run the demo, exactly as a user
would:

```bash
python3 -m venv /tmp/release-test
/tmp/release-test/bin/pip install dist/*.whl
cd /tmp && /tmp/release-test/bin/templates-pro-demo
```

Windows: `py -m venv $env:TEMP\release-test`, then
`& $env:TEMP\release-test\Scripts\pip install (Get-Item dist\*.whl)` and
`& $env:TEMP\release-test\Scripts\templates-pro-demo`.

Open <http://127.0.0.1:8000>: the home page, a PDF and a DOCX link, and `/docs/`
should work. Stop it with Ctrl+C, go back to the repository, and delete the test
folders (`/tmp/release-test`, `/tmp/templates-pro-demo`).

## 8. Tag the release

Tag the exact commit you built from:

```bash
git tag v0.3.1
git push origin v0.3.1
```

If you commit again before uploading, rebuild (step 6) and move the tag:
`git tag -f v0.3.1 && git push -f origin v0.3.1`. Only move a tag before the version
is on PyPI.

Optional: create a GitHub release from the tag, with the changelog section as text:
`gh release create v0.3.1 --title 0.3.1 --notes "..." dist/*`.

## 9. Upload to PyPI

```bash
twine upload dist/*
```

`twine` uses the token from `~/.pypirc`, or asks for it. To rehearse first, use
[TestPyPI](https://test.pypi.org/) (a separate account and token):
`twine upload --repository testpypi dist/*`.

## 10. Check the published release

- <https://pypi.org/project/django-templates-pro/> shows the new version, and the page
  text (from `README.md`) looks right. Keep README links absolute (GitHub URLs):
  relative links do not work on PyPI.
- A clean install gets it (PyPI can take a minute to update):

  ```bash
  python3 -m venv /tmp/pypi-test
  /tmp/pypi-test/bin/pip install --no-cache-dir django-templates-pro==0.3.1
  ```

## If something went wrong

| Problem | What to do |
|---|---|
| `File already exists` on upload | that version is already on PyPI: bump the version and rebuild |
| `403 Forbidden` / invalid token | the token is wrong, expired or scoped to another project: create a new one |
| a broken release is on PyPI | release a fixed patch version; on the release page, **Options → Yank** the broken one (pip then skips it unless the exact version is pinned) |
| `refusing to allow an OAuth App to create or update workflow` on push | `gh auth refresh -h github.com -s workflow`, then push again |
| `You have divergent branches` on pull | `git pull --rebase origin master` |
| a CI job fails only on one Python/Django pair | check whether that Django version supports that Python; if not, exclude the pair in `.github/workflows/ci.yml` and `noxfile.py` |
