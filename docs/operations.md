# Operations

## Validating templates after schema changes

When you rename or remove a variable in a template type's schema, templates
that use it become invalid. They still render, with the missing value empty,
but they no longer pass validation. Find them with:

```bash
python manage.py templates_pro_validate          # report problems
python manage.py templates_pro_validate --save   # also re-compile everything
```

Run it in CI or after deployments. Prefer *adding* schema fields to renaming
them. When you must rename, keep the old name for a release, or update the
stored HTML in a data migration (replace `data-path="old.path"` with
`data-path="new.path"`, then re-save to re-compile).

## Caching

- Compiled templates are cached in-process by source hash.
- Blocks and constants are cached per process and invalidated by a version
  token in `CACHE_ALIAS`. Saving or deleting a block or constant bumps the
  token through signals. With a shared cache (Redis, Memcached), all
  processes see edits immediately. With `LocMemCache` or `DummyCache` the
  token is recomputed from the database (a cheap aggregate), so it is still
  correct.
- Bulk updates (`QuerySet.update()`) skip signals. Call
  `templates_pro.services.bump_version("blocks")` (or `"constants"`)
  afterwards.

## Performance

- PDF layout is the expensive part (tens to hundreds of ms per page).
  Render in a task queue for batches.
- Keep `build_context` efficient (`select_related` / `prefetch_related`).
- Each include of a block costs one indexed query on a cold cache.

## Migrations policy

The package ships its own migrations. Released migrations are never edited,
only added. `GeneratedDocument.file` uses a callable storage, so changing
`STORAGE` needs no migration.

## Upgrading

1. Read `CHANGELOG.md`.
2. `pip install -U "django-templates-pro[...]==X.Y.Z"`
3. `python manage.py migrate`
4. `python manage.py collectstatic` (the editor bundle changes between versions)
5. `python manage.py templates_pro_validate`

Pin a compatible range in each project, e.g. `django-templates-pro>=0.1,<0.2`
while the version is below 1.0.

## Backups and portability

Templates, blocks and constants are ordinary rows. Move them between
environments with `dumpdata templates_pro.SiteConstant templates_pro.TemplateBlock
templates_pro.DocumentTemplate` and `loaddata`. Load blocks before templates.
Compiled sources are re-created on save, so re-save after loading if the
target runs a different package version.
