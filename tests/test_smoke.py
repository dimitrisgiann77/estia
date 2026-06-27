# -*- coding: utf-8 -*-
"""Smoke-tests ESTIA — επιβεβαιώνουν ότι τα κρίσιμα routes σηκώνονται χωρίς
server error (500). Δεν ελέγχουν λεπτομερή λογική — μόνο «δουλεύει/δεν σπάει»."""
import pytest

# Κρίσιμα authenticated routes (ένα ανά module-κλειδί) — επιβεβαιωμένα ότι υπάρχουν
AUTHED_ROUTES = [
    "/app",                              # core / shell
    "/dashboard/faults",                 # Βλαβοληψία
    "/dashboard/measurements",           # Μετρήσεις
    "/dashboard/measurements/console",   # Κονσόλα Μετρήσεων
    "/dashboard/evaluations",            # Αξιολόγηση
    "/dashboard/payroll",                # Μισθοδοσία
    "/dashboard/org",                    # Οργανόγραμμα
    "/dashboard/hotels",                 # Ξενοδοχεία/Πισίνες
    "/dashboard/imports",                # Κέντρο Εισαγωγής
    "/dashboard/help",                   # Ενημέρωση/Help
]


def test_login_page_loads(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_login_succeeds(client):
    r = client.post("/login", data={"username": "admin", "password": "test1234"})
    assert r.status_code in (302, 303)


def test_bad_password_does_not_log_in(client):
    client.post("/login", data={"username": "admin", "password": "LATHOS"})
    r = client.get("/app")  # ανώνυμος → δεν πρέπει να βλέπει το dashboard
    assert r.status_code in (302, 303) or b"/login" in r.data


@pytest.mark.parametrize("path", AUTHED_ROUTES)
def test_authed_route_no_server_error(auth_client, path):
    r = auth_client.get(path)
    assert r.status_code in (200, 302, 303), f"{path} -> {r.status_code} (πιθανό σπάσιμο)"
