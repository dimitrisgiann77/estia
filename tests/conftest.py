# -*- coding: utf-8 -*-
"""Pytest setup για τα smoke-tests της ESTIA.
Στήνει ασφαλείς ρυθμίσεις (test DB, χωρίς scheduler) ΠΡΙΝ φορτωθεί η app,
και φτιάχνει UTF-8 stdout (ώστε τα ελληνικά/`→` logs να μη σκάνε σε Windows)."""
import os
import sys

# UTF-8 stdout ΠΡΙΝ το import της app (το module Μετρήσεις τυπώνει `→` στο load)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("BACKUP_ENABLED", "false")
os.environ.setdefault("BOOTSTRAP_ADMIN_USER", "admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "test1234")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_smoke.db")

import pytest
import app as estia  # single import (όπως gunicorn/Railway — ΟΧΙ python app.py)


@pytest.fixture()
def client():
    estia.app.config["TESTING"] = True
    return estia.app.test_client()


@pytest.fixture()
def auth_client(client):
    """Test client ήδη συνδεδεμένος ως admin."""
    r = client.post("/login", data={"username": "admin", "password": "test1234"})
    assert r.status_code in (302, 303), f"login POST returned {r.status_code} (περίμενα redirect)"
    return client
