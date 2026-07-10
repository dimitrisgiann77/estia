# -*- coding: utf-8 -*-
"""
Data Hub — Χαρτογράφηση βάσης Pylon (READ-ONLY, διαγνωστικό) — module Οικονομικά
================================================================================
Αδελφός του map_tables.py, στοχευμένο στο **Pylon** (λογιστική/PMS/αποθήκη).
Τρέχει ΔΙΠΛΑ στο agent.py, χρησιμοποιεί το ΙΔΙΟ .env αλλά με κλειδί **PYLON_CONN**.
Διαβάζει ΜΟΝΟ system catalog (πίνακες/στήλες/όψεις) — ΚΑΜΙΑ αλλαγή, κανένα δεδομένο.

Βγάζει 3 CSV (utf-8-sig, ';') δίπλα στο script:
  pylon_tables_map.csv   → schema · table · rows · columns   (οι «μεγάλοι» πίνακες κινήσεων)
  pylon_columns_map.csv  → schema · table · pos · column · data_type · max_len · nullable
  pylon_views_map.csv    → schema · view                     (το Pylon εκθέτει πολλά ως views)

Χρήση (όπου βλέπει το Pylon SQL):  py map_pylon.py
→ Μοιράσου τα 3 CSV (ρίξ' τα στο D:\\ESTIA\\03_REFERENCE\\ΟΙΚΟΝΟΜΙΚΑ\\00_INBOX ή στείλ' τα).
"""
import os, sys, csv

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


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
    if os.environ.get('PYLON_CONN'):
        cfg['PYLON_CONN'] = os.environ['PYLON_CONN']
    return cfg


def _write_csv(name, header, rows):
    out = os.path.join(HERE, name)
    with open(out, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(header)
        w.writerows(rows)
    print('  ✓ %-24s (%d γραμμές)' % (name, len(rows)))
    return out


def main():
    cfg = load_env()
    conn_str = cfg.get('PYLON_CONN')
    if not conn_str:
        print('✗ Λείπει PYLON_CONN στο .env (δίπλα σε αυτό το script). Δες .env.example.')
        return 2
    try:
        import pyodbc
    except Exception as e:
        print('✗ Λείπει το pyodbc:', e, '→ pip install pyodbc')
        return 2

    print('== Pylon schema map == (read-only)')
    conn = pyodbc.connect(conn_str, timeout=30, readonly=True)
    cur = conn.cursor()

    # 1) Πίνακες + πλήθος γραμμών (από catalog — instant, ΟΧΙ COUNT(*))
    cur.execute("""
        SELECT s.name AS sch, t.name AS tbl,
               (SELECT COUNT(*) FROM sys.columns c WHERE c.object_id = t.object_id) AS ncols,
               SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END) AS nrows
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        LEFT JOIN sys.partitions p ON p.object_id = t.object_id
        GROUP BY s.name, t.name, t.object_id
        ORDER BY nrows DESC
    """)
    tables = [(r[0], r[1], int(r[3] or 0), int(r[2] or 0)) for r in cur.fetchall()]
    _write_csv('pylon_tables_map.csv', ['schema', 'table', 'rows', 'columns'],
               [(s, t, n, c) for (s, t, n, c) in tables])

    # 2) ΟΛΕΣ οι στήλες (catalog dump — το «χρυσό» για offline mapping)
    cur.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME,
               DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """)
    cols = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in cur.fetchall()]
    _write_csv('pylon_columns_map.csv',
               ['schema', 'table', 'pos', 'column', 'data_type', 'max_len', 'nullable'], cols)

    # 3) Views
    cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS ORDER BY TABLE_NAME")
    views = [(r[0], r[1]) for r in cur.fetchall()]
    _write_csv('pylon_views_map.csv', ['schema', 'view'], views)

    conn.close()
    print('\nΣύνολο: %d πίνακες · %d στήλες · %d views.' % (len(tables), len(cols), len(views)))
    print('→ Μοιράσου τα 3 CSV και συνεχίζουμε με στοχευμένα queries.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
