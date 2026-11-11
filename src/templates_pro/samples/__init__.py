"""Optional starter content: sample template types, blocks, templates and constants.

Add ``"templates_pro.samples"`` to ``INSTALLED_APPS`` and run::

    python manage.py templates_pro_samples

The sample types (keys ``sample_*``) take plain dicts, so they need no models:
previews use the schema's sample values, and ``services.render(..., data={...})``
renders your own data. Remove the app from ``INSTALLED_APPS`` when you no
longer need it (run ``templates_pro_samples --remove`` first).
"""

from __future__ import annotations
