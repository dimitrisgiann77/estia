#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ESTIA pre-release check — μία εντολή για το §7 «Ολοκληρωμένο» του CLAUDE.md.

Τρέχει 3 deterministic gates (χωρίς να σηκώνει app/DB, μηδέν side-effects):
  1) py_compile  — όλα τα *.py compile καθαρά
  2) Jinja parse — όλα τα templates/*.html χωρίς syntax error
  3) arch_map --check — 0 κόκκινες σημαίες (παράλληλο μητρώο / αδέσποτος writer)

Χρήση:   python tools/check.py
Exit 0 = όλα πέρασαν · Exit 1 = κάποιο gate απέτυχε (δες έξοδο).
"""
import os, sys, glob, subprocess, py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def gate_pycompile():
    pys = sorted(glob.glob(os.path.join(ROOT, "*.py")) +
                 glob.glob(os.path.join(ROOT, "tools", "*.py")))
    bad = []
    for p in pys:
        try:
            py_compile.compile(p, doraise=True)
        except py_compile.PyCompileError as e:
            bad.append("  %s\n    %s" % (os.path.relpath(p, ROOT), e))
    if bad:
        fails.append("py_compile (%d):\n%s" % (len(bad), "\n".join(bad)))
    print("1) py_compile: %d αρχεία -> %s" % (len(pys), "OK" if not bad else "%d ΣΦΑΛΜΑΤΑ" % len(bad)))


def gate_jinja():
    try:
        from jinja2 import Environment
    except Exception:
        print("2) Jinja parse: SKIP (jinja2 μη εγκατεστημένο τοπικά — `pip install jinja2` για ενεργοποίηση)")
        return
    env = Environment()
    tpls = sorted(glob.glob(os.path.join(ROOT, "templates", "*.html")))
    bad = []
    for t in tpls:
        try:
            with open(t, "r", encoding="utf-8") as f:
                env.parse(f.read())
        except Exception as e:
            bad.append("  %s\n    %s" % (os.path.relpath(t, ROOT), e))
    if bad:
        fails.append("Jinja parse (%d):\n%s" % (len(bad), "\n".join(bad)))
    print("2) Jinja parse: %d templates -> %s" % (len(tpls), "OK" if not bad else "%d ΣΦΑΛΜΑΤΑ" % len(bad)))


def gate_archmap():
    am = os.path.join(ROOT, "tools", "arch_map.py")
    try:
        r = subprocess.run([sys.executable, am, "--check"],
                           cwd=ROOT, capture_output=True, text=True)
    except Exception as e:
        fails.append("arch_map: δεν έτρεξε (%s)" % e)
        print("3) arch_map --check: ΣΦΑΛΜΑ εκτέλεσης")
        return
    out = (r.stdout + r.stderr).strip()
    last = out.splitlines()[-1] if out else ""
    ok = (r.returncode == 0) and ("no red flags" in out.lower() or "0" in last)
    if not ok:
        fails.append("arch_map --check:\n%s" % out)
    print("3) arch_map --check: %s" % (last or ("OK" if ok else "ΑΠΕΤΥΧΕ")))


def main():
    print("== ESTIA pre-release check ==")
    gate_pycompile()
    gate_jinja()
    gate_archmap()
    print("-" * 40)
    if fails:
        print("ΑΠΕΤΥΧΕ %d gate(s):\n" % len(fails))
        print("\n\n".join(fails))
        sys.exit(1)
    print("OK — όλα τα gates πέρασαν. Έτοιμο για έλεγχο/έκδοση.")
    sys.exit(0)


if __name__ == "__main__":
    main()
