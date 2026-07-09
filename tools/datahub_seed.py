# -*- coding: utf-8 -*-
"""
tools/datahub_seed.py — Data Hub Φ2 «prove-the-pipe» (DH-02 / P-096)
====================================================================
Παίρνει το ΗΔΗ επικυρωμένο export της Epsilon (integration query §6· default
`02_MODULES_ESTIA/ΚΕΝΤΡΟ_ΔΕΔΟΜΕΝΩΝ/_explore/q_seed_2024.csv`), κάνει CONFORM
(ό,τι θα κάνει ο agent Φ3: ελλ. ημ/νίες→ISO, κόμμα-δεκαδικά τα χειρίζεται το endpoint,
κενά→null), το στέλνει σε batches στο `POST /api/datahub/ingest` και βγάζει
**reconciliation** (staging/curated counts + cent-level sums source-vs-landed + idempotency).

Αποδεικνύει ότι ο σωλήνας δουλεύει ΧΩΡΙΣ live agent. ΔΕΝ είναι μέρος της εφαρμογής
(δεν το εισάγει ποτέ το app.py). Read-only ως προς το CSV (protected source).

Χρήση:
  python tools/datahub_seed.py                       # τοπικά (fresh sqlite in-process) — DEFAULT
  python tools/datahub_seed.py --csv <path>          # άλλο export
  python tools/datahub_seed.py --url https://estia... --token XXX   # πραγματικό deployment (prod-seed)
Exit 0 = reconciliation καθαρό (cent-perfect + idempotent) · 1 = απόκλιση.
"""
import os, sys, csv, io, json, argparse, hashlib
from datetime import datetime

# UTF-8 stdout (Windows cp1253 — αλλιώς ελληνικά/exit≠0 σπάνε hooks)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                                   # .../00_ESTIA-REPO/estia
WORKSPACE = os.path.dirname(os.path.dirname(REPO))            # D:\ESTIA
DEFAULT_CSV = os.path.join(WORKSPACE, '02_MODULES_ESTIA',
                           'ΚΕΝΤΡΟ_ΔΕΔΟΜΕΝΩΝ', '_explore', 'q_seed_2024.csv')

DATE_COLS = ('HRDATE', 'FRDATE', 'PERIODOS_DATE', 'PER_CALCULATED_DATE')


# ── CONFORM (agent-side, προσομοίωση) ─────────────────────────────────────────
def gr_to_iso(v):
    """«19/3/2024 12:00:00 πμ» / «16/4/2024 12:43:19 μμ» → ISO. Κενό → None."""
    s = (v or '').strip()
    if not s:
        return None
    toks = s.split()
    try:
        dd, mm, yy = [int(x) for x in toks[0].split('/')]
    except Exception:
        return None
    H = Mi = S = 0
    if len(toks) >= 2 and ':' in toks[1]:
        hp = toks[1].split(':')
        try:
            H = int(hp[0]); Mi = int(hp[1]) if len(hp) > 1 else 0; S = int(hp[2]) if len(hp) > 2 else 0
        except Exception:
            H = Mi = S = 0
        ampm = toks[2] if len(toks) > 2 else ''
        if ampm == 'μμ' and H != 12:
            H += 12
        elif ampm == 'πμ' and H == 12:
            H = 0
    try:
        return datetime(yy, mm, dd, H, Mi, S).isoformat(sep=' ')
    except Exception:
        return None

def conform(row):
    """CSV dict → ingest dict. Ημ/νίες→ISO· κενά→None· υπόλοιπα raw (το endpoint κάνει _f/_i,
    χειρίζεται κόμμα-δεκαδικά & zero-pad ΑΦΜ)."""
    out = {}
    for k, v in row.items():
        if k is None:
            continue
        if k in DATE_COLS:
            out[k] = gr_to_iso(v)
        else:
            s = (v or '').strip()
            out[k] = s if s != '' else None
    return out


def _f(v):
    s = (v or '').strip().replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0

def _afm9(v):
    s = (v or '').strip()
    return s.zfill(9) if s.isdigit() else s


# ── SOURCE baseline (ground-truth για reconciliation) ─────────────────────────
def source_stats(rows):
    afm = set(_afm9(r.get('VAT')) for r in rows)
    grain = set()   # κλειδί curated: afm|cmp|year|id_periodos|per_type
    for r in rows:
        grain.add((_afm9(r.get('VAT')), r.get('ID_CMP'), r.get('XRISI'),
                   r.get('ID_PERIODOS'), r.get('PER_TYPE')))
    years = set(_i for _i in (r.get('XRISI') for r in rows) if _i)
    return {
        'rows': len(rows),
        'afm': len(afm),
        'grain': len(grain),
        'years': years,
        'M_APODOXES': round(sum(_f(r.get('M_APODOXES')) for r in rows), 2),
        'S_KOSTOS': round(sum(_f(r.get('S_KOSTOS')) for r in rows), 2),
        'PLIROTEO': round(sum(_f(r.get('PLIROTEO')) for r in rows), 2),
    }


# ── TARGETS ───────────────────────────────────────────────────────────────────
def _batches(rows, n):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]

def send_local(payload_rows, batch):
    """In-process test_client + fresh sqlite. Επιστρέφει (tallies, dbmod, appmod)."""
    import tempfile
    db = os.path.join(tempfile.gettempdir(), 'estia_datahub_seed.db')
    if os.path.exists(db):
        os.remove(db)
    os.environ['DATABASE_URL'] = 'sqlite:///' + db.replace('\\', '/')
    os.environ.setdefault('DATAHUB_INGEST_TOKEN', 'seed-local')
    sys.path.insert(0, REPO)
    os.chdir(REPO)
    print('   [local] φορτώνω app + άδεια sqlite… (%s)' % db)
    import app as A
    import datahub as D
    client = A.app.test_client()
    tok = os.environ['DATAHUB_INGEST_TOKEN']

    def post(chunk):
        r = client.post('/api/datahub/ingest',
                        data=json.dumps({'source': 'bmisthos', 'tier': 'B',
                                         'mode': 'seed', 'rows': chunk}),
                        content_type='application/json',
                        headers={'Authorization': 'Bearer ' + tok})
        return r.status_code, r.get_json()

    def send_all(chunks_rows, label):
        agg = {'staged': 0, 'upserted': 0, 'created': 0, 'amounts': 0}
        for bi, ch in enumerate(_batches(chunks_rows, batch), 1):
            sc, j = post(ch)
            if sc != 200 or (j or {}).get('status') != 'ok':
                print('   ✗ batch %d [%s] απέτυχε: %s %s' % (bi, label, sc, j))
                return None
            for k in agg:
                agg[k] += j.get(k, 0)
            print('   %s batch %d/%d: staged+%d upserted+%d amounts+%d' % (
                label, bi, (len(chunks_rows) + batch - 1) // batch,
                j.get('staged', 0), j.get('upserted', 0), j.get('amounts', 0)))
        return agg

    a1 = send_all(payload_rows, 'PASS-1')
    a2 = send_all(payload_rows, 'PASS-2(idem)')   # idempotency
    return a1, a2, {'kind': 'local', 'A': A, 'D': D}


def send_url(payload_rows, batch, url, token, year=None):
    import urllib.request
    base = url.rstrip('/')
    endpoint = base + '/api/datahub/ingest'
    print('   [url] POST → %s' % endpoint)

    def post(chunk):
        req = urllib.request.Request(
            endpoint, data=json.dumps({'source': 'bmisthos', 'tier': 'B',
                                       'mode': 'seed', 'rows': chunk}).encode('utf-8'),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer ' + token}, method='POST')
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    def send_all(chunks_rows, label):
        agg = {'staged': 0, 'upserted': 0, 'created': 0, 'amounts': 0}
        for bi, ch in enumerate(_batches(chunks_rows, batch), 1):
            sc, j = post(ch)
            if sc != 200 or (j or {}).get('status') != 'ok':
                print('   ✗ batch %d [%s]: %s %s' % (bi, label, sc, j)); return None
            for k in agg:
                agg[k] += j.get(k, 0)
            print('   %s batch %d: staged+%d upserted+%d amounts+%d' % (
                label, bi, j.get('staged', 0), j.get('upserted', 0), j.get('amounts', 0)))
        return agg

    a1 = send_all(payload_rows, 'PASS-1')
    a2 = send_all(payload_rows, 'PASS-2(idem)')
    # read-back verify από την παραγωγή (GET /api/datahub/verify) → πραγματικό reconciliation
    verify = None
    if a1 is not None:
        vurl = base + '/api/datahub/verify' + (('?year=%d' % year) if year else '')
        try:
            req = urllib.request.Request(vurl, headers={'Authorization': 'Bearer ' + token}, method='GET')
            with urllib.request.urlopen(req, timeout=120) as resp:
                verify = json.loads(resp.read().decode('utf-8'))
            print('   [url] verify ← %s' % vurl)
        except Exception as e:
            print('   ⚠ verify GET απέτυχε (%s) — reconciliation μόνο με endpoint tallies' % e)
    return a1, a2, {'kind': 'url', 'verify': verify}


# ── RECONCILIATION ────────────────────────────────────────────────────────────
def reconcile(src, a1, a2, ctx):
    print('\n' + '=' * 64)
    print('RECONCILIATION — source vs landed')
    print('=' * 64)
    fails = 0

    def chk(name, ok, detail=''):
        nonlocal fails
        print(('  OK   ' if ok else ' FAIL  ') + name + (('  → ' + detail) if detail else ''))
        if not ok:
            fails += 1

    print('SOURCE: rows=%d · ΑΦΜ=%d · grain(afm×cmp×έτος×περ×τύπο)=%d' % (src['rows'], src['afm'], src['grain']))
    print('        Σ M_APODOXES=%.2f · Σ S_KOSTOS=%.2f · Σ PLIROTEO=%.2f' % (src['M_APODOXES'], src['S_KOSTOS'], src['PLIROTEO']))
    print('PASS-1 endpoint tallies: %s' % a1)
    print('PASS-2 (idempotency)   : %s' % a2)

    # endpoint-level (ισχύει και για url mode)
    chk('PASS-1 staged == rows πηγής', a1 and a1['staged'] == src['rows'], '%s vs %s' % (a1 and a1['staged'], src['rows']))
    chk('idempotency: PASS-2 staged == 0', a2 and a2['staged'] == 0, str(a2 and a2['staged']))

    # ── URL mode: read-back verify από την παραγωγή ──
    if ctx.get('kind') == 'url':
        v = ctx.get('verify')
        if not v:
            print('\n⚠ δεν ήρθε verify από την παραγωγή — reconciliation μόνο με endpoint tallies (staged/idempotency).')
            return fails
        stg = v.get('staging', {}); cur = v.get('curated', {}); syn = v.get('sync', {})
        print('\nLANDED (verify@prod): staging=%s · curated=%s · curated ΑΦΜ=%s' % (
            stg.get('rows'), cur.get('rows'), cur.get('distinct_afm')))
        print('  staging Σ: Αποδ=%s Κόστος=%s Πληρ=%s' % (stg.get('sum_M_APODOXES'), stg.get('sum_S_KOSTOS'), stg.get('sum_PLIROTEO')))
        print('  curated Σ: Αποδ=%s Κόστος=%s Καθαρές=%s' % (cur.get('sum_gross'), cur.get('sum_employer_cost'), cur.get('sum_net')))
        print('  sync: batches=%s guard_nonzero=%s last_status=%s' % (syn.get('batches'), syn.get('guard_nonzero_count'), syn.get('last_status')))
        chk('staging rows == πηγή', stg.get('rows') == src['rows'], '%s vs %s' % (stg.get('rows'), src['rows']))
        chk('staging Σ M_APODOXES cent-perfect', abs((stg.get('sum_M_APODOXES') or 0) - src['M_APODOXES']) < 0.01, '%s vs %.2f' % (stg.get('sum_M_APODOXES'), src['M_APODOXES']))
        chk('staging Σ S_KOSTOS cent-perfect', abs((stg.get('sum_S_KOSTOS') or 0) - src['S_KOSTOS']) < 0.01, '%s vs %.2f' % (stg.get('sum_S_KOSTOS'), src['S_KOSTOS']))
        chk('curated Σ Αποδοχές cent-perfect (SUM)', abs((cur.get('sum_gross') or 0) - src['M_APODOXES']) < 0.01, '%s vs %.2f' % (cur.get('sum_gross'), src['M_APODOXES']))
        chk('curated Σ Κόστος cent-perfect (SUM)', abs((cur.get('sum_employer_cost') or 0) - src['S_KOSTOS']) < 0.01, '%s vs %.2f' % (cur.get('sum_employer_cost'), src['S_KOSTOS']))
        chk('curated rows == grain πηγής', cur.get('rows') == src['grain'], '%s vs %s' % (cur.get('rows'), src['grain']))
        chk('guard flags == 0', (syn.get('guard_nonzero_count') or 0) == 0, str(syn.get('guard_nonzero_count')))
        chk('last sync status == ok', syn.get('last_status') == 'ok', str(syn.get('last_status')))
        if src['grain'] != src['rows']:
            print('  NOTE  %d γραμμές αθροίστηκαν σε %d curated grains (ίδιο άτομο×μήνα, πολλαπλά επεισόδια) — όπως το εκκαθαριστικό.' % (src['rows'] - src['grain'], src['grain']))
        return fails

    # ── LOCAL mode: DB-level reconciliation ──
    A = ctx['A']; D = ctx['D']
    with A.app.app_context():
        st = D.DatahubStagingBmisthos.query.count()
        ln_rows = D.LegalNetImport.query.filter_by(source_file='datahub:bmisthos').count()
        # cent-level sums στο STAGING (bronze — πρέπει cent-perfect, τίποτα δεν χάνεται)
        from sqlalchemy import func
        s_apod = A.db.session.query(func.coalesce(func.sum(D.DatahubStagingBmisthos.M_APODOXES), 0.0)).scalar()
        s_kost = A.db.session.query(func.coalesce(func.sum(D.DatahubStagingBmisthos.S_KOSTOS), 0.0)).scalar()
        s_plir = A.db.session.query(func.coalesce(func.sum(D.DatahubStagingBmisthos.PLIROTEO), 0.0)).scalar()
        # curated sums
        c_apod = A.db.session.query(func.coalesce(func.sum(D.LegalNetImport.gross_legal), 0.0)).filter(
            D.LegalNetImport.source_file == 'datahub:bmisthos').scalar()
        c_kost = A.db.session.query(func.coalesce(func.sum(D.LegalNetImport.employer_cost_legal), 0.0)).filter(
            D.LegalNetImport.source_file == 'datahub:bmisthos').scalar()
        # distinct ΑΦΜ curated
        c_afm = A.db.session.query(func.count(func.distinct(D.LegalNetImport.afm))).filter(
            D.LegalNetImport.source_file == 'datahub:bmisthos').scalar()

    print('\nLANDED: staging=%d · curated(LegalNetImport)=%d · curated ΑΦΜ=%d' % (st, ln_rows, c_afm))
    chk('staging rows == πηγή', st == src['rows'], '%d vs %d' % (st, src['rows']))
    chk('staging Σ M_APODOXES cent-perfect', abs(s_apod - src['M_APODOXES']) < 0.01, '%.2f vs %.2f' % (s_apod, src['M_APODOXES']))
    chk('staging Σ S_KOSTOS cent-perfect', abs(s_kost - src['S_KOSTOS']) < 0.01, '%.2f vs %.2f' % (s_kost, src['S_KOSTOS']))
    chk('staging Σ PLIROTEO cent-perfect', abs(s_plir - src['PLIROTEO']) < 0.01, '%.2f vs %.2f' % (s_plir, src['PLIROTEO']))
    chk('curated ΑΦΜ == πηγή', c_afm == src['afm'], '%d vs %d' % (c_afm, src['afm']))
    chk('curated rows == grain πηγής', ln_rows == src['grain'], '%d vs %d' % (ln_rows, src['grain']))
    # curated ποσά: cent-perfect ΠΑΝΤΑ — αθροίζουμε τα επεισόδια ανά grain (P-097/DH-06)
    chk('curated Σ M_APODOXES cent-perfect (SUM)', abs(c_apod - src['M_APODOXES']) < 0.01, '%.2f vs %.2f' % (c_apod, src['M_APODOXES']))
    chk('curated Σ S_KOSTOS cent-perfect (SUM)', abs(c_kost - src['S_KOSTOS']) < 0.01, '%.2f vs %.2f' % (c_kost, src['S_KOSTOS']))
    if src['grain'] != src['rows']:
        d = src['rows'] - src['grain']
        print('  NOTE  %d γραμμές συμπτύχθηκαν σε %d curated grains (ίδιο άτομο×μήνα, πολλαπλά επεισόδια) → ΑΘΡΟΙΣΤΗΚΑΝ (όπως το εκκαθαριστικό).' % (d, src['grain']))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=DEFAULT_CSV)
    ap.add_argument('--batch', type=int, default=500)
    ap.add_argument('--url', default=None, help='πραγματικό deployment (αλλιώς τοπικά in-process)')
    ap.add_argument('--token', default=os.environ.get('DATAHUB_INGEST_TOKEN'))
    args = ap.parse_args()

    print('== Data Hub Φ2 — prove-the-pipe ==')
    print('CSV: %s' % args.csv)
    if not os.path.exists(args.csv):
        print('✗ Δεν βρέθηκε το CSV.'); sys.exit(1)
    with io.open(args.csv, encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    print('Διαβάστηκαν %d γραμμές.' % len(rows))

    src = source_stats(rows)
    payload = [conform(r) for r in rows]

    if args.url:
        if not args.token:
            print('✗ url mode: απαιτείται --token ή env DATAHUB_INGEST_TOKEN'); sys.exit(1)
        one_year = list(src['years'])[0] if len(src['years']) == 1 else None
        a1, a2, ctx = send_url(payload, args.batch, args.url, args.token, year=one_year)
    else:
        a1, a2, ctx = send_local(payload, args.batch)

    if a1 is None or a2 is None:
        print('\n✗ Το POST απέτυχε — δες παραπάνω.'); sys.exit(1)

    fails = reconcile(src, a1, a2, ctx)
    print('\n' + '=' * 64)
    print('ΑΠΟΤΕΛΕΣΜΑ: %s (%d αποκλίσεις)' % ('✓ ΚΑΘΑΡΟ' if fails == 0 else '✗ ΑΠΟΚΛΙΣΕΙΣ', fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
