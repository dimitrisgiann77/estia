# -*- coding: utf-8 -*-
"""brief.py — Boot Briefing / read-only aggregator (SPEC-BRIEF-001 · P-003/P-043/P-044).

Διαβάζει τα ΥΠΑΡΧΟΝΤΑ trackers (root + modules + μητρώο P-xxx + app CHANGELOG) και
παράγει την κάρτα ανοίγματος + «τι μου αναλογεί» (φίλτρο Owner). ΔΕΝ γράφει τίποτα.

Χρήση:  python tools/brief.py [--for code|cowork|giannis] [--json]
Αρχή:   read-only · exit 0 πάντα · διατηρεί τη ροή (καμία μετακίνηση pending).
"""
import os, re, sys, glob, json

# Windows consoles default to cp1253 (Greek) → emoji/utf-8 crash με UnicodeEncodeError.
# Force UTF-8 με errors='replace' ώστε ΠΟΤΕ να μην σκάει (spec: exit 0 πάντα).
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MARK = '00_ΜΝΗΜΗ_ESTIA.md'  # 00_ΜΝΗΜΗ_ESTIA.md
PEND = 'ΕΚΚΡΕΜΟΤΗΤΕΣ.md'  # ΕΚΚΡΕΜΟΤΗΤΕΣ.md
REGDIR = os.path.join('GOVERNANCE_DASHBOARD', '_REGISTRY')  # P-118: ενοποιημένο μητρώο

# ── P-118 Φ2 (cutover flag) ──────────────────────────────────────────────────
# False = ΤΡΕΧΟΥΣΑ συμπεριφορά (διαβάζει ΕΚΚΡΕΜΟΤΗΤΕΣ.md + ΜΗΤΡΩΟ). True = διαβάζει _REGISTRY/.
# ΑΛΛΑΞΕ σε True ΜΟΝΟ ταυτόχρονα με Cowork _build.py ΚΑΙ αφού τρέξει migrate_registry.py --apply
# (αλλιώς κενή/μερική κάρτα boot). Δοκιμή χωρίς commit: env ESTIA_BRIEF_REGISTRY=1.
USE_REGISTRY = (os.environ.get('ESTIA_BRIEF_REGISTRY') == '1') or True   # P-118 Φ2: LIVE (cutover 12/07)
REG_MIN = 50  # δικλείδα: κάτω από τόσα task/bug records → μη-πληθυσμένο → fallback (όχι κενή κάρτα)

def find_root():
    seeds = [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]
    for start in seeds:
        d = start
        for _ in range(8):
            if os.path.exists(os.path.join(d, MARK)):
                return d
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    return None

def rd(p):
    try:
        return open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        return ''

def parse_rows(txt):
    rows = []
    for ln in txt.splitlines():
        if re.match(r'\s*\|\s*[A-Z]{2,4}-\d', ln):
            c = [x.strip() for x in ln.strip().strip('|').split('|')]
            if len(c) >= 7:
                rows.append({'id': c[0], 'date': c[1], 'header': c[2], 'origin': c[3],
                             'notes': c[4], 'owner': (c[5] or 'Code'),
                             'stage': (c[6] or 'NEW').upper()})
    return rows

def modname(path):
    p = path.replace('\\', '/').split('/')
    if '02_MODULES_ESTIA' in p:
        i = p.index('02_MODULES_ESTIA')
        return '/'.join(p[i + 1:i + 3])
    return 'ROOT'

def collect(root):
    trackers = [os.path.join(root, PEND)] + glob.glob(
        os.path.join(root, '02_MODULES_ESTIA', '**', PEND), recursive=True)
    allrows, modcount = [], {}
    for f in trackers:
        rows = parse_rows(rd(f))
        mod = modname(f)
        opn = 0
        for r in rows:
            r['mod'] = mod
            allrows.append(r)
            if r['stage'] != 'DONE':
                opn += 1
        if opn:
            modcount[mod] = modcount.get(mod, 0) + opn
    return allrows, modcount

def parse_fm(txt):
    """Front-matter (μεταξύ των δύο πρώτων '---') → dict. split στο ΠΡΩΤΟ ':' (headers έχουν ':')."""
    lines = txt.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    d = {}
    for ln in lines[1:]:
        if ln.strip() == '---':
            break
        if ':' in ln:
            k, v = ln.split(':', 1)
            d[k.strip()] = v.strip()
    return d

def collect_registry(root):
    """P-118: διαβάζει _REGISTRY/*.md (record-ανά-αρχείο). Ίδιο σχήμα rows με collect().
    tasks/bugs → allrows+modcount· proposals με decision=open → prop_open."""
    files = glob.glob(os.path.join(root, REGDIR, '*.md'))
    allrows, modcount, prop_open = [], {}, 0
    for f in files:
        d = parse_fm(rd(f))
        if not d.get('id'):
            continue
        if d.get('type') == 'proposal':
            if (d.get('decision') or 'open') == 'open':
                prop_open += 1
            continue
        stage = (d.get('stage') or 'NEW').upper()
        mod = d.get('module') or 'ROOT'
        allrows.append({'id': d['id'], 'date': d.get('created', ''), 'header': d.get('header', ''),
                        'origin': d.get('source', ''), 'notes': '', 'owner': (d.get('owner') or 'Code'),
                        'stage': stage, 'mod': mod})
        if stage != 'DONE':
            modcount[mod] = modcount.get(mod, 0) + 1
    return allrows, modcount, prop_open

def app_changelog(root):
    appsrc = rd(os.path.join(root, '00_ESTIA-REPO', 'estia', 'app.py'))
    return re.findall(
        r"\{'v':\s*'([^']+)',\s*'b':\s*'[^']*',\s*'date':\s*'([^']+)',"
        r"\s*'time':\s*'[^']*',\s*'title':\s*'([^']+)'", appsrc)

def build(root, recipient):
    mv = re.search(r'v12\.\d+', rd(os.path.join(root, MARK)))
    version = mv.group(0) if mv else 'v12.x'
    src = 'trackers'
    used = False
    if USE_REGISTRY:
        r_rows, r_mod, r_prop = collect_registry(root)
        if len(r_rows) >= REG_MIN:  # δικλείδα: πληθυσμένο → χρησιμοποίησέ το
            allrows, modcount, prop_open, src, used = r_rows, r_mod, r_prop, 'registry', True
    if not used:  # default ή fallback (registry μη-πληθυσμένο) → παλιά trackers
        allrows, modcount = collect(root)
        reg = rd(os.path.join(root, 'GOVERNANCE_DASHBOARD', 'ΜΗΤΡΩΟ_ΠΡΟΤΑΣΕΩΝ.md'))
        prop_open = sum(1 for ln in reg.splitlines()
                        if re.match(r'\s*\|\s*P-\d', ln) and '\U0001f7e1' in ln)
    open_rows = [r for r in allrows if r['stage'] != 'DONE']
    mine = [r for r in open_rows if r['owner'].lower() == recipient.lower()]
    cl = app_changelog(root)
    return {
        'version': version, 'recipient': recipient,
        'recent': [{'v': v, 'date': d, 'title': t} for (v, d, t) in cl[:5]],
        'mine': [{'id': r['id'], 'mod': r['mod'], 'header': r['header'], 'stage': r['stage']} for r in mine],
        'modcount': modcount, 'open_total': len(open_rows), 'prop_open': prop_open,
        'source': src,  # P-118: 'trackers' (παλιό) ή 'registry' (μετά cutover)
        'next': (mine[0]['header'] if mine else (open_rows[0]['header'] if open_rows else '—')),
    }

def render(b):
    L = []
    L.append('\U0001f4cd Πού είμαστε: %s (Εστία)' % b['version'])
    if b['recent']:
        r0 = b['recent'][0]
        L.append('\U0001f517 Συνέχεια: v%s — %s' % (r0['v'], r0['title']))
        L.append('✅ Πρόσφατα: ' + ' · '.join('v%s' % r['v'] for r in b['recent']))
    if b['mine']:
        CAP = 8  # P-045: shortlist αντί για dump ΟΛΩΝ — καθαρή κάρτα boot
        head = b['mine'][:CAP]
        ids = ' · '.join('%s' % m['id'] for m in head)
        extra = len(b['mine']) - len(head)
        if extra > 0:
            ids += ' · …+%d ακόμη' % extra
        L.append('\U0001f4e5 Για σένα (Owner=%s): %s' % (b['recipient'], ids))
    else:
        L.append('\U0001f4e5 Για σένα (Owner=%s): καθαρό' % b['recipient'])
    mc = ' · '.join('%s (%d)' % (k, v) for k, v in sorted(b['modcount'].items(), key=lambda x: -x[1]))
    L.append('⏳ Ανοιχτά ανά module: ' + (mc or '—'))
    L.append('\U0001f5f3️ Χρειάζονται απόφαση: %d προτάσεις (P-xxx)' % b['prop_open'])
    L.append('▶️ Προτεινόμενο επόμενο: %s' % b['next'])
    return '\n'.join(L)

def main():
    args = sys.argv[1:]
    recipient = 'Cowork'
    if '--for' in args:
        try:
            v = args[args.index('--for') + 1].lower()
            recipient = {'code': 'Code', 'cowork': 'Cowork', 'giannis': 'Giannis'}.get(v, 'Cowork')
        except Exception:
            pass
    try:
        root = find_root()
        if not root:
            print('brief: δεν βρέθηκε ο φάκελος docs (%s).' % MARK)
            return 0
        b = build(root, recipient)
        if '--json' in args:
            print(json.dumps(b, ensure_ascii=False, indent=2))
        else:
            print(render(b))
    except Exception as e:
        # read-only aggregator: ποτέ δεν ρίχνει το boot — απλώς ενημερώνει.
        print('brief: μη κρίσιμο σφάλμα ανάγνωσης (%s). Συνεχίζουμε.' % e)
    return 0

if __name__ == '__main__':
    sys.exit(main())
