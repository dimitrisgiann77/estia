# -*- coding: utf-8 -*-
"""
Data Hub — Χαρτογράφηση πινάκων Epsilon (READ-ONLY, διαγνωστικό)
===============================================================
Τρέχει στον CND_SERVER, ΔΙΠΛΑ στο agent.py (χρησιμοποιεί το ΙΔΙΟ .env). Διαβάζει ΜΟΝΟ
τα ονόματα/μεγέθη ΟΛΩΝ των πινάκων της βάσης (system catalog) — ΚΑΜΙΑ αλλαγή, κανένα δεδομένο
εργαζομένων. Σκοπός: να δούμε «τι άλλο έχει να δώσει ο agent» πέρα από τους 2 πίνακες που τραβάμε.

Οι γραμμές μετρώνται από το system catalog (sys.partitions) — ακαριαίο, ΟΧΙ αργό COUNT(*).

Χρήση (στον server):  py map_tables.py
Βγάζει λίστα στην οθόνη + σώζει `epsilon_tables_map.csv` (μοιράσου το μαζί μου).
"""
import os, sys, csv

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# τα δύο που ήδη τραβάμε (για σήμανση στη λίστα)
OURS = {'EMPLOYEE', 'PERIODOI_DATA'}


def load_env():
    """Ίδιος parser με το agent.py (.env δίπλα στο script, utf-8-sig για BOM)."""
    cfg = {}
    path = os.path.join(HERE, '.env')
    if os.path.exists(path):
        with open(path, encoding='utf-8-sig') as fh:
            for ln in fh:
                ln = ln.strip().lstrip('﻿')
                if not ln or ln.startswith('#') or '=' not in ln:
                    continue
                k, v = ln.split('=', 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    if os.environ.get('EPSILON_CONN'):
        cfg['EPSILON_CONN'] = os.environ['EPSILON_CONN']
    return cfg


def main():
    cfg = load_env()
    if not cfg.get('EPSILON_CONN'):
        print('✗ Λείπει EPSILON_CONN στο .env (δίπλα σε αυτό το script).')
        return 2
    try:
        import pyodbc
    except Exception as e:
        print('✗ Λείπει το pyodbc:', e)
        return 2
    conn = pyodbc.connect(cfg['EPSILON_CONN'], timeout=30, readonly=True)
    cur = conn.cursor()
    # ΕΝΑ query: σχήμα · πίνακας · #στήλες · #γραμμές (από catalog, instant)
    cur.execute("""
        SELECT s.name AS sch, t.name AS tbl,
               (SELECT COUNT(*) FROM sys.columns c WHERE c.object_id = t.object_id) AS ncols,
               SUM(CASE WHEN p.index_id IN (0, 1) THEN p.rows ELSE 0 END) AS nrows
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        LEFT JOIN sys.partitions p ON p.object_id = t.object_id
        GROUP BY s.name, t.name, t.object_id
        ORDER BY nrows DESC
    """)
    data = [(r[0], r[1], int(r[3] or 0), int(r[2] or 0)) for r in cur.fetchall()]

    print('\n%-42s %13s %8s' % ('ΠΙΝΑΚΑΣ', 'ΓΡΑΜΜΕΣ', 'ΣΤΗΛΕΣ'))
    print('-' * 70)
    for sch, tbl, nrows, ncols in data:
        name = tbl if sch == 'dbo' else '%s.%s' % (sch, tbl)
        mark = '  <= ΤΡΑΒΑΜΕ' if tbl in OURS else ''
        print('%-42s %13s %8d%s' % (name[:42], '{:,}'.format(nrows), ncols, mark))
    print('-' * 70)
    print('Σύνολο πινάκων: %d' % len(data))

    out = os.path.join(HERE, 'epsilon_tables_map.csv')
    with open(out, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['schema', 'table', 'rows', 'columns', 'pulled_now'])
        for sch, tbl, nrows, ncols in data:
            w.writerow([sch, tbl, nrows, ncols, 'yes' if tbl in OURS else ''])
    print('\n✓ Αποθηκεύτηκε: %s' % out)
    print('  → Στείλε μου αυτό το αρχείο για να δούμε μαζί τι αξίζει.')
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
