# Management commands

The package adds two `manage.py` commands. The demo project adds a third.

| Command | Comes with | Purpose |
|---|---|---|
| [`templates_pro_validate`](#templates_pro_validate) | the package | check (and re-compile) every template and block |
| [`templates_pro_samples`](#templates_pro_samples) | the package, with `templates_pro.samples` installed | load or remove the starter content |
| [`seed_demo`](#seed_demo) | the demo project (`example/`) | load the demo content and records |

Django's own `check` command also reports configuration problems; the IDs
are listed in [settings.md](settings.md#system-checks).

The demo website itself starts with `python -m templates_pro.demo` (no
`manage.py` needed, see [samples.md](samples.md#run-it)).

## templates_pro_validate

```bash
python manage.py templates_pro_validate          # report problems
python manage.py templates_pro_validate --save   # also re-save valid items
```

Runs the same validation as the admin's **Save** on every block and every
template, and prints one line per item:

```
✓ block “Company letterhead” (company-letterhead)
✗ document template “Invoice (standard)” (invoice-standard)
    body: unknown variable 'invoice.reference'
1 item(s) need attention.
```

Nothing is changed without `--save`. With `--save`, every valid item is saved
again, which re-compiles it. Invalid items are never saved.

Run it:

- after renaming or removing a field in a schema (templates that use the
  field are listed)
- after changing a `format=` default in a schema, with `--save`, because
  defaults are compiled into each template
  ([formatting.md](formatting.md#which-format-applies))
- after upgrading the package, with `--save`
- in CI, to catch a schema change that breaks stored templates

The command always exits with status 0. To fail a CI job, check its output
for `need attention`.

## templates_pro_samples

```bash
python manage.py templates_pro_samples               # create what is missing
python manage.py templates_pro_samples --overwrite   # reset sample blocks and templates
python manage.py templates_pro_samples --remove      # delete sample templates and blocks
```

Needs `"templates_pro.samples"` in `INSTALLED_APPS`; otherwise it stops with
a message saying so.

| | Constants | Sample blocks and templates |
|---|---|---|
| no option | created if the key is missing | created if missing, otherwise left alone |
| `--overwrite` | created if the key is missing | reset to the shipped version (your edits to them are lost) |
| `--remove` | kept | deleted, except blocks your own content still uses |

Only items with a `sample-` slug are ever changed or deleted. A sample
template becomes its type's default only when the type has no default yet.
See [samples.md](samples.md#packaged-samples) for what is loaded and how to
use it.

## seed_demo

Only in the demo project. `python example/run_demo.py` runs it for you the
first time (see [samples.md](samples.md#run-it)).

```bash
cd example
python manage.py seed_demo            # load or refresh the demo
python manage.py seed_demo --reset    # delete everything first
```

Without options it:

1. sets the demo's ten constants to their shipped values
2. creates or resets the demo's seven blocks and six templates
3. creates the demo customers, invoices, orders and employees, if there are
   no customers yet
4. creates the superuser `admin` / `admin`, if there is no user named `admin`

`--reset` first deletes **all** document templates, blocks and constants and
all demo records, including ones you added. Generated documents and users
are kept.

Never run it against a real database: it is written for the demo's SQLite
file and creates a superuser with a known password.
