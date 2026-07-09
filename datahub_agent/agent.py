# -*- coding: utf-8 -*-
"""
Data Hub — On-prem Agent (Epsilon Business Μισθοδοσία → Εστία)
==============================================================
Φ3. Τρέχει στον CND_SERVER (μέσα στο LAN, δίπλα στην Epsilon SQL). READ-ONLY στην Epsilon
(db_datareader)· conform· PUSH outbound HTTPS στο `/api/datahub/ingest` (bearer token).
ΚΑΜΙΑ εγγραφή/DDL στην Epsilon. Spec: 02_MODULES_ESTIA/ΚΕΝΤΡΟ_ΔΕΔΟΜΕΝΩΝ/AGENT_DESIGN.md.

ΟΛΑ ΤΑ ΠΕΔΙΑ: ανακαλύπτει τις στήλες από INFORMATION_SCHEMA και τραβάει ΟΛΕΣ
(εκτός binary: image) — PERIODOI_DATA (643) + EMPLOYEE (681). Το bronze staging τα κρατά
στο `raw_json` (+ typed columns για τα γνωστά). Τίποτα δεν χάνεται.

Δύο ροές:
  Tier A (ταυτότητες) = ΠΛΗΡΕΣ snapshot EMPLOYEE — συχνά (πιάνει προσλήψεις/αποχωρήσεις/τηλέφωνα).
  Tier B (ποσά)       = PERIODOI_DATA join — SEED (όλα) ή LIVE (incremental watermark PER_CALCULATED_DATE).

Χρήση:
  python agent.py --seed            # εφάπαξ: ΟΛΑ τα έτη + όλο το μητρώο (Tier B + Tier A)
  python agent.py --live            # incremental (Tier B watermark) + Tier A snapshot
  python agent.py --tier A          # μόνο ταυτότητες
  python agent.py --dry             # δείξε τι θα σταλεί (χωρίς POST)
Config: `.env` δίπλα στο script (βλ. .env.example).
"""
import os, sys, json, argparse, datetime, decimal, urllib.request, ssl

HERE = os.path.dirname(os.path.abspath(__file__))

# ── UTF-8 console (Windows cp1253) ────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


# ── Config (.env δίπλα στο script· απλός parser, χωρίς εξάρτηση) ───────────────
def load_env():
    cfg = {}
    path = os.path.join(HERE, '.env')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln or ln.startswith('#') or '=' not in ln:
                    continue
                k, v = ln.split('=', 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    # env vars override .env
    for k in ('EPSILON_CONN', 'ESTIA_URL', 'ESTIA_TOKEN', 'DB_INSTANCE', 'BATCH'):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


# ── Epsilon read (pyodbc, read-only) ──────────────────────────────────────────
IMAGE_TYPES = {'image'}          # binary — ΔΕΝ τα τραβάμε (φωτο/CV/attachments)
# προαιρετικά βαριά/άχρηστα προς παράλειψη (κρατάμε τα υπόλοιπα ΟΛΑ):
SKIP_COLS = {
    'EMPLOYEE': {'PHOTO', 'PHOTO_EXT', 'CV', 'CV_NAME'},
    'PERIODOI_DATA': set(),
}

def _connect(cfg):
    import pyodbc  # μόνο on-prem (CND_SERVER)
    conn = pyodbc.connect(cfg['EPSILON_CONN'], timeout=30, readonly=True)
    return conn

def discover_columns(cur, table):
    """Στήλες του πίνακα από INFORMATION_SCHEMA, εξαιρώντας image/skip. Verbatim ονόματα."""
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", table)
    cols = []
    for name, dtype in cur.fetchall():
        if dtype in IMAGE_TYPES:
            continue
        if name in SKIP_COLS.get(table, set()):
            continue
        cols.append(name)
    return cols


# ── Conform (Epsilon τιμές → JSON-safe) ───────────────────────────────────────
def _val(v):
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat(sep=' ') if isinstance(v, datetime.datetime) else v.isoformat()
    if isinstance(v, (bytes, bytearray, memoryview)):
        return None   # ασφάλεια: κανένα binary στο JSON
    return v

def rows_to_dicts(cur):
    cols = [c[0] for c in cur.description]
    for r in cur.fetchall():
        yield {cols[i]: _val(r[i]) for i in range(len(cols))}


# ── Queries (χτισμένα από τις discovered στήλες — verbatim, prefix στα collisions) ──
def build_tier_b_query(pcols):
    """PERIODOI_DATA (ΟΛΕΣ οι στήλες) + join context (EMPLOYEE ταυτότητα, CMP, ΥΠΟΚ, PERIODOI)."""
    p = ', '.join('p.[%s]' % c for c in pcols)
    emp = ('e.VAT, e.ID_EMP AS E_ID_EMP, e.CODE, e.SURNAME, e.NAME, e.FTHRNAME, '
           'e.AM_IKA, e.AM_KOIN_ASF, e.email, e.MOBILE, e.HRDATE, e.FRDATE, '
           'e.FR_REASON, e.FR_REASON_DESCR, e.IS_FUTURE_EMP, e.HOTEL_SEASONAL, '
           'e.SUPERVISOR, e.LENDING_FROM, e.LENDING_TO')
    ctx = ('c.ID_CMP, c.NAME AS CMP_NAME, c.VAT AS CMP_VAT, c.CMP_CODE, '
           'y.DESCR AS YPOKAT_DESCR, per.DESCR AS PERIODOS_DESCR, per.PER_TYPE')
    return (
        "SELECT %s, %s, %s\n"
        "FROM PERIODOI_DATA p\n"
        "JOIN EMPLOYEE e        ON e.ID_EMP = p.ID_EMP\n"
        "JOIN CMP c             ON c.ID_CMP = p.ID_CMP\n"
        "LEFT JOIN CMP_YPOKAT y ON y.ID_CMP = p.ID_CMP AND y.COD_YPOKAT = p.COD_YPOKAT\n"
        "LEFT JOIN PERIODOI per ON per.ID_PERIODOS = p.ID_PERIODOS\n"
    ) % (p, emp, ctx)

def build_tier_a_query(ecols):
    """EMPLOYEE — ΟΛΕΣ οι (μη-image) στήλες = πλήρες μητρώο ταυτοτήτων."""
    e = ', '.join('e.[%s]' % c for c in ecols)
    return "SELECT %s FROM EMPLOYEE e" % e


# ── Push (outbound HTTPS + token· TLS via certifi) ────────────────────────────
def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

def push(cfg, tier, mode, rows, dry=False):
    batch = int(cfg.get('BATCH', '500'))
    endpoint = cfg['ESTIA_URL'].rstrip('/') + '/api/datahub/ingest'
    ctx = _ctx()
    total = {'staged': 0, 'upserted': 0, 'created': 0, 'amounts': 0}
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        body = json.dumps({'source': 'bmisthos', 'tier': tier, 'mode': mode, 'rows': chunk}).encode('utf-8')
        if dry:
            print('   [dry] tier %s batch %d rows=%d (δεν στέλνω)' % (tier, i // batch + 1, len(chunk)))
            continue
        req = urllib.request.Request(endpoint, data=body, method='POST',
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + cfg['ESTIA_TOKEN']})
        with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
            j = json.loads(resp.read().decode('utf-8'))
        if j.get('status') != 'ok':
            print('   ✗ tier %s batch %d: %s' % (tier, i // batch + 1, j)); return None
        for k in total:
            total[k] += j.get(k, 0)
        print('   tier %s batch %d/%d: staged+%d upserted+%d amounts+%d' % (
            tier, i // batch + 1, (len(rows) + batch - 1) // batch,
            j.get('staged', 0), j.get('upserted', 0), j.get('amounts', 0)))
    return total


# ── Ροές ──────────────────────────────────────────────────────────────────────
def run_tier_a(cfg, cur, mode, dry):
    ecols = discover_columns(cur, 'EMPLOYEE')
    print('Tier A (EMPLOYEE): %d στήλες (χωρίς image/skip)' % len(ecols))
    cur.execute(build_tier_a_query(ecols))
    rows = list(rows_to_dicts(cur))
    print('Tier A: %d γραμμές μητρώου.' % len(rows))
    return push(cfg, 'A', mode, rows, dry)

def run_tier_b(cfg, cur, mode, dry, watermark=None, last_id=None):
    pcols = discover_columns(cur, 'PERIODOI_DATA')
    print('Tier B (PERIODOI_DATA): %d στήλες (χωρίς image/skip)' % len(pcols))
    q = build_tier_b_query(pcols)
    params = []
    if mode == 'live' and (watermark or last_id):
        q += "WHERE p.PER_CALCULATED_DATE > ? OR p.ID_EMP > ?\n"
        params = [watermark or datetime.datetime(1900, 1, 1), last_id or 0]
    q += "ORDER BY e.VAT, p.XRISI, p.PERIODOS_DATE, p.ID_PERIODOS"
    cur.execute(q, *params) if params else cur.execute(q)
    rows = list(rows_to_dicts(cur))
    print('Tier B: %d γραμμές μισθοδοσίας.' % len(rows))
    return push(cfg, 'B', mode, rows, dry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', action='store_true', help='εφάπαξ πλήρες (όλα τα έτη + μητρώο)')
    ap.add_argument('--live', action='store_true', help='incremental (watermark) + Tier A snapshot')
    ap.add_argument('--tier', choices=['A', 'B'], help='μόνο ένα tier')
    ap.add_argument('--dry', action='store_true', help='δείξε, μη στέλνεις')
    args = ap.parse_args()

    cfg = load_env()
    for req_key in ('EPSILON_CONN', 'ESTIA_URL', 'ESTIA_TOKEN'):
        if not cfg.get(req_key):
            print('✗ Λείπει config: %s (δες .env.example)' % req_key); sys.exit(2)

    mode = 'seed' if args.seed else ('live' if args.live else 'manual')
    print('== Data Hub Agent == mode=%s dry=%s' % (mode, args.dry))
    try:
        conn = _connect(cfg)
    except Exception as e:
        print('✗ Σύνδεση Epsilon απέτυχε: %s' % e); sys.exit(2)
    cur = conn.cursor()
    try:
        only = args.tier
        if only == 'A':
            run_tier_a(cfg, cur, mode, args.dry)
        elif only == 'B':
            run_tier_b(cfg, cur, mode, args.dry)
        else:
            # Tier A (ταυτότητες) πρώτα, μετά Tier B (ποσά)
            run_tier_a(cfg, cur, mode, args.dry)
            run_tier_b(cfg, cur, mode, args.dry)
    finally:
        cur.close(); conn.close()
    print('OK.')


if __name__ == '__main__':
    main()
