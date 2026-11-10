"""Test matrix: nox (all), nox -s tests-3.12, nox -s lint."""

import nox

nox.options.reuse_existing_virtualenvs = True

DJANGO = {"4.2": "Django>=4.2,<5.0", "5.1": "Django>=5.1,<5.2", "5.2": "Django>=5.2,<6.0"}


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
@nox.parametrize("django", list(DJANGO))
def tests(session, django):
    session.install(DJANGO[django])
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(python="3.12")
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")
