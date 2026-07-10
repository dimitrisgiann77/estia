# -*- coding: utf-8 -*-
"""
Εστία — Module «Κέντρο Δεδομένων» (Data Hub) — Φ1: Landing model + ingest endpoint
==================================================================================
Plug-in: `import datahub` από το ΤΕΛΟΣ του app.py (αφού οριστούν app/db/helpers ΚΑΙ
αφού φορτωθεί το payroll, ΠΡΙΝ το init_db() ώστε το create_all να πιάσει τους νέους πίνακες).

Το «λιμάνι» υποδοχής στην Εστία (cloud) πριν τον on-prem agent (Φ3). Δέχεται push από τον
agent (outbound HTTPS + bearer token), γράφει bronze staging (verbatim, τίποτα δεν χάνεται),
κάνει idempotent upsert στα curated (EmployeePII/LegalNetImport, κλειδί ΑΦΜ) και audit sync log.

Specs: 02_MODULES_ESTIA/ΚΕΝΤΡΟ_ΔΕΔΟΜΕΝΩΝ/LANDING_SCHEMA.md · SOURCE_MAP_EPSILON.md · AGENT_DESIGN.md
Handoff: GOVERNANCE_DASHBOARD/_handoff/INBOX/2026-07-09-datahub-phase1-landing.md (P-093 Φ1)

ΕΚΤΟΣ Φ1 (χωριστά tasks): on-prem agent (Φ3), review/monitoring UI (P-091, Φ4), Pylon (Φ4).
ΔΕΝ αλλάζει layout/menu. Read-only στην Epsilon (μονόδρομη ροή).
"""
import os, json, hashlib, uuid
from datetime import datetime, date
from flask import request, jsonify, render_template, redirect, url_for

from app import app, db, _add_col
# curated προορισμοί ζουν στο payroll (owner των πινάκων EmployeePII/LegalNetImport/Company)
from payroll import (EmployeePII, LegalNetImport, Company, User,
                     _create_locked_employee, _company_from_name)


# ── Λεξικά χαρτογράφησης (SOURCE_MAP §4/§8) ───────────────────────────────────
PER_TYPE_KIND = {   # PER_TYPE → period_kind (κείμενο, όπως LegalNetImport.period_kind)
    1: 'monthly', 4: 'Δώρο Χριστουγέννων', 2: 'Δώρο Πάσχα', 3: 'Επίδομα Αδείας',
    5: 'Αποδοχές Αδείας', 6: 'Αποζημίωση Απόλυσης', 7: 'Αναδρομικά αποδοχών',
    8: 'Αναδρομικά εισφορών', 9: 'Εκκαθάριση Φόρου', 10: 'Αναστολή/COVID',
    99: 'Ειδικά', 0: 'Ειδικά',
}
EMP_KIND_TXT = {0: 'Έμμισθος', 1: 'Ημερομίσθιος', 2: 'Ωρομίσθιος'}
ORISMENOU_TXT = {1: 'Αορίστου', 0: 'Ορισμένου'}   # ⚠ ανάποδο όνομα (SOURCE_MAP §8)


# ── Coercions (ανθεκτικά — κακή/κενή τιμή → None, ποτέ crash στο ingest) ───────
def _s(v, n=None):
    if v is None:
        return None
    # strip \x00 (η Postgres απορρίπτει null bytes σε text) + άλλους C0 control χαρακτήρες
    s = str(v).replace('\x00', '')
    s = ''.join(ch for ch in s if ch >= ' ' or ch in '\t\n\r').strip()
    if s == '':
        return None
    return s[:n] if n else s

def _f(v):
    if v in (None, ''):
        return None
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None

def _i(v):
    if v in (None, ''):
        return None
    try:
        return int(float(str(v)))
    except Exception:
        return None

def _b(v):
    if v in (None, ''):
        return None
    s = str(v).strip().lower()
    return s in ('1', 'true', 't', 'yes', 'ναι', 'y')

def _dt(v):
    """Δέχεται ISO date/datetime string ή date/datetime object → datetime|None."""
    if v in (None, ''):
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace('T', ' ').replace('Z', '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(s[:len(fmt) + 4], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _afm9(v):
    """ΚΛΕΙΔΙ ΤΑΥΤΟΤΗΤΑΣ — zero-pad σε 9 ψηφία (SOURCE_MAP §5, κρίσιμο)."""
    if v in (None, ''):
        return None
    s = str(v).strip()
    if s.isdigit():
        return s.zfill(9)
    return s[:12]


# ── ΜΟΝΤΕΛΑ (control plane + bronze staging + audit) ──────────────────────────
class DatahubSource(db.Model):
    """Μητρώο πηγών (control plane· LANDING_SCHEMA §1). Μία γραμμή ανά πρόγραμμα-πηγή."""
    id                = db.Column(db.Integer, primary_key=True)
    source            = db.Column(db.String(20), unique=True, index=True)  # bmisthos/pylon
    vendor            = db.Column(db.String(20))    # epsilon
    kind              = db.Column(db.String(20))    # payroll/finance_pms
    db_instance       = db.Column(db.String(80))
    last_watermark    = db.Column(db.DateTime)      # τελευταίο PER_CALCULATED_DATE
    last_id_seen      = db.Column(db.Integer)       # τελευταίο MAX(ID_EMP) (Tier A)
    last_sync_at      = db.Column(db.DateTime)
    enabled           = db.Column(db.Boolean, default=True)
    refresh_requested = db.Column(db.Boolean, default=False)  # κουμπί «Refresh τώρα» (Φ4→agent)


class DatahubStagingBmisthos(db.Model):
    """Bronze landing — ΟΛΕΣ οι στήλες verbatim Epsilon (LANDING_SCHEMA §2 / SOURCE_MAP §9).
    ΔΕΝ είναι μητρώο προσωπικού: raw landing (φυσικά κλειδιά Epsilon, χωρίς user_id) —
    τεκμηριωμένη εξαίρεση στο arch_map (KNOWN_OK_ENTITIES). Τίποτα δεν χάνεται."""
    id      = db.Column(db.Integer, primary_key=True)
    # — φυσικό κλειδί: VAT+ID_CMP+XRISI+ID_PERIODOS+ID_EMP —
    VAT     = db.Column(db.String(20), index=True)
    ID_EMP  = db.Column(db.Integer, index=True)
    CODE    = db.Column(db.String(20))
    SURNAME = db.Column(db.String(120))
    NAME    = db.Column(db.String(120))
    FTHRNAME = db.Column(db.String(120))
    AM_IKA  = db.Column(db.String(20))
    AM_KOIN_ASF = db.Column(db.String(20))
    email   = db.Column(db.String(160))
    MOBILE  = db.Column(db.String(40))
    HRDATE  = db.Column(db.DateTime)
    FRDATE  = db.Column(db.DateTime)
    FR_REASON = db.Column(db.String(40))
    FR_REASON_DESCR = db.Column(db.String(160))
    IS_FUTURE_EMP = db.Column(db.String(10))
    HOTEL_SEASONAL = db.Column(db.String(20))
    SUPERVISOR = db.Column(db.Integer)
    LENDING_FROM = db.Column(db.String(80))
    LENDING_TO = db.Column(db.String(80))
    ID_CMP  = db.Column(db.Integer, index=True)
    CMP_NAME = db.Column(db.String(160))
    CMP_VAT = db.Column(db.String(20))
    CMP_CODE = db.Column(db.String(20))
    COD_YPOKAT = db.Column(db.String(20))
    YPOKAT_DESCR = db.Column(db.String(160))
    TMHMA   = db.Column(db.String(160))
    ID_ADMINISTRATION = db.Column(db.Integer)
    ID_ADMINISTRATION_SUB = db.Column(db.Integer)
    XRISI   = db.Column(db.Integer, index=True)
    ID_PERIODOS = db.Column(db.Integer, index=True)
    PERIODOS_DESCR = db.Column(db.String(120))
    PER_TYPE = db.Column(db.Integer)
    PERIODOS_DATE = db.Column(db.DateTime)
    SPC_DESCR = db.Column(db.String(160))
    CNDTDESCR = db.Column(db.String(200))
    EMP_KIND = db.Column(db.Integer)
    MERIKH_APASX = db.Column(db.Integer)
    ORISMENOU = db.Column(db.Integer)
    PAY_TYPE = db.Column(db.Integer)
    WORKING_DAYS = db.Column(db.Float)
    SALARY  = db.Column(db.Float)
    M_APODOXES = db.Column(db.Float)
    PROSTHETES_SUM = db.Column(db.Float)
    PROSTHETES_SUM_NOKRAT = db.Column(db.Float)
    SKRATISEIS_ERGAZ = db.Column(db.Float)
    SKRATISEIS_ERGOD = db.Column(db.Float)
    FMY     = db.Column(db.Float)
    XARTOSHMO = db.Column(db.Float)
    PROKATAVOLI = db.Column(db.Float)
    PAROXES = db.Column(db.Float)
    PLIROTEO = db.Column(db.Float)
    S_KOSTOS = db.Column(db.Float)
    APOZ_APOL_SALARY = db.Column(db.Float)
    PER_CALCULATED_DATE = db.Column(db.DateTime)
    # — meta —
    ingested_at = db.Column(db.DateTime, default=datetime.now, index=True)
    row_hash = db.Column(db.String(40), unique=True, index=True)  # idempotency
    batch_id = db.Column(db.String(48), index=True)               # → sync_log
    raw_json = db.Column(db.Text)                                 # πλήρες raw (lossless backstop)


# πεδία staging που γράφονται verbatim από το row (όνομα = Epsilon key)
_STAGING_STR = ('CODE', 'SURNAME', 'NAME', 'FTHRNAME', 'AM_IKA', 'AM_KOIN_ASF',
                'MOBILE', 'FR_REASON', 'FR_REASON_DESCR', 'IS_FUTURE_EMP', 'HOTEL_SEASONAL',
                'LENDING_FROM', 'LENDING_TO', 'CMP_NAME', 'CMP_VAT', 'CMP_CODE',
                'COD_YPOKAT', 'YPOKAT_DESCR', 'TMHMA', 'PERIODOS_DESCR', 'SPC_DESCR', 'CNDTDESCR')
_STAGING_INT = ('ID_EMP', 'SUPERVISOR', 'ID_CMP', 'ID_ADMINISTRATION', 'ID_ADMINISTRATION_SUB',
                'XRISI', 'ID_PERIODOS', 'PER_TYPE', 'EMP_KIND', 'MERIKH_APASX', 'ORISMENOU', 'PAY_TYPE')
_STAGING_FLOAT = ('WORKING_DAYS', 'SALARY', 'M_APODOXES', 'PROSTHETES_SUM', 'PROSTHETES_SUM_NOKRAT',
                  'SKRATISEIS_ERGAZ', 'SKRATISEIS_ERGOD', 'FMY', 'XARTOSHMO', 'PROKATAVOLI',
                  'PAROXES', 'PLIROTEO', 'S_KOSTOS', 'APOZ_APOL_SALARY')
_STAGING_DT = ('HRDATE', 'FRDATE', 'PERIODOS_DATE', 'PER_CALCULATED_DATE')


class DatahubSyncLog(db.Model):
    """Audit ανά κύκλο συγχρονισμού (LANDING_SCHEMA §5)."""
    id           = db.Column(db.Integer, primary_key=True)
    batch_id     = db.Column(db.String(48), index=True)
    source       = db.Column(db.String(20), index=True)  # bmisthos/pylon
    tier         = db.Column(db.String(1))                # A/B
    mode         = db.Column(db.String(10))               # seed/live/manual
    started_at   = db.Column(db.DateTime)
    finished_at  = db.Column(db.DateTime)
    rows_read    = db.Column(db.Integer, default=0)
    rows_upserted = db.Column(db.Integer, default=0)
    watermark_to = db.Column(db.DateTime)
    guard_flags  = db.Column(db.Text)     # f_* που σήκωσαν σημαία (0 = καθαρό)
    status       = db.Column(db.String(10))  # ok/error
    error        = db.Column(db.Text)


# ── MIGRATION (μη καταστροφικό — καμία αλλαγή υπάρχουσας στήλης) ───────────────
def ensure_datahub_columns():
    """ALTER ADD COLUMN για τις επεκτάσεις EmployeePII (+10) & LegalNetImport (+15).
    Οι νέοι πίνακες (datahub_*) πιάνονται από create_all()."""
    with app.app_context():
        try:
            pg = db.engine.dialect.name == 'postgresql'
            DT = 'TIMESTAMP' if pg else 'DATETIME'   # Postgres δεν έχει DATETIME
            BOOL = 'BOOLEAN'
            # EmployeePII +10 (LANDING_SCHEMA §3)
            _add_col('employee_pii', 'email', 'email VARCHAR(160)')
            _add_col('employee_pii', 'mobile', 'mobile VARCHAR(40)')
            _add_col('employee_pii', 'fr_reason', 'fr_reason VARCHAR(40)')
            _add_col('employee_pii', 'fr_reason_descr', 'fr_reason_descr VARCHAR(160)')
            _add_col('employee_pii', 'is_future_emp', 'is_future_emp %s' % BOOL)
            _add_col('employee_pii', 'hotel_seasonal', 'hotel_seasonal VARCHAR(20)')
            _add_col('employee_pii', 'supervisor_id_emp', 'supervisor_id_emp INTEGER')
            _add_col('employee_pii', 'lending_from', 'lending_from VARCHAR(80)')
            _add_col('employee_pii', 'lending_to', 'lending_to VARCHAR(80)')
            _add_col('employee_pii', 'id_emp_current', 'id_emp_current INTEGER')
            # LegalNetImport +15 (LANDING_SCHEMA §4)
            _add_col('legal_net_import', 'prosthetes_sum', 'prosthetes_sum FLOAT')
            _add_col('legal_net_import', 'prosthetes_sum_nokrat', 'prosthetes_sum_nokrat FLOAT')
            _add_col('legal_net_import', 'skratiseis_ergod', 'skratiseis_ergod FLOAT')
            _add_col('legal_net_import', 'xartoshmo', 'xartoshmo FLOAT')
            _add_col('legal_net_import', 'prokatavoli', 'prokatavoli FLOAT')
            _add_col('legal_net_import', 'paroxes', 'paroxes FLOAT')
            _add_col('legal_net_import', 's_kostos', 's_kostos FLOAT')
            _add_col('legal_net_import', 'apoz_apol_salary', 'apoz_apol_salary FLOAT')
            _add_col('legal_net_import', 'salary', 'salary FLOAT')
            _add_col('legal_net_import', 'working_days', 'working_days FLOAT')
            _add_col('legal_net_import', 'id_periodos', 'id_periodos INTEGER')
            _add_col('legal_net_import', 'per_type', 'per_type INTEGER')
            _add_col('legal_net_import', 'periodos_date', 'periodos_date %s' % DT)
            _add_col('legal_net_import', 'per_calculated_date', 'per_calculated_date %s' % DT)
            _add_col('legal_net_import', 'katavliteo', 'katavliteo FLOAT')
        except Exception as e:
            print('ensure_datahub_columns skipped:', e)


# ── SEED (idempotent) — 1 γραμμή μητρώου πηγών ────────────────────────────────
def seed_datahub():
    with app.app_context():
        try:
            if not DatahubSource.query.filter_by(source='bmisthos').first():
                db.session.add(DatahubSource(
                    source='bmisthos', vendor='epsilon', kind='payroll',
                    db_instance='WIN-TQ396JC4P4R\\EPSILON12', enabled=True,
                    refresh_requested=False))
                db.session.commit()
        except Exception as e:
            db.session.rollback(); print('seed_datahub skipped:', e)


# ── STAGING (bronze) ──────────────────────────────────────────────────────────
def _row_hash(row):
    """sha1 πλήρους raw row → idempotency (ίδια γραμμή = ίδιο hash = skip)."""
    blob = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(blob.encode('utf-8')).hexdigest()[:40]

# μέγιστο μήκος ανά string-στήλη staging (από το ίδιο το μοντέλο) — ώστε το κόψιμο να ταιριάζει
# ΑΚΡΙΒΩΣ με τη στήλη (π.χ. CMP_NAME=160), όχι blanket 200 (που ξεχείλιζε → HTTP 500).
_STR_MAXLEN = {c.key: (getattr(c.type, 'length', None) or 255)
               for c in DatahubStagingBmisthos.__table__.columns
               if c.type.__class__.__name__ == 'String'}

def _write_staging(row, batch_id):
    """Γράφει bronze verbatim. Idempotent: αν υπάρχει row_hash → skip. Returns (rec|None, is_new)."""
    h = _row_hash(row)
    if DatahubStagingBmisthos.query.filter_by(row_hash=h).first():
        return None, False   # ήδη landed — τίποτα διπλό
    rec = DatahubStagingBmisthos(row_hash=h, batch_id=batch_id, ingested_at=datetime.now())
    rec.VAT = _s(row.get('VAT'), _STR_MAXLEN.get('VAT', 20))
    for k in _STAGING_STR:
        setattr(rec, k, _s(row.get(k), _STR_MAXLEN.get(k, 200)))
    for k in _STAGING_INT:
        setattr(rec, k, _i(row.get(k)))
    for k in _STAGING_FLOAT:
        setattr(rec, k, _f(row.get(k)))
    for k in _STAGING_DT:
        setattr(rec, k, _dt(row.get(k)))
    rec.email = _s(row.get('email'), _STR_MAXLEN.get('email', 160))
    rec.raw_json = json.dumps(row, ensure_ascii=False, default=str)
    db.session.add(rec)
    return rec, True


# ── CURATED UPSERT (κλειδί ΑΦΜ· MERGE POLICY LANDING_SCHEMA §8) ────────────────
def _company_for_row(row):
    """Company από CMP_VAT (zero-pad 9) → fallback CMP_NAME."""
    v = _afm9(row.get('CMP_VAT'))
    if v:
        c = Company.query.filter_by(vat=v).first()
        if c:
            return c
        # μερικά ΑΦΜ εταιρειών αποθηκεύονται χωρίς zero-pad
        c = Company.query.filter_by(vat=str(_i(row.get('CMP_VAT')) or '')).first()
        if c:
            return c
    return _company_from_name(row.get('CMP_NAME'))

def _upsert_identity(row, afm9):
    """EmployeePII keyed by ΑΦΜ. Νέο ΑΦΜ → auto-create locked User+EmployeePII.
    A=set (Epsilon authoritative) · B=fill-gaps (email/mobile) · C=ignore (οργανόγραμμα)."""
    created = False
    pii = EmployeePII.query.filter_by(afm=afm9).first()
    if pii:
        u = User.query.get(pii.user_id)
    else:
        u = _create_locked_employee({'epon': _s(row.get('SURNAME')) or '',
                                     'onoma': _s(row.get('NAME')) or ''})
        pii = EmployeePII.query.filter_by(user_id=u.id).first()
        if not pii:
            pii = EmployeePII(user_id=u.id); db.session.add(pii)
        pii.afm = afm9
        db.session.flush()
        created = True
    # A — Epsilon authoritative (set/overwrite)
    A = {
        'amka': _s(row.get('AM_KOIN_ASF'), 12),
        'ika_am': _s(row.get('AM_IKA'), 15),
        'last_name': _s(row.get('SURNAME'), 80),
        'first_name': _s(row.get('NAME'), 80),
        'father_name': _s(row.get('FTHRNAME'), 80),
        'ergani_specialty': _s(row.get('SPC_DESCR'), 120),
        'emp_code': _s(row.get('CODE'), 12),
        'fr_reason': _s(row.get('FR_REASON'), 40),
        'fr_reason_descr': _s(row.get('FR_REASON_DESCR'), 160),
        'hotel_seasonal': _s(row.get('HOTEL_SEASONAL'), 20),
        'lending_from': _s(row.get('LENDING_FROM'), 80),
        'lending_to': _s(row.get('LENDING_TO'), 80),
    }
    for fld, val in A.items():
        if val is not None:
            setattr(pii, fld, val)
    # παράγωγα (κείμενο) — set μόνο όταν υπάρχει τιμή πηγής
    ori = _i(row.get('ORISMENOU'))
    if ori is not None:
        pii.contract_type = ORISMENOU_TXT.get(ori)
    ek = _i(row.get('EMP_KIND'))
    if ek is not None:
        pii.employment_kind = EMP_KIND_TXT.get(ek, str(ek))
    hd = _dt(row.get('HRDATE'))
    if hd is not None:
        pii.hired_at = hd.date()
    fd = _dt(row.get('FRDATE'))
    if fd is not None:
        pii.left_at = fd.date()
    ife = _b(row.get('IS_FUTURE_EMP'))
    if ife is not None:
        pii.is_future_emp = ife
    sup = _i(row.get('SUPERVISOR'))
    if sup is not None:
        pii.supervisor_id_emp = sup
    # id_emp_current = πιο πρόσφατο επεισόδιο (max ID_EMP)
    ide = _i(row.get('ID_EMP'))
    if ide is not None and (pii.id_emp_current is None or ide > pii.id_emp_current):
        pii.id_emp_current = ide
    # B — Εστία-owned (fill-gaps only· ΠΟΤΕ overwrite μη-κενού)
    em = _s(row.get('email'), 160)
    if em and not (pii.email or '').strip():
        pii.email = em
    mob = _s(row.get('MOBILE'), 40)
    if mob and not (pii.mobile or '').strip():
        pii.mobile = mob
    # C — οργανόγραμμα (τμήμα/ξενοδοχείο/υπεύθυνος): ΔΕΝ αγγίζεται εδώ.
    pii.locked = True
    db.session.flush()
    return u, created

def _month_of(row):
    """Μήνας: από ID_PERIODOS 1-12 (μηνιαία) αλλιώς από PERIODOS_DATE."""
    idp = _i(row.get('ID_PERIODOS'))
    pt = _i(row.get('PER_TYPE'))
    if pt == 1 and idp and 1 <= idp <= 12:
        return idp
    pd = _dt(row.get('PERIODOS_DATE'))
    return pd.month if pd else None

def _grain_episodes(row):
    """Επιστρέφει τα staging επεισόδια του grain (ίδιο άτομο×εταιρεία×έτος×περίοδος×τύπος),
    ΕΝΑ ανά ID_EMP (το τελευταίο ingested — ώστε re-push ίδιου επεισοδίου να ΜΗ διπλομετρά).
    Εδώ συναντιούνται οι >1 γραμμές/μήνα (π.χ. Epsilon σπάει εκκαθαριστικό ανά επεισόδιο) → θα ΑΘΡΟΙΣΤΟΥΝ."""
    raw_vat = _s(row.get('VAT'), 20)
    q = DatahubStagingBmisthos.query.filter_by(
        VAT=raw_vat, XRISI=_i(row.get('XRISI')),
        ID_PERIODOS=_i(row.get('ID_PERIODOS')), PER_TYPE=_i(row.get('PER_TYPE')))
    idc = _i(row.get('ID_CMP'))
    if idc is not None:
        q = q.filter_by(ID_CMP=idc)
    latest = {}   # ID_EMP → τελευταίο staging record
    for s in q.order_by(DatahubStagingBmisthos.ingested_at.asc()).all():
        latest[s.ID_EMP] = s
    return list(latest.values())

def _upsert_amounts(row, afm9, u, comp):
    """LegalNetImport keyed by hash(afm, company, year, id_periodos, per_type).
    ΑΘΡΟΙΣΜΑ ανά grain (P-097/DH-06): όταν εργαζόμενος έχει >1 επεισόδιο τον ίδιο μήνα/εταιρεία,
    το curated = ΣΥΝΟΛΟ όλων των επεισοδίων (όπως το εκκαθαριστικό λογιστηρίου). Idempotent:
    ξαναϋπολογίζεται από το staging (πηγή αλήθειας), ΟΧΙ incremental → re-run δεν διπλομετρά.
    Καταβλητέο = ΣPLIROTEO − ΣPROKATAVOLI − ΣPAROXES (τύπος Epsilon)."""
    yr = _i(row.get('XRISI'))
    idp = _i(row.get('ID_PERIODOS'))
    pt = _i(row.get('PER_TYPE'))
    if not yr or idp is None:
        return None, False   # χωρίς περίοδο → δεν είναι γραμμή ποσών
    cid = comp.id if comp else 'x'
    key = 'datahub|%s|%s|%s|%s|%s' % (afm9, cid, yr, idp, pt)
    h = hashlib.sha1(key.encode('utf-8')).hexdigest()[:40]
    is_new = False
    rec = LegalNetImport.query.filter_by(import_hash=h).first()
    if not rec:
        rec = LegalNetImport(import_hash=h); db.session.add(rec); is_new = True
    # ΣΥΝΟΛΟ όλων των επεισοδίων του grain από το staging (idempotent recompute)
    eps = _grain_episodes(row)
    def S(attr):
        return round(sum((getattr(e, attr) or 0.0) for e in eps), 2)
    last = eps[-1] if eps else None   # αντιπροσωπευτικό για μη-αθροιστικά
    rec.company_id = comp.id if comp else None
    rec.user_id = u.id if u else None
    rec.year = yr
    rec.month = _month_of(row)
    rec.afm = afm9
    rec.emp_name = ((_s(row.get('SURNAME')) or '') + ' ' + (_s(row.get('NAME')) or '')).strip()
    rec.period_kind = (PER_TYPE_KIND.get(pt, 'monthly') or 'monthly')[:24]
    # ── ΑΘΡΟΙΣΤΙΚΑ ποσά (headline + verbatim επεκτάσεις) ──
    plir = S('PLIROTEO'); prok = S('PROKATAVOLI'); parx = S('PAROXES')
    rec.gross_legal = S('M_APODOXES')
    rec.efka_employee_legal = S('SKRATISEIS_ERGAZ')
    rec.fmy_legal = S('FMY')
    rec.net_legal = plir
    rec.employer_cost_legal = S('S_KOSTOS')
    rec.prosthetes_sum = S('PROSTHETES_SUM')
    rec.prosthetes_sum_nokrat = S('PROSTHETES_SUM_NOKRAT')
    rec.skratiseis_ergod = S('SKRATISEIS_ERGOD')
    rec.xartoshmo = S('XARTOSHMO')
    rec.prokatavoli = prok
    rec.paroxes = parx
    rec.s_kostos = S('S_KOSTOS')
    rec.apoz_apol_salary = S('APOZ_APOL_SALARY')
    rec.working_days = S('WORKING_DAYS')
    rec.katavliteo = round(plir - prok - parx, 2)   # καταβλητέο (τύπος Epsilon)
    # ── ΜΗ-αθροιστικά (αντιπροσωπευτικά = τελευταίο επεισόδιο / max ημ/νία) ──
    rec.salary = (last.SALARY if last else None)    # βασικός ΣΣΕ — δεν αθροίζεται
    rec.id_periodos = idp
    rec.per_type = pt
    rec.periodos_date = max((e.PERIODOS_DATE for e in eps if e.PERIODOS_DATE), default=None)
    rec.per_calculated_date = max((e.PER_CALCULATED_DATE for e in eps if e.PER_CALCULATED_DATE), default=None)
    rec.source_file = 'datahub:bmisthos'
    return rec, is_new


# ── INGEST ENDPOINT (machine — bearer token, όχι session) ─────────────────────
def _authorized():
    token = os.environ.get('DATAHUB_INGEST_TOKEN')
    if not token:
        return None   # endpoint απενεργοποιημένο μέχρι να οριστεί token
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer ') and auth[7:].strip() == token:
        return True
    return False


@app.route('/api/datahub/ingest', methods=['POST'])
def datahub_ingest():
    """Δέχεται push από τον on-prem agent. Body:
       {source, tier:'A'|'B', mode:'seed'|'live'|'manual', rows:[...]}
       Ροή ανά γραμμή: bronze staging (idempotent) → curated upsert (κλειδί ΑΦΜ) → sync_log."""
    auth = _authorized()
    if auth is None:
        return jsonify({'error': 'ingest disabled (no DATAHUB_INGEST_TOKEN)'}), 503
    if auth is False:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    source = (data.get('source') or '').strip() or 'bmisthos'
    tier = (data.get('tier') or 'B').strip().upper()[:1] or 'B'
    mode = (data.get('mode') or 'manual').strip().lower()[:10]
    rows = data.get('rows')
    if source != 'bmisthos':
        return jsonify({'error': 'unknown source (Φ1: μόνο bmisthos)'}), 400
    if not isinstance(rows, list):
        return jsonify({'error': 'rows must be a list'}), 400

    batch_id = '%s-%s-%s' % (source, datetime.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex[:8])
    started = datetime.now()
    staged = upserted = created = amounts = skipped = skipped_bronze = 0
    watermark_to = None
    status = 'ok'; err = None; first_err = None
    # ΑΝΘΕΚΤΙΚΟΤΗΤΑ ΑΝΑ ΓΡΑΜΜΗ (2 savepoints): bronze ξεχωριστά (κρατιέται πάντα — «τίποτα δεν
    # χάνεται») + curated ξεχωριστά (μόνο αυτό προσπερνιέται αν σκάσει). Μία κακή γραμμή ΔΕΝ ρίχνει batch.
    def _note_err(kind, e, row):
        nonlocal first_err
        if first_err is None:
            first_err = ('%s@%s | VAT=%s XRISI=%s IDPER=%s PERTYPE=%s: %s' % (
                type(e).__name__, kind, row.get('VAT'), row.get('XRISI'),
                row.get('ID_PERIODOS'), row.get('PER_TYPE'), str(e)))[:1800]

    for row in rows:
        if not isinstance(row, dict):
            continue
        afm9 = _afm9(row.get('VAT'))
        # 1) BRONZE — δικό του savepoint (raw, κρατιέται ακόμη κι αν το curated σκάσει)
        sp1 = db.session.begin_nested()
        try:
            _rec, is_new = _write_staging(row, batch_id)
            db.session.flush()
            sp1.commit()
            if is_new:
                staged += 1
        except Exception as e:
            try: sp1.rollback()
            except Exception: pass
            skipped_bronze += 1; _note_err('bronze', e, row)
        # 2) CURATED — δικό του savepoint
        if afm9:
            sp2 = db.session.begin_nested()
            try:
                u, was_created = _upsert_identity(row, afm9)
                r_up = 1; r_cr = 1 if was_created else 0; r_am = 0
                if tier != 'A':
                    comp = _company_for_row(row)
                    arec, _an = _upsert_amounts(row, afm9, u, comp)
                    r_am = 1 if arec is not None else 0
                db.session.flush()
                sp2.commit()
                upserted += r_up; created += r_cr; amounts += r_am
            except Exception as e:
                try: sp2.rollback()
                except Exception: pass
                skipped += 1; _note_err('curated', e, row)
                continue
        pcd = _dt(row.get('PER_CALCULATED_DATE'))
        if pcd and (watermark_to is None or pcd > watermark_to):
            watermark_to = pcd
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        status = 'error'; err = str(e)[:2000]
    if (skipped or skipped_bronze) and status == 'ok':
        err = 'skipped_curated=%d skipped_bronze=%d first=%s' % (skipped, skipped_bronze, first_err or '')

    # 3) audit sync log + control-plane update
    finished = datetime.now()
    try:
        db.session.add(DatahubSyncLog(
            batch_id=batch_id, source=source, tier=tier, mode=mode,
            started_at=started, finished_at=finished,
            rows_read=len(rows), rows_upserted=upserted,
            watermark_to=watermark_to, guard_flags='0', status=status, error=err))
        if status == 'ok':
            src = DatahubSource.query.filter_by(source=source).first()
            if src:
                src.last_sync_at = finished
                if watermark_to:
                    src.last_watermark = watermark_to
                src.refresh_requested = False   # καταναλώθηκε το «Refresh»
        db.session.commit()
    except Exception as e:
        db.session.rollback(); print('[datahub] sync_log skipped:', e)

    code = 200 if status == 'ok' else 500
    return jsonify({
        'batch_id': batch_id, 'source': source, 'tier': tier, 'mode': mode,
        'rows_read': len(rows), 'staged': staged, 'upserted': upserted,
        'created': created, 'amounts': amounts,
        'skipped': skipped, 'skipped_bronze': skipped_bronze,
        'watermark_to': watermark_to.isoformat() if watermark_to else None,
        'status': status, 'error': err,
    }), code


@app.route('/api/datahub/verify', methods=['GET'])
def datahub_verify():
    """Read-only επαλήθευση από την παραγωγή (bearer token). Επιστρέφει πλήθη + αθροίσματα
    staging & curated (+ guard flags) ώστε το prove-run να κάνει reconciliation στο live.
    Προαιρετικό ?year=YYYY για φιλτράρισμα ανά έτος. Μέρος Φ4 monitoring."""
    auth = _authorized()
    if auth is None:
        return jsonify({'error': 'ingest disabled (no DATAHUB_INGEST_TOKEN)'}), 503
    if auth is False:
        return jsonify({'error': 'unauthorized'}), 401
    from sqlalchemy import func
    year = request.args.get('year', type=int)
    ST = DatahubStagingBmisthos
    LN = LegalNetImport

    def ssum(col):
        q = db.session.query(func.coalesce(func.sum(col), 0.0))
        if year:
            q = q.filter(ST.XRISI == year)
        return round(q.scalar() or 0.0, 2)

    def csum(col):
        q = db.session.query(func.coalesce(func.sum(col), 0.0)).filter(LN.source_file == 'datahub:bmisthos')
        if year:
            q = q.filter(LN.year == year)
        return round(q.scalar() or 0.0, 2)

    sq = ST.query
    cq = LN.query.filter(LN.source_file == 'datahub:bmisthos')
    saq = db.session.query(func.count(func.distinct(ST.VAT)))
    caq = db.session.query(func.count(func.distinct(LN.afm))).filter(LN.source_file == 'datahub:bmisthos')
    if year:
        sq = sq.filter(ST.XRISI == year)
        cq = cq.filter(LN.year == year)
        saq = saq.filter(ST.XRISI == year)
        caq = caq.filter(LN.year == year)

    guard_nonzero = DatahubSyncLog.query.filter(
        DatahubSyncLog.source == 'bmisthos', DatahubSyncLog.guard_flags != '0').count()
    last = DatahubSyncLog.query.filter_by(source='bmisthos').order_by(DatahubSyncLog.id.desc()).first()
    return jsonify({
        'year': year,
        'staging': {
            'rows': sq.count(), 'distinct_afm': saq.scalar() or 0,
            'sum_M_APODOXES': ssum(ST.M_APODOXES),
            'sum_S_KOSTOS': ssum(ST.S_KOSTOS),
            'sum_PLIROTEO': ssum(ST.PLIROTEO),
        },
        'curated': {
            'rows': cq.count(), 'distinct_afm': caq.scalar() or 0,
            'sum_gross': csum(LN.gross_legal),
            'sum_employer_cost': csum(LN.employer_cost_legal),
            'sum_net': csum(LN.net_legal),
        },
        'sync': {
            'batches': DatahubSyncLog.query.filter_by(source='bmisthos').count(),
            'guard_nonzero_count': guard_nonzero,
            'last_status': last.status if last else None,
            'last_watermark': last.watermark_to.isoformat() if last and last.watermark_to else None,
            'recent_errors': [e.error for e in DatahubSyncLog.query.filter(
                DatahubSyncLog.source == 'bmisthos', DatahubSyncLog.error.isnot(None))
                .order_by(DatahubSyncLog.id.desc()).limit(5).all()],
        },
    })


@app.route('/api/datahub/purge_legacy_legal', methods=['POST'])
def datahub_purge_legacy_legal():
    """Καθαρισμός διπλών `LegalNetImport`: αφαιρεί τις ΠΑΛΙΕΣ (μη-datahub) γραμμές που το Data Hub
    **ήδη καλύπτει** (ίδιο ΑΦΜ×έτος×μήνα) → datahub = ΜΟΝΑΔΙΚΗ πηγή, σταματά το διπλομέτρημα στην κάρτα.
    Ασφάλεια: default DRY (δεν σβήνει)· κρατά όσες ΔΕΝ καλύπτονται από datahub (coverage gap).
    Body: {commit:false, dump:false}. bearer token."""
    auth = _authorized()
    if auth is None:
        return jsonify({'error': 'ingest disabled (no DATAHUB_INGEST_TOKEN)'}), 503
    if auth is False:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(silent=True) or {}
    commit = bool(data.get('commit'))
    dump = bool(data.get('dump'))
    DH = 'datahub:bmisthos'
    # κλειδιά κάλυψης datahub: (afm, year, month)
    covered = set()
    for r in db.session.query(LegalNetImport.afm, LegalNetImport.year, LegalNetImport.month).filter(
            LegalNetImport.source_file == DH).all():
        covered.add((r[0], r[1], r[2]))
    legacy = LegalNetImport.query.filter(
        (LegalNetImport.source_file.is_(None)) | (LegalNetImport.source_file != DH)).all()
    to_delete, kept = [], []
    for li in legacy:
        if (li.afm, li.year, li.month) in covered:
            to_delete.append(li)
        else:
            kept.append(li)
    by_year = {}
    for li in to_delete:
        by_year[li.year] = by_year.get(li.year, 0) + 1
    resp = {
        'mode': 'commit' if commit else 'dry',
        'legacy_total': len(legacy),
        'would_delete': len(to_delete),
        'kept_no_coverage': len(kept),
        'delete_by_year': {str(k): v for k, v in sorted(by_year.items(), key=lambda x: (x[0] or 0))},
        'kept_sample': [{'id': li.id, 'afm': li.afm, 'year': li.year, 'month': li.month,
                         'net': li.net_legal, 'src': li.source_file} for li in kept[:50]],
    }
    if dump:
        resp['deleted_rows'] = [{'id': li.id, 'afm': li.afm, 'year': li.year, 'month': li.month,
                                 'period_kind': li.period_kind, 'net_legal': li.net_legal,
                                 'gross_legal': li.gross_legal, 'employer_cost_legal': li.employer_cost_legal,
                                 'source_file': li.source_file} for li in to_delete]
    if commit:
        n = 0
        for li in to_delete:
            db.session.delete(li); n += 1
        db.session.commit()
        resp['deleted'] = n
    return jsonify(resp)


# ══════════════════════════════════════════════════════════════════════════════
# ΟΘΟΝΗ «Business Μισθοδοσία» — Επιθεώρηση σύνδεσης Epsilon (DH-04, read-only)
# Το ΠΡΩΤΟ σημείο ελέγχου: «τι έφτασε ολόκληρο από την Epsilon» χωρίς κατέβασμα Excel.
# Διαβάζει ΜΟΝΟ το bronze staging (raw_json = όλα τα πεδία verbatim). Admin-gated.
# ══════════════════════════════════════════════════════════════════════════════

# Ελληνικές ετικέτες για τα modeled πεδία (τα υπόλοιπα raw εμφανίζονται ως «Λοιπά»).
FIELD_LABELS = {
    'VAT': 'ΑΦΜ', 'CODE': 'Κωδικός εργαζομένου', 'SURNAME': 'Επώνυμο', 'NAME': 'Όνομα',
    'FTHRNAME': 'Πατρώνυμο', 'AM_IKA': 'ΑΜ ΙΚΑ', 'AM_KOIN_ASF': 'ΑΜΚΑ', 'email': 'Email',
    'MOBILE': 'Κινητό', 'HRDATE': 'Ημ. πρόσληψης', 'FRDATE': 'Ημ. αποχώρησης',
    'FR_REASON': 'Κωδ. λόγου αποχώρησης', 'FR_REASON_DESCR': 'Λόγος αποχώρησης',
    'IS_FUTURE_EMP': 'Μελλοντικός εργαζόμενος', 'HOTEL_SEASONAL': 'Εποχικό ξενοδοχείο',
    'SUPERVISOR': 'Υπεύθυνος (ID)', 'LENDING_FROM': 'Δανεισμός από', 'LENDING_TO': 'Δανεισμός προς',
    'ID_CMP': 'ID εταιρείας', 'CMP_NAME': 'Εταιρεία', 'CMP_VAT': 'ΑΦΜ εταιρείας',
    'CMP_CODE': 'Κωδ. εταιρείας', 'COD_YPOKAT': 'Κωδ. υποκαταστήματος', 'YPOKAT_DESCR': 'Υποκατάστημα',
    'TMHMA': 'Τμήμα', 'ID_ADMINISTRATION': 'Διαβάθμιση (ID)', 'ID_ADMINISTRATION_SUB': 'Υπο-διαβάθμιση (ID)',
    'XRISI': 'Χρήση (έτος)', 'ID_PERIODOS': 'Περίοδος (αρ.)', 'PERIODOS_DESCR': 'Περιγραφή περιόδου',
    'PER_TYPE': 'Τύπος περιόδου', 'PERIODOS_DATE': 'Ημ. περιόδου', 'SPC_DESCR': 'Ειδικότητα',
    'CNDTDESCR': 'Σύμβαση / όροι', 'EMP_KIND': 'Είδος μισθωτού', 'MERIKH_APASX': 'Μερική απασχόληση',
    'ORISMENOU': 'Ορισμένου / Αορίστου', 'PAY_TYPE': 'Τρόπος πληρωμής', 'WORKING_DAYS': 'Ημέρες εργασίας',
    'PER_CALCULATED_DATE': 'Ημ. υπολογισμού', 'SALARY': 'Βασικός μισθός', 'M_APODOXES': 'Μικτές αποδοχές',
    'PROSTHETES_SUM': 'Πρόσθετες αποδοχές', 'PROSTHETES_SUM_NOKRAT': 'Πρόσθετες (χωρίς κρατήσεις)',
    'SKRATISEIS_ERGAZ': 'Κρατήσεις εργαζομένου (ΕΦΚΑ)', 'SKRATISEIS_ERGOD': 'Κρατήσεις εργοδότη',
    'FMY': 'ΦΜΥ', 'XARTOSHMO': 'Χαρτόσημο', 'PROKATAVOLI': 'Προκαταβολή', 'PAROXES': 'Παροχές',
    'PLIROTEO': 'Πληρωτέο (καθαρό)', 'S_KOSTOS': 'Συνολικό κόστος εργοδότη',
    'APOZ_APOL_SALARY': 'Αποζημίωση απόλυσης',
}
# Ομαδοποίηση εμφάνισης (σειρά + τίτλοι group)
FIELD_GROUPS = [
    ('Ταυτότητα εργαζομένου', ['VAT', 'CODE', 'SURNAME', 'NAME', 'FTHRNAME', 'AM_IKA', 'AM_KOIN_ASF',
        'email', 'MOBILE', 'HRDATE', 'FRDATE', 'FR_REASON', 'FR_REASON_DESCR', 'IS_FUTURE_EMP',
        'HOTEL_SEASONAL', 'SUPERVISOR', 'LENDING_FROM', 'LENDING_TO']),
    ('Εταιρεία / Οργάνωση', ['ID_CMP', 'CMP_NAME', 'CMP_VAT', 'CMP_CODE', 'COD_YPOKAT', 'YPOKAT_DESCR',
        'TMHMA', 'ID_ADMINISTRATION', 'ID_ADMINISTRATION_SUB']),
    ('Περίοδος / Σύμβαση', ['XRISI', 'ID_PERIODOS', 'PERIODOS_DESCR', 'PER_TYPE', 'PERIODOS_DATE',
        'SPC_DESCR', 'CNDTDESCR', 'EMP_KIND', 'MERIKH_APASX', 'ORISMENOU', 'PAY_TYPE', 'WORKING_DAYS',
        'PER_CALCULATED_DATE']),
    ('Ποσά (αποδοχές / κρατήσεις / κόστος)', ['SALARY', 'M_APODOXES', 'PROSTHETES_SUM',
        'PROSTHETES_SUM_NOKRAT', 'SKRATISEIS_ERGAZ', 'SKRATISEIS_ERGOD', 'FMY', 'XARTOSHMO',
        'PROKATAVOLI', 'PAROXES', 'PLIROTEO', 'S_KOSTOS', 'APOZ_APOL_SALARY']),
]
_KNOWN_KEYS = set()
for _t, _ks in FIELD_GROUPS:
    _KNOWN_KEYS.update(_ks)

# ── Προορισμός κάθε πεδίου Epsilon στην Εστία (σπόρος = ό,τι γράφει ΣΗΜΕΡΑ το curated).
# Λείπει/None → «διαθέσιμο». Μεγαλώνει σιγά-σιγά καθώς καλωδιώνουμε νέα πεδία.
FIELD_DEST = {
    # Ταυτότητα → EmployeePII (καρτέλα εργαζομένου)
    'VAT': 'Μητρώο › ΑΦΜ', 'SURNAME': 'Καρτέλα › Επώνυμο', 'NAME': 'Καρτέλα › Όνομα',
    'FTHRNAME': 'Καρτέλα › Πατρώνυμο', 'AM_KOIN_ASF': 'Καρτέλα › ΑΜΚΑ', 'AM_IKA': 'Καρτέλα › ΑΜ ΙΚΑ',
    'CODE': 'Καρτέλα › Κωδικός', 'SPC_DESCR': 'Καρτέλα › Ειδικότητα',
    'HRDATE': 'Καρτέλα › Ημ. πρόσληψης', 'FRDATE': 'Καρτέλα › Ημ. αποχώρησης',
    'EMP_KIND': 'Καρτέλα › Είδος μισθωτού', 'ORISMENOU': 'Καρτέλα › Τύπος σύμβασης',
    'FR_REASON': 'Καρτέλα › Λόγος αποχώρησης', 'FR_REASON_DESCR': 'Καρτέλα › Λόγος αποχώρησης',
    'HOTEL_SEASONAL': 'Καρτέλα › Εποχικό', 'LENDING_FROM': 'Καρτέλα › Δανεισμός από',
    'LENDING_TO': 'Καρτέλα › Δανεισμός προς', 'SUPERVISOR': 'Καρτέλα › Υπεύθυνος',
    'IS_FUTURE_EMP': 'Καρτέλα › Μελλοντικός', 'ID_EMP': 'Καρτέλα › Τρέχον ID',
    'email': 'Καρτέλα › Email (μόνο αν λείπει)', 'MOBILE': 'Καρτέλα › Κινητό (μόνο αν λείπει)',
    # Ποσά/περίοδος → LegalNetImport (Μισθοδοσία «Λογιστήριο»)
    'M_APODOXES': 'Μισθοδοσία › Μικτές', 'PLIROTEO': 'Μισθοδοσία › Καθαρό',
    'S_KOSTOS': 'Μισθοδοσία › Κόστος εργοδότη', 'SKRATISEIS_ERGAZ': 'Μισθοδοσία › ΕΦΚΑ εργαζ.',
    'SKRATISEIS_ERGOD': 'Μισθοδοσία › Εισφορές εργοδ.', 'FMY': 'Μισθοδοσία › ΦΜΥ',
    'XARTOSHMO': 'Μισθοδοσία › Χαρτόσημο', 'PROSTHETES_SUM': 'Μισθοδοσία › Πρόσθετες',
    'PROSTHETES_SUM_NOKRAT': 'Μισθοδοσία › Πρόσθετες (χωρ. κρατ.)', 'PROKATAVOLI': 'Μισθοδοσία › Προκαταβολή',
    'PAROXES': 'Μισθοδοσία › Παροχές', 'APOZ_APOL_SALARY': 'Μισθοδοσία › Αποζημ. απόλυσης',
    'SALARY': 'Μισθοδοσία › Βασικός', 'WORKING_DAYS': 'Μισθοδοσία › Ημέρες',
    'XRISI': 'Μισθοδοσία › Έτος', 'ID_PERIODOS': 'Μισθοδοσία › Περίοδος', 'PER_TYPE': 'Μισθοδοσία › Τύπος',
    'PERIODOS_DATE': 'Μισθοδοσία › Ημ. περιόδου', 'PER_CALCULATED_DATE': 'Μισθοδοσία › Ημ. υπολογισμού',
}
# Κατηγοριοποίηση περιόδων (αριστερή στήλη hub) ανά PER_TYPE
PERIOD_CATS = [
    ('Μηνιαίες', {1}),
    ('Δώρα / Επιδόματα', {2, 3, 4, 5}),
    ('Εκκαθαρίσεις / Αναδρομικά', {6, 7, 8, 9}),
    ('Λοιπά', None),   # ό,τι δεν έπεσε παραπάνω
]
# Ποια group πάει πού: 'header' = σταθερή κεφαλίδα (ΑΦΜ/όνομα κ.λπ., όχι στο detail)·
# 'period' = μέσα στην ανάλυση μήνα (Εταιρεία/Οργάνωση εδώ γιατί αλλάζει ανά περίοδο).
GROUP_TAB = {
    'Ταυτότητα εργαζομένου': 'header',
    'Εταιρεία / Οργάνωση': 'period',
    'Περίοδος / Σύμβαση': 'period',
    'Ποσά (αποδοχές / κρατήσεις / κόστος)': 'period',
}
# hero (μικρό, δευτερεύον) — τα ποσά-κλειδιά
HERO_TILES = [('Μικτές', 'M_APODOXES'), ('Πρόσθετες', 'PROSTHETES_SUM'), ('ΕΦΚΑ εργαζ.', 'SKRATISEIS_ERGAZ'),
              ('ΦΜΥ', 'FMY'), ('Πληρωτέο', 'PLIROTEO'), ('Κόστος εργοδ.', 'S_KOSTOS')]
HERO_ACCENT = 'PLIROTEO'
# «Βασικά» view — τι δείχνει το default (τα υπόλοιπα με «Όλα»)
BASIC_FIELDS = {'VAT', 'CODE', 'SURNAME', 'NAME', 'FTHRNAME', 'AM_KOIN_ASF', 'AM_IKA', 'SPC_DESCR',
                'HRDATE', 'FRDATE', 'EMP_KIND', 'ORISMENOU', 'CMP_NAME', 'TMHMA', 'YPOKAT_DESCR',
                'XRISI', 'ID_PERIODOS', 'PERIODOS_DESCR', 'PER_TYPE', 'WORKING_DAYS',
                'M_APODOXES', 'PROSTHETES_SUM', 'SKRATISEIS_ERGAZ', 'SKRATISEIS_ERGOD', 'FMY',
                'PROKATAVOLI', 'PAROXES', 'PLIROTEO', 'S_KOSTOS'}


@app.route('/dashboard/payroll/epsilon')
def datahub_epsilon_inspect():
    """Read-only επιθεώρηση: τι φέρνει η σύνδεση Epsilon (bronze staging).
    3 καταστάσεις σε μία σελίδα: αναζήτηση → περίοδοι εργαζομένου → πλήρη πεδία περιόδου."""
    from payroll import _padmin
    if not _padmin():
        return redirect(url_for('login'))
    from sqlalchemy import func
    ST = DatahubStagingBmisthos
    vat = (request.args.get('vat') or '').strip()
    row_id = request.args.get('row', type=int)
    year = request.args.get('year', type=int)
    show_test = request.args.get('test') == '1'   # παρκαρισμένες «δοκιμαστικές» (χρήση 0/κενή)

    # «Δοκιμαστικές εγγραφές» = XRISI 0 ή κενό: το λογιστήριο δεν τις βλέπει στη μισθοδοσία.
    # Δεν εμφανίζονται εδώ (κρατιούνται στο bronze)· προσβάσιμες με ?test=1.
    def _scope(q):
        if show_test:
            return q.filter(db.or_(ST.XRISI.is_(None), ST.XRISI == 0))
        return q.filter(ST.XRISI.isnot(None), ST.XRISI != 0)

    # διαθέσιμες χρήσεις (έτη) — εκτός 0/κενό· default = πιο πρόσφατη
    years = [int(y[0]) for y in db.session.query(ST.XRISI)
             .filter(ST.XRISI.isnot(None), ST.XRISI != 0).distinct().order_by(ST.XRISI.desc()).all()]
    if year is None and years:
        year = years[0]
    test_rows = db.session.query(func.count(ST.id)).filter(
        db.or_(ST.XRISI.is_(None), ST.XRISI == 0)).scalar() or 0

    src = DatahubSource.query.filter_by(source='bmisthos').first()
    last = DatahubSyncLog.query.filter_by(source='bmisthos').order_by(DatahubSyncLog.id.desc()).first()
    status = {
        'total_rows': ST.query.count(),
        'distinct_afm': db.session.query(func.count(func.distinct(ST.VAT))).scalar() or 0,
        'last_sync_at': (src.last_sync_at if src else None),
        'last_watermark': (src.last_watermark if src else None),
        'last_status': (last.status if last else None),
    }

    people, periods, rec, groups, extra, hero, period_cats, hdr = [], [], None, None, None, None, [], None
    if vat or row_id:
        # ── HUB εργαζομένου: σταθερή κεφαλίδα + ΟΛΕΣ οι χρήσεις (φίλτρο client-side) ──
        rec0 = ST.query.get(row_id) if row_id else None
        if rec0 is not None and not vat:
            vat = rec0.VAT
        # ΜΙΑ γραμμή ανά περίοδο (dedup), ΟΛΕΣ οι χρήσεις
        allp = _scope(ST.query.filter_by(VAT=vat)).order_by(ST.ingested_at.asc()).all()
        dd = {}
        for p in allp:
            dd[(p.ID_CMP, p.XRISI, p.ID_PERIODOS, p.PER_TYPE, p.ID_EMP)] = p
        periods = sorted(dd.values(),
                         key=lambda p: (p.XRISI or 0, p.ID_PERIODOS or 0, p.PER_TYPE or 0), reverse=True)
        # χρήσεις του εργαζομένου (για τον selector)
        emp_years = sorted({p.XRISI for p in periods if p.XRISI}, reverse=True)
        if emp_years:
            years = emp_years
        # κατηγορίες (όλες οι χρήσεις μαζί· φιλτράρονται client-side ανά έτος)
        used = set()
        for title, types in PERIOD_CATS:
            if types is None:
                items = [p for p in periods if id(p) not in used]
            else:
                items = [p for p in periods if p.PER_TYPE in types]
                used.update(id(p) for p in items)
            if items:
                period_cats.append({'title': title, 'items': items})
        # επιλεγμένη περίοδος = row_id ή η πιο πρόσφατη· προεπιλεγμένη χρήση = της επιλεγμένης
        rec = rec0 or (periods[0] if periods else None)
        if rec is not None and rec.XRISI:
            year = rec.XRISI
        if rec is not None:
            try:
                raw = json.loads(rec.raw_json) if rec.raw_json else {}
            except Exception:
                raw = {}

            def _val(k):
                v = raw.get(k, None)
                return v if v is not None else getattr(rec, k, None)

            def _frow(k, v):
                empty = v is None or (isinstance(v, str) and v.strip() == '')
                return {'label': FIELD_LABELS.get(k, k), 'key': k, 'value': v,
                        'dest': FIELD_DEST.get(k), 'basic': k in BASIC_FIELDS, 'empty': empty}
            groups = [{'title': gt, 'tab': GROUP_TAB.get(gt, 'period'),
                       'rows': [_frow(k, _val(k)) for k in keys]} for gt, keys in FIELD_GROUPS]
            extra = sorted((_frow(k, v) for k, v in raw.items()
                            if k not in _KNOWN_KEYS and k != 'raw_json'),
                           key=lambda d: d['key'])
            hero = [{'label': lbl, 'value': _val(k), 'accent': (k == HERO_ACCENT)}
                    for lbl, k in HERO_TILES]

            # ── ΚΕΦΑΛΙΔΑ (σταθερά) + heuristic email/IBAN (αυτο-εντοπισμός στηλών) ──
            def _multi(needle):
                out = []
                for k in sorted(raw.keys()):
                    if needle in k.upper():
                        v = raw.get(k)
                        if v not in (None, '') and str(v) not in out:
                            out.append(str(v))
                return out
            hdr = {'name': ((_val('SURNAME') or '') + ' ' + (_val('NAME') or '')).strip(),
                   'vat': vat, 'amka': _val('AM_KOIN_ASF'), 'ika': _val('AM_IKA'),
                   'code': _val('CODE'), 'spc': _val('SPC_DESCR'),
                   'emails': _multi('MAIL'), 'ibans': _multi('IBAN')}
    else:
        # ── ΛΙΣΤΑ όλων των εργαζομένων (distinct ΑΦΜ), φίλτρο χρήσης + client-side search ──
        pq = _scope(db.session.query(ST.VAT, func.max(ST.SURNAME), func.max(ST.NAME),
                                     func.max(ST.CODE)).filter(ST.VAT.isnot(None)))
        if year and not show_test:
            pq = pq.filter(ST.XRISI == year)
        rows = pq.group_by(ST.VAT).all()
        people = sorted(({'vat': r[0], 'name': ((r[1] or '') + ' ' + (r[2] or '')).strip(),
                          'code': r[3]} for r in rows), key=lambda d: d['name'])

    return render_template('datahub_epsilon.html', vat=vat, year=year, years=years, status=status,
                           people=people, periods=periods, period_cats=period_cats, rec=rec, hdr=hdr,
                           groups=groups, extra=extra, hero=hero, per_type_kind=PER_TYPE_KIND,
                           show_test=show_test, test_rows=test_rows)
