# -*- coding: utf-8 -*-
"""
Εστία — Module «Πρόγραμμα Εργασίας» (Βάρδιες) — Φάση 1 (v12.40)
==============================================================
Plug-in: `import schedule` από το ΤΕΛΟΣ του app.py (αφού οριστούν app/db/helpers,
ΠΡΙΝ το init_db() ώστε το create_all να πιάσει τους νέους πίνακες).
Spec: 02_MODULES_ESTIA/ΠΡΟΓΡΑΜΜΑ_ΕΡΓΑΣΙΑΣ/00_SPEC.md

Αρχές:
 - Κάθε εργαζόμενος = User (login_enabled=false για το μαζικό προσωπικό).
 - Τμήματα οργανισμού-wide· ξενοδοχείο = ξεχωριστή διάσταση (home_hotel_id).
 - Κωδικολόγιο μισθοδοσίας (8 κωδικοί) + μηχανή ωρών (8.5 normal, έξτρα, σπαστή, νυχτερινή).
 - Workflow υποβολής: WeekPlan(τμήμα) -> ScheduleSubmission(ενοποιημένη/ξενοδοχείο),
   κανόνες (R1 ≥1 ρεπό/εβδ.), χρονικά κλειδώματα (Πέμπτη), versions + diff.
"""
import os, re, json, unicodedata, threading
from datetime import datetime, date, timedelta, time as dtime
from flask import request, redirect, url_for, render_template, session, jsonify, Response
from app import (app, db, current_user, is_admin, allowed_hotels, notify, notify_admins,
                 log_activity, Hotel, User, Setting, ROLE_RANK, role_rank, BASE_DIR,
                 send_email, EMAIL_TO_LIST, active_hotel_id)
from werkzeug.security import generate_password_hash

# ── Σταθερές μηχανής ──────────────────────────────────────────────────────────
NORMAL_HOURS = 8.5          # κανονικό ωράριο/μέρα (περιλαμβάνει 30' διάλειμμα)
HOTEL_CODES  = {'AST', 'CNT', 'SRG', 'PSV', 'PLM', 'IRO', 'CND', 'ΗΡΩ'}
HOTEL_NORM   = {'ΗΡΩ': 'IRO'}

# Κωδικολόγιο βαρδιών (από το σύστημα μισθοδοσίας — seed στο ShiftType)
SHIFT_CODES = [
    # code,  label,                 color,     counts_as_work, note, ergani
    ('ΕΡΓ',   'Εργασία',             '#16a34a', True,  'έξτρα = διάρκεια − 8,5', 'WORK'),
    ('ΑΝ',    'Ρεπό',                '#185FA5', False, 'ρεπό/εβδομάδα',          'OFF'),
    ('ΑΔ',    'Κανονική άδεια',      '#64748b', False, 'το βγάζει το λογιστήριο','LEAVE'),
    ('ΑΣΘ',   'Αναρρωτική',          '#0e9f6e', False, 'το βγάζει το λογιστήριο','SICK'),
    ('ΑΠ',    'Αδικαιολόγητος απών', '#dc2626', False, '—',                      'ABSENT'),
    ('ΑΡΓ',   'Αργία (ρεπό αργίας)', '#7e22ce', False, 'αν δουλέψει → ΕΡΓ',      'HOLIDAY'),
    ('ΑΝΕΥ',  'Άνευ αποδοχών',       '#ea580c', False, 'το βγάζει το λογιστήριο','UNPAID'),
    ('Ειδ.Α', 'Ειδική άδεια',        '#0891b2', False, 'το βγάζει το λογιστήριο','SPECIAL'),
]

# Κανονικά τμήματα (οργανισμού-wide) + aliases (καθαρισμός Ελλ/Αγγλ διπλών)
DEPARTMENTS = [
    ('Housekeeping',  'Housekeeping', '#0ea5e9', ['housekeeping', 'hk']),
    ('Reception',     'Reception',    '#6366f1', ['reception', 'ρεσεψιον', 'υποδοχη']),
    ('Service',       'Service',      '#f59e0b', ['service', 'σερβις']),
    ('Kitchen',       'Kitchen',      '#ef4444', ['kitchen', 'κουζινα']),
    ('Maintenance',   'Maintenance',  '#64748b', ['maintenance', 'συντηρηση']),
    ('Management',    'Management',   '#7e22ce', ['management', 'διοικηση', 'operations']),
    ('Pool Bar',      'Pool Bar',     '#06b6d4', ['poolbar', 'pool bar', 'pool']),
    ('Bar',           'Bar',          '#0891b2', ['bar', 'μπαρ', 'barman']),
    ('Restaurant',    'Restaurant',   '#d97706', ['restaurant', 'oliva', 'μπουφε']),
    ("Kid's Club",    "Kid's Club",   '#ec4899', ["kid's club", 'kids club', 'kidsclub']),
    ('Bellboy',       'Bellboy',      '#0d9488', ['bellboy', 'γκρουμ', 'groom']),
    ('Replacement',   'Replacement',  '#94a3b8', ['replacement', 'replacant', 'replacant']),
]

WEEKDAYS_EL = ['Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
DOW_EL = {0: 'Δευτέρα', 1: 'Τρίτη', 2: 'Τετάρτη', 3: 'Πέμπτη', 4: 'Παρασκευή', 5: 'Σάββατο', 6: 'Κυριακή'}
MONTHS_EL = ['', 'Ιανουάριος', 'Φεβρουάριος', 'Μάρτιος', 'Απρίλιος', 'Μάιος', 'Ιούνιος',
             'Ιούλιος', 'Αύγουστος', 'Σεπτέμβριος', 'Οκτώβριος', 'Νοέμβριος', 'Δεκέμβριος']

WP_STATUS = ('draft', 'ready', 'submitted', 'locked')
WP_LABELS  = {'draft': 'Πρόχειρο', 'ready': 'Έτοιμο', 'submitted': 'Υποβλήθηκε', 'locked': 'Κλειδωμένο'}


# ── Normalization helpers ─────────────────────────────────────────────────────
def _acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')

def _norm(s):
    return re.sub(r'[^a-zα-ω0-9]', '', _acc(s).strip().lower()) if s else ''

def monday_of(d):
    """Δευτέρα της εβδομάδας που περιέχει το d."""
    return d - timedelta(days=d.weekday())


# ── ΜΟΝΤΕΛΑ ───────────────────────────────────────────────────────────────────
class Department(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(60), unique=True, nullable=False)
    name_en   = db.Column(db.String(60))
    color     = db.Column(db.String(9), default='#64748b')
    aliases   = db.Column(db.Text)            # JSON list κανονικοποιημένων aliases
    active    = db.Column(db.Boolean, default=True)
    sort      = db.Column(db.Integer, default=0)

class ShiftType(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(12), unique=True, nullable=False)
    label         = db.Column(db.String(60))
    color         = db.Column(db.String(9), default='#64748b')
    default_start = db.Column(db.String(5))   # 'HH:MM'
    default_end   = db.Column(db.String(5))
    counts_as_work= db.Column(db.Boolean, default=False)
    payroll_note  = db.Column(db.String(120))
    ergani_type   = db.Column(db.String(16))
    active        = db.Column(db.Boolean, default=True)
    sort          = db.Column(db.Integer, default=0)

class EmploymentProfile(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    agreement_amount= db.Column(db.Float)               # συμφωνημένο μηνιαίο ποσό
    days_per_month  = db.Column(db.Integer, default=26)
    hours_per_day   = db.Column(db.Float, default=8.0)
    agreement_type  = db.Column(db.String(20), default='Μηνιαίος')   # Μηνιαίος/Management/Ωρομίσθιος
    position        = db.Column(db.String(80))          # θέση/ειδικότητα
    hired_at        = db.Column(db.Date)
    left_at         = db.Column(db.Date)
    status          = db.Column(db.String(20), default='Ενεργός')

    @property
    def day_wage(self):
        try:
            return round(self.agreement_amount / (self.days_per_month or 26), 4) if self.agreement_amount else 0.0
        except Exception:
            return 0.0
    @property
    def hour_wage(self):
        dw = self.day_wage
        return round(dw / 8.0, 4) if dw else 0.0

class ShiftAssignment(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    work_date     = db.Column(db.Date, nullable=False, index=True)
    shift_code    = db.Column(db.String(12), default='ΕΡΓ')     # κωδικός ShiftType
    segments      = db.Column(db.Text)            # JSON [{'start':'07:00','end':'15:30'}, ...]
    work_hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'))   # != home αν δανεικός
    note          = db.Column(db.String(200))
    created_by    = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at    = db.Column(db.DateTime, default=datetime.now)
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    import_hash   = db.Column(db.String(40), index=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'work_date', name='uq_user_date'),)

class NameLink(db.Model):
    """Επιβεβαιωμενη συνδεση ονοματος προγραμματος -> master προφιλ.
    Αγκυρωνεται στο master (που κουβαλα τον αριθμο E0xxx + ΑΦΜ). Το φτιαχνει ΜΟΝΟ ο χρηστης."""
    id         = db.Column(db.Integer, primary_key=True)
    norm_name  = db.Column(db.String(120), unique=True, index=True, nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    raw_name   = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class PendingShift(db.Model):
    """Προθαλαμος ταυτοποιησης: βαρδιες ονοματων ΧΩΡΙΣ επιβεβαιωμενη συνδεση.
    ΔΕΝ φτιαχνεται User -> δεν μπαινουν πουθενα στην πλατφορμα μεχρι να τα ταυτοποιησεις."""
    id            = db.Column(db.Integer, primary_key=True)
    norm_name     = db.Column(db.String(120), index=True, nullable=False)
    raw_name      = db.Column(db.String(120))
    epon          = db.Column(db.String(80))
    onoma         = db.Column(db.String(80))
    hotel_tag     = db.Column(db.String(20))    # upok raw
    dept_raw      = db.Column(db.String(120))
    employer      = db.Column(db.String(120))
    work_date     = db.Column(db.Date, index=True)
    shift_code    = db.Column(db.String(12))
    segments      = db.Column(db.Text)
    work_hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'))
    import_hash   = db.Column(db.String(40), index=True)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    created_by    = db.Column(db.Integer, db.ForeignKey('user.id'))
    __table_args__ = (db.UniqueConstraint('norm_name', 'work_date', name='uq_pending_name_date'),)

class Holiday(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    hol_date    = db.Column(db.Date, unique=True, nullable=False)
    description = db.Column(db.String(120))
    year        = db.Column(db.Integer, index=True)

class ScheduleRule(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200))
    severity    = db.Column(db.String(8), default='block')   # block | warn
    params      = db.Column(db.Text)            # JSON
    active      = db.Column(db.Boolean, default=True)

class WeekPlan(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False, index=True)
    week_start    = db.Column(db.Date, nullable=False, index=True)   # Δευτέρα
    status        = db.Column(db.String(12), default='draft')
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by    = db.Column(db.Integer, db.ForeignKey('user.id'))
    __table_args__ = (db.UniqueConstraint('hotel_id', 'department_id', 'week_start', name='uq_weekplan'),)

class ScheduleSubmission(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False, index=True)
    week_start    = db.Column(db.Date, nullable=False, index=True)
    version       = db.Column(db.Integer, default=1)
    parent_version= db.Column(db.Integer)
    status        = db.Column(db.String(12), default='submitted')
    snapshot      = db.Column(db.Text)          # JSON: τι ακριβώς δηλώθηκε
    changes       = db.Column(db.Text)          # JSON diff από parent_version
    submitted_at  = db.Column(db.DateTime, default=datetime.now)
    submitted_by  = db.Column(db.Integer, db.ForeignKey('user.id'))


# ── MIGRATION (στήλες User) ───────────────────────────────────────────────────
def ensure_schedule_columns():
    """Auto-migration: νέες στήλες στον User (μη καταστροφικό, race-safe μέσω app._add_col)."""
    try:
        from app import _add_col
    except Exception:
        return
    with app.app_context():
        _add_col('user', 'department_id',     'department_id INTEGER')
        _add_col('user', 'employer',          'employer VARCHAR(120)')
        _add_col('user', 'subunit',           'subunit VARCHAR(20)')
        _add_col('user', 'home_hotel_id',     'home_hotel_id INTEGER')
        _add_col('user', 'login_enabled',     'login_enabled BOOLEAN')
        _add_col('user', 'employment_active', 'employment_active BOOLEAN')


# ── ΜΗΧΑΝΗ ΩΡΩΝ ───────────────────────────────────────────────────────────────
_RANGE_RE = re.compile(r'(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})')

def segments_hours(segments):
    """segments: list[{'start':'HH:MM','end':'HH:MM'}] -> συνολικές ώρες (νυχτερινή->ίδια μέρα)."""
    tot = 0.0
    for seg in (segments or []):
        try:
            sh, sm = [int(x) for x in str(seg['start']).split(':')]
            eh, em = [int(x) for x in str(seg['end']).split(':')]
        except Exception:
            continue
        a = sh * 60 + sm
        b = eh * 60 + em
        if b <= a:
            b += 1440           # περνά μεσάνυχτα -> μετρά στη μέρα έναρξης
        tot += (b - a) / 60.0
    return round(tot, 4)

def extra_hours(total):
    return round(max(0.0, total - NORMAL_HOURS), 4) if total and total > 0 else 0.0

# v12.118 — Διάλειμμα: 30' αφαιρούνται από τις πληρωτέες ώρες ΜΟΝΟ σε βάρδιες ≥6ω παρουσίας.
BREAK_HOURS = 0.5
BREAK_MIN_PRESENCE = 6.0
def shift_break(presence):
    return BREAK_HOURS if (presence and presence >= BREAK_MIN_PRESENCE) else 0.0
def worked_hours(a):
    """Πληρωτέες ώρες = παρουσία − διάλειμμα (30' αν παρουσία ≥6ω). Σε σπαστή το κενό
    είναι ήδη εκτός (segments_hours) ΚΑΙ αφαιρείται επιπλέον 30' εφόσον σύνολο ≥6ω."""
    p = assignment_hours(a)
    return round(max(0.0, p - shift_break(p)), 4)

# v12.119 — Επιτρεπτοί κωδικοί καταχώρησης (ρυθμιζόμενο από Πρόγραμμα·Ρυθμίσεις).
def _entry_codes_setting():
    row = Setting.query.get('sched_entry_codes')
    if row and row.value:
        try:
            vals = [c for c in json.loads(row.value) if c]
            return vals or None
        except Exception:
            pass
    return None  # None = όλοι οι ενεργοί κωδικοί
def entry_shift_types():
    sts = ShiftType.query.filter_by(active=True).order_by(ShiftType.sort).all()
    allow = _entry_codes_setting()
    if allow is not None:
        sts = [s for s in sts if s.code in allow]
    return sts

def parse_cell(v):
    """Κελί Excel -> (shift_code, segments[list], work_hotel_tag).
    Πιστή μεταφορά λογικής ENGINE_v2: τμήματα ΕΡΓ, κωδικοί, cross-hotel tag."""
    if v is None:
        return (None, [], None)
    s = str(v).strip()
    if not s:
        return (None, [], None)
    tag = None
    m = re.match(r'^\s*(AST|CNT|SRG|PSV|PLM|IRO|CND|ΗΡΩ)\b\s*[-: ]*\s*(.*)$', s, re.I)
    if m and (m.group(2).strip() == '' or 'ΕΡΓ' in m.group(2).upper() or _RANGE_RE.search(m.group(2))):
        tag = HOTEL_NORM.get(m.group(1).upper(), m.group(1).upper())
        s = m.group(2).strip()
    up = _acc(s).upper()
    ranges = _RANGE_RE.findall(s)
    if ranges or 'ΕΡΓ' in up or (tag is not None and s):
        segs = [{'start': f'{int(h1):02d}:{m1}', 'end': f'{int(h2):02d}:{m2}'} for h1, m1, h2, m2 in ranges]
        return ('ΕΡΓ', segs, tag)
    # κωδικοί χωρίς ώρες (σειρά: ειδικοί πριν τα γενικά)
    for c in ['ΑΣΘ', 'ΑΝΕΥ', 'ΑΡΓ', 'ΕΙΔ', 'ΑΔ', 'ΑΠ', 'ΑΑ', 'ΑΝ']:
        if up.startswith(_acc(c).upper()):
            return ({'ΕΙΔ': 'Ειδ.Α', 'ΑΑ': 'ΑΠ'}.get(c, c), [], None)
    return (None, [], None)   # άγνωστο -> αγνοείται

def assignment_hours(a):
    try:
        segs = json.loads(a.segments) if a.segments else []
    except Exception:
        segs = []
    return segments_hours(segs)

def is_work_code(code):
    st = ShiftType.query.filter_by(code=code).first()
    if st:
        return bool(st.counts_as_work)
    return code == 'ΕΡΓ'

def aggregate(assignments, home_hotel_id=None):
    """Σύνολα από λίστα ShiftAssignment: work_days, repo, sundays, holidays_worked, extra, elsewhere."""
    hol = {h.hol_date for h in Holiday.query.all()}
    work = repo = sundays = hol_worked = elsewhere = 0
    extra = 0.0
    for a in assignments:
        code = a.shift_code
        if is_work_code(code):
            work += 1
            extra += extra_hours(assignment_hours(a))
            if a.work_date.weekday() == 6:
                sundays += 1
            if a.work_date in hol:
                hol_worked += 1
            if a.work_hotel_id and home_hotel_id and a.work_hotel_id != home_hotel_id:
                elsewhere += 1
        elif code == 'ΑΝ':
            repo += 1
    return {'work_days': work, 'repo': repo, 'sundays': sundays,
            'holidays_worked': hol_worked, 'extra_hours': round(extra, 2),
            'elsewhere_days': elsewhere, 'total_days': work}

def monthly_settlement(year, month, hotel_id=None):
    """Λίστα «ΠΡΟΣ ΛΟΓΙΣΤΗΡΙΟ» ανά εργαζόμενο για μήνα."""
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    q = (db.session.query(ShiftAssignment)
         .filter(ShiftAssignment.work_date >= start, ShiftAssignment.work_date < end))
    rows = q.all()
    by_user = {}
    for a in rows:
        by_user.setdefault(a.user_id, []).append(a)
    out = []
    for uid, alist in by_user.items():
        u = User.query.get(uid)
        if not u:
            continue
        if hotel_id and getattr(u, 'home_hotel_id', None) != hotel_id:
            continue
        agg = aggregate(alist, getattr(u, 'home_hotel_id', None))
        prof = EmploymentProfile.query.filter_by(user_id=uid).first()
        payable = 0.0
        if prof and prof.agreement_amount:
            if prof.agreement_type == 'Management':
                payable = round(prof.agreement_amount, 2)
            else:
                payable = round(prof.day_wage * agg['total_days'] + extra_wage(prof, agg['extra_hours']), 2)
        out.append({'user': u, 'agg': agg, 'payable': payable, 'profile': prof})
    out.sort(key=lambda r: r['user'].full_name or '')
    return out

def extra_wage(prof, hours):
    try:
        return round((prof.hour_wage or 0) * (hours or 0), 2)
    except Exception:
        return 0.0


# ── POLICY / RULES helpers ────────────────────────────────────────────────────
POLICY_DEFAULTS = {
    'planning_horizon_weeks': 8,
    'cutoff_dow': 3,          # 0=Δευτ ... 3=Πέμπτη
    'cutoff_time': '18:00',
    'lead_days': 4,           # προθεσμία = lead_days πριν τη Δευτέρα της W (4 = Πέμπτη προηγ.)
    'allow_admin_override': 1,
}

def get_policy():
    pol = dict(POLICY_DEFAULTS)
    for row in Setting.query.filter(Setting.key.like('sched_%')).all():
        k = row.key[6:]
        if k in pol:
            try:
                pol[k] = type(POLICY_DEFAULTS[k])(row.value) if not isinstance(POLICY_DEFAULTS[k], str) else row.value
            except Exception:
                pass
    return pol

def set_policy(d):
    for k, v in d.items():
        if k in POLICY_DEFAULTS:
            row = Setting.query.get('sched_' + k)
            if not row:
                row = Setting(key='sched_' + k); db.session.add(row)
            row.value = str(v)
    db.session.commit()

def week_deadline(week_start):
    """datetime προθεσμίας οριστικοποίησης για εβδομάδα που ξεκινά (Δευτέρα) week_start."""
    pol = get_policy()
    try:
        hh, mm = [int(x) for x in str(pol['cutoff_time']).split(':')]
    except Exception:
        hh, mm = 18, 0
    d = week_start - timedelta(days=int(pol['lead_days']))
    return datetime.combine(d, dtime(hh, mm))

def week_editable(week_start, user=None):
    """True αν η εβδομάδα είναι ακόμη επεξεργάσιμη (πριν την προθεσμία) ή admin override."""
    if datetime.now() < week_deadline(week_start):
        return True
    if user is not None and role_rank(user.role) >= ROLE_RANK['admin'] and int(get_policy()['allow_admin_override']):
        return True
    return False


# ── ROLE helpers ──────────────────────────────────────────────────────────────
def is_accountant():
    u = current_user()
    return u is not None and (u.role == 'accountant' or role_rank(u.role) >= ROLE_RANK['admin'])

def can_edit_schedule():
    return is_admin() or (current_user() and role_rank(current_user().role) >= ROLE_RANK['manager'])

def resolve_department(name):
    """Ταίριασμα ονόματος τμήματος -> Department (exact -> alias normalized)."""
    if not name:
        return None
    n = _norm(name)
    for d in Department.query.all():
        if _norm(d.name) == n or _norm(d.name_en or '') == n:
            return d
        try:
            for al in json.loads(d.aliases or '[]'):
                if _norm(al) == n:
                    return d
        except Exception:
            pass
    return None


# ── SEED (idempotent) ─────────────────────────────────────────────────────────
def seed_schedule():
  with app.app_context():
    try:
        # ShiftTypes
        if not ShiftType.query.first():
            for i, (code, label, color, cw, note, erg) in enumerate(SHIFT_CODES):
                db.session.add(ShiftType(code=code, label=label, color=color, counts_as_work=cw,
                                         payroll_note=note, ergani_type=erg, sort=i,
                                         default_start='07:00' if code == 'ΕΡΓ' else None,
                                         default_end='15:30' if code == 'ΕΡΓ' else None))
        # Departments
        if not Department.query.first():
            for i, (name, en, color, aliases) in enumerate(DEPARTMENTS):
                db.session.add(Department(name=name, name_en=en, color=color,
                                          aliases=json.dumps(aliases, ensure_ascii=False), sort=i))
        # Rules
        if not ScheduleRule.query.first():
            db.session.add(ScheduleRule(code='R1_repo', severity='block',
                description='Κάθε εργαζόμενος ≥1 ρεπό (ΑΝ) ανά εβδομάδα', params='{}'))
            db.session.add(ScheduleRule(code='R2_complete', severity='block',
                description='Καμία κενή ημέρα για assigned εργαζόμενο (πληρότητα 7/7)', params='{}', active=False))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'seed_schedule skipped: {e}')


# ── IMPORT (workbook προγράμματος -> χρήστες/τμήματα/αναθέσεις) ────────────────
CODE_HOTELNAME = {
    'AST': 'Asterias', 'CNT': 'Central', 'SRG': 'Sergios',
    'PSV': 'Piskopiano', 'IRO': 'Iro', 'PLM': 'Palm',  # v12.52: PLM = Palm Island Suites
}
_LABELS = {'τμημα': 'dept', 'ειδικοτητα': 'spec', 'εταιρεια': 'comp', 'υποκ': 'upok',
           'επωνυμο': 'epon', 'ονομα': 'onoma'}

def _resolve_hotel_by_code(code):
    if not code:
        return None
    code = HOTEL_NORM.get(str(code).strip().upper(), str(code).strip().upper())
    target = CODE_HOTELNAME.get(code)
    if not target:
        return None
    tn = _norm(target)
    for h in Hotel.query.all():
        if tn in _norm(h.name):
            return h
    return None

def _route_name(full):
    """Επιστρεφει master ΜΟΝΟ αν υπαρχει επιβεβαιωμενη συνδεση (NameLink, φτιαγμενη απο τον χρηστη).
    Αλλιως None -> ο καλων στελνει τη βαρδια στον προθαλαμο (PendingShift)."""
    nm = _norm(full)
    if not nm:
        return None
    link = NameLink.query.filter_by(norm_name=nm).first()
    if link:
        u = User.query.get(link.user_id)
        if u and u.is_active:
            return u
    return None

def _suggest_masters(full, limit=6):
    """Προτασεις (ΟΧΙ αυτοματη ενεργεια) πιθανων master για ενα ονομα — προτεραιοτητα locked Λογιστηριο.
    Επιστρεφει [(user, score)] ταξινομημενο. score: 100 ακριβες / 90 ιδιες λεξεις / 70 fuzzy / 40 ιδιο επωνυμο."""
    fn = _norm(full)
    if not fn:
        return []
    locked = _locked_uids()
    tgt = _tok_key(full)
    sur_t, _f = _name_parts(full)
    out = []
    for u in User.query.filter(User.is_active == True).all():
        un = u.full_name or ''
        sc = 0
        if _norm(un) == fn:
            sc = 100
        elif tgt and _tok_key(un) == tgt:
            sc = 90
        elif _names_likely_same(full, un):
            sc = 70
        else:
            sur_u, _ = _name_parts(un)
            if sur_t and sur_u == sur_t:
                sc = 40
        if sc:
            if u.id in locked:
                sc += 5
            out.append((u, sc))
    out.sort(key=lambda t: (-t[1], 0 if t[0].id in locked else 1, t[0].full_name or ''))
    return out[:limit]

def _find_or_create_user(epon, onoma, hotel, dept, employer, upok):
    full = (str(epon).strip() + ' ' + (str(onoma).strip() if onoma else '')).strip()
    # ΠΡΩΤΑ ταιριασμα με υπαρχον προφιλ (προτεραιοτητα master Λογιστηριο)
    user = _match_existing(full)
    created = False
    if user is None:
        base = _acc(full).lower().replace(' ', '.')
        uname = re.sub(r'[^a-z0-9.]', '', base) or ('emp' + str(ShiftAssignment.query.count() + 1))
        if User.query.filter_by(username=uname).first():
            uname = uname + '.' + str(User.query.count() + 1)
        user = User(username=uname[:50], password=generate_password_hash(os.urandom(8).hex()),
                    full_name=full[:100], role='staff', approved=True, is_active=True)
        db.session.add(user); db.session.flush(); created = True
    # μετα-στοιχεια ΜΟΝΟ σε νεο προφιλ - τα master κρατουν τα δικα τους assigned
    if created:
        if hotel: user.home_hotel_id = hotel.id
        if dept: user.department_id = dept.id
        if employer: user.employer = str(employer)[:120]
        if upok: user.subunit = str(upok)[:20]
        user.login_enabled = False
        user.employment_active = True
    return user

def import_schedule_workbook(source, only_year=None, created_by=None):
    """source = path ή bytes. Επιστρέφει στατιστικά. Idempotent (upsert ανά user/μέρα)."""
    import openpyxl, io
    if isinstance(source, (bytes, bytearray)):
        wb = openpyxl.load_workbook(io.BytesIO(source), data_only=True)
    else:
        wb = openpyxl.load_workbook(source, data_only=True)
    stats = {'users_new': 0, 'users_seen': 0, 'assign_new': 0, 'assign_upd': 0,
             'no_hotel': 0, 'cells': 0, 'pending_new': 0, 'pending_upd': 0}
    before_users = User.query.count()
    seen_users = set()
    for ws in wb.worksheets:
        mr, mc = ws.max_row, min(ws.max_column, 40)
        r = 1
        while r <= mr:
            a = ws.cell(r, 1).value
            if a and _norm(a) == 'τμημα':
                colmap = {}; datecols = []
                for c in range(1, mc + 1):
                    v = ws.cell(r, c).value
                    nv = _norm(v)
                    if nv in _LABELS:
                        colmap[_LABELS[nv]] = c
                    d = None
                    if isinstance(v, datetime):
                        d = v.date()
                    elif isinstance(v, str):
                        mm = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', v)
                        if mm:
                            d = date(int(mm.group(3)), int(mm.group(2)), int(mm.group(1)))
                    if d:
                        datecols.append((c, d))
                ce, co = colmap.get('epon'), colmap.get('onoma')
                rr = r + 1
                while rr <= mr and not (ws.cell(rr, 1).value and _norm(ws.cell(rr, 1).value) == 'τμημα'):
                    epon = ws.cell(rr, ce).value if ce else None
                    if epon and str(epon).strip():
                        onoma = ws.cell(rr, co).value if co else ''
                        upok = ws.cell(rr, colmap['upok']).value if colmap.get('upok') else None
                        dept_v = ws.cell(rr, colmap['dept']).value if colmap.get('dept') else None
                        comp_v = ws.cell(rr, colmap['comp']).value if colmap.get('comp') else None
                        hotel = _resolve_hotel_by_code(upok)
                        dept = resolve_department(dept_v)
                        full = (str(epon).strip() + ' ' + (str(onoma).strip() if onoma else '')).strip()
                        nm = _norm(full)
                        master = _route_name(full)   # ΜΟΝΟ επιβεβαιωμενη συνδεση -> αλλιως προθαλαμος
                        if master and master.id not in seen_users:
                            seen_users.add(master.id)
                        if not hotel:
                            stats['no_hotel'] += 1
                        for c, dt in datecols:
                            if only_year and dt.year != only_year:
                                continue
                            cell = ws.cell(rr, c).value
                            code, segs, tag = parse_cell(cell)
                            if code is None:
                                continue
                            stats['cells'] += 1
                            whid = None
                            if tag:
                                th = _resolve_hotel_by_code(tag)
                                whid = th.id if th else None
                            elif hotel:
                                whid = hotel.id
                            segj = json.dumps(segs, ensure_ascii=False)
                            if master:
                                ex = ShiftAssignment.query.filter_by(user_id=master.id, work_date=dt).first()
                                if ex:
                                    ex.shift_code = code; ex.segments = segj; ex.work_hotel_id = whid
                                    stats['assign_upd'] += 1
                                else:
                                    db.session.add(ShiftAssignment(
                                        user_id=master.id, work_date=dt, shift_code=code,
                                        segments=segj, work_hotel_id=whid, created_by=created_by))
                                    stats['assign_new'] += 1
                            else:
                                pend = PendingShift.query.filter_by(norm_name=nm, work_date=dt).first()
                                if pend:
                                    pend.shift_code = code; pend.segments = segj; pend.work_hotel_id = whid
                                    pend.raw_name = full[:120]
                                    stats['pending_upd'] += 1
                                else:
                                    db.session.add(PendingShift(
                                        norm_name=nm, raw_name=full[:120],
                                        epon=str(epon)[:80], onoma=(str(onoma)[:80] if onoma else None),
                                        hotel_tag=(str(upok)[:20] if upok else None),
                                        dept_raw=(str(dept_v)[:120] if dept_v else None),
                                        employer=(str(comp_v)[:120] if comp_v else None),
                                        work_date=dt, shift_code=code, segments=segj,
                                        work_hotel_id=whid, created_by=created_by))
                                    stats['pending_new'] += 1
                    rr += 1
                db.session.commit()
                r = rr
            else:
                r += 1
    wb.close()
    stats['users_new'] = User.query.count() - before_users
    stats['users_seen'] = len(seen_users)
    return stats


# ── ROUTES helpers ────────────────────────────────────────────────────────────
def _auth():
    return 'user_id' in session

def _week_arg():
    w = request.args.get('week')
    if w:
        try:
            return monday_of(datetime.strptime(w, '%Y-%m-%d').date())
        except Exception:
            pass
    return monday_of(date.today())

def _dept_users(hotel_id, dept_id):
    q = User.query.filter(User.is_active == True)
    if hotel_id:
        q = q.filter(User.home_hotel_id == hotel_id)
    if dept_id:
        q = q.filter(User.department_id == dept_id)
    return q.order_by(User.full_name).all()

def week_grid(hotel_id, dept_id, week_start):
    days = [week_start + timedelta(days=i) for i in range(7)]
    users = _dept_users(hotel_id, dept_id)
    uids = [u.id for u in users]
    amap = {}
    if uids:
        for a in (ShiftAssignment.query
                  .filter(ShiftAssignment.user_id.in_(uids))
                  .filter(ShiftAssignment.work_date >= days[0], ShiftAssignment.work_date <= days[6]).all()):
            amap[(a.user_id, a.work_date.isoformat())] = a
    rows = []
    for u in users:
        cells = []
        wk_hours = 0.0; wk_extra = 0.0; repo = 0; work_days = 0
        for d in days:
            a = amap.get((u.id, d.isoformat()))
            if a:
                pres = assignment_hours(a)
                hrs = worked_hours(a)
                if is_work_code(a.shift_code):
                    wk_hours += hrs; work_days += 1; wk_extra += extra_hours(pres)
                elif a.shift_code == 'ΑΝ':
                    repo += 1
                try:
                    segs = json.loads(a.segments) if a.segments else []
                except Exception:
                    segs = []
                label = a.shift_code
                if segs:
                    label = '\n'.join(f"{s['start']} - {s['end']}" for s in segs)
                cells.append({'date': d.isoformat(), 'code': a.shift_code, 'segs': segs,
                              'label': label, 'hours': round(hrs, 1),
                              'elsewhere': bool(a.work_hotel_id and a.work_hotel_id != hotel_id),
                              'note': a.note or ''})
            else:
                cells.append({'date': d.isoformat(), 'code': '', 'segs': [], 'label': '', 'hours': 0,
                              'elsewhere': False, 'note': ''})
        rows.append({'user': u, 'cells': cells, 'wk_hours': round(wk_hours, 1), 'wk_extra': round(wk_extra, 1), 'repo': repo, 'work_days': work_days})
    return days, rows

def validate_hotel_week(hotel_id, week_start):
    """Εφαρμογή ScheduleRules σε όλο το ξενοδοχείο/εβδομάδα. Επιστρέφει issues."""
    days = [week_start + timedelta(days=i) for i in range(7)]
    issues = []
    rules = {r.code: r for r in ScheduleRule.query.filter_by(active=True).all()}
    users = User.query.filter(User.is_active == True, User.home_hotel_id == hotel_id).all()
    for u in users:
        alist = (ShiftAssignment.query.filter(ShiftAssignment.user_id == u.id)
                 .filter(ShiftAssignment.work_date >= days[0], ShiftAssignment.work_date <= days[6]).all())
        if not alist:
            continue
        codes = [a.shift_code for a in alist]
        if 'R1_repo' in rules and codes.count('ΑΝ') < 1:
            issues.append({'user': u, 'rule': 'R1_repo', 'severity': rules['R1_repo'].severity,
                           'msg': f'{u.full_name}: κανένα ρεπό αυτή την εβδομάδα'})
        if 'R2_complete' in rules and len(alist) < 7:
            issues.append({'user': u, 'rule': 'R2_complete', 'severity': rules['R2_complete'].severity,
                           'msg': f'{u.full_name}: {7 - len(alist)} κενές ημέρες'})
    return issues


# ── ROUTE: Board (multi-week + πολλαπλά τμήματα δυναμικά) ──────────────────────
def _depts_present(hotel_id):
    """Τμήματα που έχουν εργαζόμενους στο ξενοδοχείο (για chips)."""
    if not hotel_id:
        return Department.query.filter_by(active=True).order_by(Department.sort).all()
    ids = {u.department_id for u in User.query.filter(User.is_active == True,
            User.home_hotel_id == hotel_id, User.department_id != None).all()}
    if not ids:
        return Department.query.filter_by(active=True).order_by(Department.sort).all()
    return Department.query.filter(Department.id.in_(ids)).order_by(Department.sort, Department.name).all()

def _build_block(hotel_id, dept_list, week_start, user):
    days = [week_start + timedelta(days=i) for i in range(7)]
    deptgrids = []
    for d in dept_list:
        _, rows = week_grid(hotel_id, d.id, week_start)
        deptgrids.append({'dept': d, 'rows': rows})
    sub = None
    if hotel_id:
        sub = (ScheduleSubmission.query.filter_by(hotel_id=hotel_id, week_start=week_start)
               .order_by(ScheduleSubmission.version.desc()).first())
    return {
        'week_start': week_start, 'days': days, 'deptgrids': deptgrids,
        'editable': week_editable(week_start, user) and can_edit_schedule(),
        'issues': validate_hotel_week(hotel_id, week_start) if hotel_id else [],
        'deadline': week_deadline(week_start), 'sub': sub, 'iso': week_start.isoformat(),
        'label': f"{week_start.strftime('%d/%m')} – {(week_start + timedelta(days=6)).strftime('%d/%m/%Y')}",
    }

@app.route('/dashboard/schedule')
def schedule_board():
    if not _auth():
        return redirect(url_for('login'))
    user = current_user()
    hotels = allowed_hotels(user)
    hotel_id = request.args.get('hotel_id', type=int) or active_hotel_id() or (hotels[0].id if hotels else None)
    dept_list = _depts_present(hotel_id)
    week_start = _week_arg()
    pol = get_policy()
    horizon = max(1, int(pol.get('planning_horizon_weeks', 8)))
    weeks = max(1, min(request.args.get('weeks', type=int) or 1, horizon))
    # v12.55 — πλοήγηση/προβολή μήνα: αν δοθεί month, δείξε ΟΛΟΝ τον μήνα (5-6 εβδομάδες)
    import calendar as _cal
    mon_arg = request.args.get('month', type=int)
    yr_arg = request.args.get('year', type=int) or week_start.year
    sel_month = mon_arg or week_start.month
    sel_year = yr_arg
    if mon_arg:
        first = date(yr_arg, mon_arg, 1)
        week_start = monday_of(first)
        last = date(yr_arg, mon_arg, _cal.monthrange(yr_arg, mon_arg)[1])
        weeks = ((monday_of(last) - week_start).days // 7) + 1
    prev_m = (date(sel_year, sel_month, 1) - timedelta(days=1))
    nxt = date(sel_year, sel_month, 28) + timedelta(days=10)
    blocks = [_build_block(hotel_id, dept_list, week_start + timedelta(days=7 * i), user) for i in range(weeks)]
    shift_types = ShiftType.query.filter_by(active=True).order_by(ShiftType.sort).all()
    shift_lookup = {st.code: st for st in shift_types}
    shift_types_json = json.dumps([{'code': st.code, 'color': st.color} for st in entry_shift_types()], ensure_ascii=False)
    cur_hotel = Hotel.query.get(hotel_id) if hotel_id else None
    return render_template('schedule_board.html',
        shift_lookup=shift_lookup, shift_types_json=shift_types_json,
        hotels=hotels, hotel_id=hotel_id, cur_hotel=cur_hotel, dept_list=dept_list,
        weekdays=WEEKDAYS_EL, shift_types=shift_types, blocks=blocks, weeks=weeks, horizon=horizon,
        week_start=week_start, week_start_iso=week_start.isoformat(),
        prev_week=(week_start - timedelta(days=7)).isoformat(),
        next_week=(week_start + timedelta(days=7)).isoformat(),
        month_el=MONTHS_EL, is_admin=is_admin(),
        sel_month=sel_month, sel_year=sel_year,
        prev_month=prev_m.month, prev_year=prev_m.year, next_month=nxt.month, next_year=nxt.year)


# ── API: autosave κελιού ──────────────────────────────────────────────────────
@app.route('/dashboard/schedule/cell', methods=['POST'])
def schedule_cell():
    if not _auth():
        return ('', 401)
    if not can_edit_schedule():
        return jsonify(ok=False, err='forbidden'), 403
    user = current_user()
    d = request.json or {}
    try:
        uid = int(d['user_id'])
        wd = datetime.strptime(d['date'], '%Y-%m-%d').date()
    except Exception:
        return jsonify(ok=False, err='bad'), 400
    if not week_editable(monday_of(wd), user):
        return jsonify(ok=False, err='locked'), 423
    code = (d.get('code') or '').strip()
    segs = d.get('segments') or []
    note = (d.get('note') or '')[:200]
    whid = d.get('work_hotel_id')
    a = ShiftAssignment.query.filter_by(user_id=uid, work_date=wd).first()
    if not code:
        if a:
            db.session.delete(a); db.session.commit()
        return jsonify(ok=True, deleted=True)
    # προεπιλεγμένες ώρες αν ΕΡΓ χωρίς segments
    if code == 'ΕΡΓ' and not segs:
        st = ShiftType.query.filter_by(code='ΕΡΓ').first()
        if st and st.default_start and st.default_end:
            segs = [{'start': st.default_start, 'end': st.default_end}]
    if not a:
        a = ShiftAssignment(user_id=uid, work_date=wd, created_by=user.id)
        db.session.add(a)
    a.shift_code = code
    a.segments = json.dumps(segs, ensure_ascii=False)
    a.work_hotel_id = whid
    a.note = note
    # WeekPlan -> draft (αν δεν υπάρχει)
    u = User.query.get(uid)
    if u and getattr(u, 'home_hotel_id', None) and getattr(u, 'department_id', None):
        wp = WeekPlan.query.filter_by(hotel_id=u.home_hotel_id, department_id=u.department_id,
                                      week_start=monday_of(wd)).first()
        if not wp:
            wp = WeekPlan(hotel_id=u.home_hotel_id, department_id=u.department_id,
                          week_start=monday_of(wd), status='draft')
            db.session.add(wp)
        if wp.status in ('submitted', 'locked'):
            wp.status = 'draft'
        wp.updated_by = user.id
    db.session.commit()
    hrs = worked_hours(a)
    return jsonify(ok=True, hours=round(hrs, 1), work=is_work_code(code))

@app.route('/dashboard/schedule/cells_bulk', methods=['POST'])
def schedule_cells_bulk():
    """v12.117 — μαζική εφαρμογη βαρδιας σε ευρος ημερων ενος εργαζομενου
    (drag-select στο μηνιαιο grid). Ιδιος ελεγχος/λογικη με το /schedule/cell."""
    if not _auth():
        return ('', 401)
    if not can_edit_schedule():
        return jsonify(ok=False, err='forbidden'), 403
    user = current_user()
    d = request.json or {}
    try:
        uid = int(d['user_id'])
        dates = d.get('dates') or []
    except Exception:
        return jsonify(ok=False, err='bad'), 400
    code = (d.get('code') or '').strip()
    segs = d.get('segments') or []
    if code == 'ΕΡΓ' and not segs:
        st = ShiftType.query.filter_by(code='ΕΡΓ').first()
        if st and st.default_start and st.default_end:
            segs = [{'start': st.default_start, 'end': st.default_end}]
    done = 0; locked = 0
    weeks = set()
    for ds in dates:
        try:
            wd = datetime.strptime(ds, '%Y-%m-%d').date()
        except Exception:
            continue
        if not week_editable(monday_of(wd), user):
            locked += 1; continue
        a = ShiftAssignment.query.filter_by(user_id=uid, work_date=wd).first()
        if not code:
            if a:
                db.session.delete(a)
        else:
            if not a:
                a = ShiftAssignment(user_id=uid, work_date=wd, created_by=user.id)
                db.session.add(a)
            a.shift_code = code
            a.segments = json.dumps(segs, ensure_ascii=False)
        weeks.add(monday_of(wd))
        done += 1
    # WeekPlan -> draft για τις επηρεασμενες εβδομαδες (οπως το single)
    u = User.query.get(uid)
    if u and getattr(u, 'home_hotel_id', None) and getattr(u, 'department_id', None):
        for ws in weeks:
            wp = WeekPlan.query.filter_by(hotel_id=u.home_hotel_id, department_id=u.department_id,
                                          week_start=ws).first()
            if not wp:
                wp = WeekPlan(hotel_id=u.home_hotel_id, department_id=u.department_id,
                              week_start=ws, status='draft')
                db.session.add(wp)
            if wp.status in ('submitted', 'locked'):
                wp.status = 'draft'
            wp.updated_by = user.id
    db.session.commit()
    return jsonify(ok=True, done=done, locked=locked)



# ── Αντιγραφή προηγούμενης εβδομάδας ──────────────────────────────────────────
@app.route('/dashboard/schedule/copyprev', methods=['POST'])
def schedule_copyprev():
    if not _auth() or not can_edit_schedule():
        return redirect(url_for('login'))
    user = current_user()
    hotel_id = request.form.get('hotel_id', type=int)
    dept_id = request.form.get('department_id', type=int)
    week_start = monday_of(datetime.strptime(request.form['week'], '%Y-%m-%d').date())
    if not week_editable(week_start, user):
        return redirect(f'/dashboard/schedule?hotel_id={hotel_id}&week={week_start}&embed=1&err=locked')
    prev = week_start - timedelta(days=7)
    users = _dept_users(hotel_id, dept_id) if dept_id else User.query.filter(User.is_active == True, User.home_hotel_id == hotel_id).all()
    n = 0
    for u in users:
        for i in range(7):
            sd, dd = prev + timedelta(days=i), week_start + timedelta(days=i)
            src = ShiftAssignment.query.filter_by(user_id=u.id, work_date=sd).first()
            if not src:
                continue
            dst = ShiftAssignment.query.filter_by(user_id=u.id, work_date=dd).first()
            if not dst:
                dst = ShiftAssignment(user_id=u.id, work_date=dd, created_by=user.id)
                db.session.add(dst)
            dst.shift_code = src.shift_code
            dst.segments = src.segments
            dst.work_hotel_id = src.work_hotel_id
            n += 1
    db.session.commit()
    log_activity('schedule_copyprev', f'{n} κελιά', hotel_id=hotel_id)
    return redirect(f'/dashboard/schedule?hotel_id={hotel_id}&week={week_start}&embed=1&ok=copied')


# ── ΥΠΟΒΟΛΗ (ενοποιημένη ανά ξενοδοχείο-εβδομάδα) ─────────────────────────────
def _hotel_week_snapshot(hotel_id, week_start):
    days = [week_start + timedelta(days=i) for i in range(7)]
    users = User.query.filter(User.is_active == True, User.home_hotel_id == hotel_id).all()
    snap = {}
    for u in users:
        alist = (ShiftAssignment.query.filter(ShiftAssignment.user_id == u.id)
                 .filter(ShiftAssignment.work_date >= days[0], ShiftAssignment.work_date <= days[6]).all())
        if not alist:
            continue
        dd = {}
        for a in alist:
            dd[a.work_date.isoformat()] = {'code': a.shift_code, 'segs': a.segments or '[]',
                                           'wh': a.work_hotel_id}
        snap[str(u.id)] = {'name': u.full_name, 'dept': getattr(u, 'department_id', None), 'days': dd}
    return snap

def _diff_snapshots(old, new):
    changes = []
    old = old or {}
    keys = set(old.keys()) | set(new.keys())
    for uid in keys:
        oname = (old.get(uid) or new.get(uid) or {}).get('name', uid)
        od = (old.get(uid) or {}).get('days', {})
        nd = (new.get(uid) or {}).get('days', {})
        for d in sorted(set(od.keys()) | set(nd.keys())):
            ov = od.get(d); nv = nd.get(d)
            if (ov or {}).get('code') != (nv or {}).get('code') or (ov or {}).get('segs') != (nv or {}).get('segs'):
                changes.append({'user_id': uid, 'name': oname, 'date': d,
                                'old': (ov or {}).get('code', '—'), 'new': (nv or {}).get('code', '—')})
    return changes

@app.route('/dashboard/schedule/submit', methods=['POST'])
def schedule_submit():
    if not _auth() or not can_edit_schedule():
        return redirect(url_for('login'))
    user = current_user()
    hotel_id = request.form.get('hotel_id', type=int)
    week_start = monday_of(datetime.strptime(request.form['week'], '%Y-%m-%d').date())
    issues = validate_hotel_week(hotel_id, week_start)
    blockers = [i for i in issues if i['severity'] == 'block']
    if blockers:
        return redirect(f'/dashboard/schedule?hotel_id={hotel_id}&week={week_start}&embed=1&err=rules')
    last = (ScheduleSubmission.query.filter_by(hotel_id=hotel_id, week_start=week_start)
            .order_by(ScheduleSubmission.version.desc()).first())
    snap = _hotel_week_snapshot(hotel_id, week_start)
    version = (last.version + 1) if last else 1
    changes = _diff_snapshots(json.loads(last.snapshot) if last and last.snapshot else None, snap) if last else []
    sub = ScheduleSubmission(hotel_id=hotel_id, week_start=week_start, version=version,
                             parent_version=(last.version if last else None),
                             status='submitted', snapshot=json.dumps(snap, ensure_ascii=False),
                             changes=json.dumps(changes, ensure_ascii=False),
                             submitted_by=user.id)
    db.session.add(sub)
    for wp in WeekPlan.query.filter_by(hotel_id=hotel_id, week_start=week_start).all():
        wp.status = 'submitted'
    db.session.commit()
    log_activity('schedule_submit', f'v{version}', hotel_id=hotel_id)
    # ειδοποίηση + email λογιστηρίου (background)
    hotel = Hotel.query.get(hotel_id)
    hn = hotel.name if hotel else ''
    label = 'ΤΡΟΠΟΠΟΙΗΣΗ' if version > 1 else 'Νέα υποβολή'
    _notify_accountants(hotel_id, week_start, version, label, changes)
    return redirect(f'/dashboard/schedule?hotel_id={hotel_id}&week={week_start}&embed=1&ok=submitted')

def _notify_accountants(hotel_id, week_start, version, label, changes):
    try:
        hotel = Hotel.query.get(hotel_id)
        hn = hotel.name if hotel else ''
        wk = week_start.strftime('%d/%m/%Y')
        accts = User.query.filter_by(role='accountant', is_active=True).all()
        for a in accts:
            notify(a.id, f'Πρόγραμμα {hn} — εβδ. {wk} ({label} v{version})', '/dashboard/schedule/submissions?embed=1')
        db.session.commit()
        recips = [a.email for a in accts if a.email] + list(EMAIL_TO_LIST)
        rows = ''.join(f"<tr><td>{c['name']}</td><td>{c['date']}</td><td>{c['old']}</td><td>{c['new']}</td></tr>" for c in changes)
        chtml = (f"<p><b>Αλλαγές (v{version}):</b></p><table border=1 cellpadding=4 style='border-collapse:collapse'>"
                 f"<tr><th>Εργαζόμενος</th><th>Ημ/νία</th><th>Πριν</th><th>Μετά</th></tr>{rows}</table>") if changes else ''
        html = (f"<h3>Πρόγραμμα Εργασίας — {hn}</h3>"
                f"<p>Εβδομάδα <b>{wk}</b> — <b>{label}</b> (έκδοση v{version}).</p>{chtml}"
                f"<p>Δες στο σύστημα: Εστία → Πρόγραμμα Εργασίας → Υποβολές.</p>")
        threading.Thread(target=lambda: send_email(f'[Εστία] Πρόγραμμα {hn} — εβδ. {wk} ({label})', html, recips)).start()
    except Exception as e:
        db.session.rollback()
        print('notify_accountants:', e)

@app.route('/dashboard/schedule/submissions')
def schedule_submissions():
    if not _auth():
        return redirect(url_for('login'))
    if not (is_admin() or is_accountant()):
        return ('Δεν έχετε πρόσβαση', 403)
    user = current_user()
    hids = {h.id for h in allowed_hotels(user)}
    q = ScheduleSubmission.query.order_by(ScheduleSubmission.submitted_at.desc())
    aid = active_hotel_id()
    if aid:
        q = q.filter(ScheduleSubmission.hotel_id == aid)
    subs = [s for s in q.limit(300).all() if (not hids) or s.hotel_id in hids]
    hotels = {h.id: h.name for h in Hotel.query.all()}
    return render_template('schedule_submissions.html', subs=subs, hotels=hotels,
                           month_el=MONTHS_EL)

@app.route('/dashboard/schedule/submission/<int:sid>')
def schedule_submission_view(sid):
    if not _auth():
        return redirect(url_for('login'))
    if not (is_admin() or is_accountant()):
        return ('Δεν έχετε πρόσβαση', 403)
    sub = ScheduleSubmission.query.get_or_404(sid)
    try:
        snap = json.loads(sub.snapshot or '{}')
        changes = json.loads(sub.changes or '[]')
    except Exception:
        snap, changes = {}, []
    days = [sub.week_start + timedelta(days=i) for i in range(7)]
    changed = {(c['user_id'], c['date']) for c in changes}
    hotel = Hotel.query.get(sub.hotel_id)
    return render_template('schedule_submission_view.html', sub=sub, snap=snap, changes=changes,
                           days=days, weekdays=WEEKDAYS_EL, changed=changed,
                           hotel=hotel, month_el=MONTHS_EL)


# ── EXPORT «ΠΡΟΣ ΛΟΓΙΣΤΗΡΙΟ» (μηνιαίο) ────────────────────────────────────────
@app.route('/dashboard/schedule/export.xlsx')
def schedule_export():
    if not _auth() or not (is_admin() or is_accountant()):
        return redirect(url_for('login'))
    import openpyxl, io
    year = request.args.get('year', type=int) or date.today().year
    month = request.args.get('month', type=int) or date.today().month
    hotel_id = request.args.get('hotel_id', type=int) or active_hotel_id()
    data = monthly_settlement(year, month, hotel_id)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'ΠΡΟΣ ΛΟΓΙΣΤΗΡΙΟ'
    ws.append(['Ονοματεπώνυμο', 'Μήνας', 'Καθημερινές εργάσιμες', 'Κυριακές', 'Αργίες',
               'Έξτρα ώρες', 'Ρεπό', 'Μέρες αλλού', 'Σύνολο ημερών', 'Πληρωτέο συμφωνίας'])
    mname = MONTHS_EL[month]
    for r in data:
        a = r['agg']
        ws.append([r['user'].full_name, mname, a['work_days'], a['sundays'], a['holidays_worked'],
                   a['extra_hours'], a['repo'], a['elsewhere_days'], a['total_days'], r['payable']])
    bio = io.BytesIO(); wb.save(bio); bio.seek(0)
    fn = f'PROS_LOGISTIRIO_{year}_{month:02d}.xlsx'
    return Response(bio.read(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={fn}'})


# ── v12.115 — ΜΗΝΙΑΙΑ ΣΥΓΚΕΝΤΡΩΤΙΚΗ ΚΑΤΑΣΤΑΣΗ (για μεροκάματα) ────────────────
def _monthly_rows(year, month, hotel_id=None, dept_id=None):
    """Ανά εργαζόμενο (home hotel, ΟΛΕΣ οι ώρες μαζί): ώρες/έξτρα/Κυριακές/εργάσιμες/ρεπό
    + ημερολόγιο μήνα (day->assignment). Group ανά home hotel + υποσύνολα + γενικό σύνολο."""
    import calendar as _cal
    ndays = _cal.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    hol = {h.hol_date for h in Holiday.query.all()}
    try:
        from payroll import EmployeePII as _PII
        piimap = {p.user_id: p for p in _PII.query.all()}
    except Exception:
        piimap = {}
    assigns = (ShiftAssignment.query
               .filter(ShiftAssignment.work_date >= start, ShiftAssignment.work_date < end).all())
    by_user = {}
    for a in assigns:
        by_user.setdefault(a.user_id, []).append(a)
    rows = []
    for uid, alist in by_user.items():
        u = User.query.get(uid)
        if not u or not u.is_active:
            continue
        hh = getattr(u, 'home_hotel_id', None)
        if hotel_id and hh != hotel_id:
            continue
        if dept_id and getattr(u, 'department_id', None) != dept_id:
            continue
        days = {}
        hours = extra = 0.0
        sundays = work_days = repo = hol_worked = 0
        for a in alist:
            days[a.work_date.day] = a
            if is_work_code(a.shift_code):
                pres = assignment_hours(a)
                hours += worked_hours(a); extra += extra_hours(pres); work_days += 1
                if a.work_date.weekday() == 6:
                    sundays += 1
                if a.work_date in hol:
                    hol_worked += 1
            elif a.shift_code == 'ΑΝ':
                repo += 1
        prof = EmploymentProfile.query.filter_by(user_id=uid).first()
        payable = 0.0
        if prof and getattr(prof, 'agreement_amount', None):
            if getattr(prof, 'agreement_type', None) == 'Management':
                payable = round(prof.agreement_amount, 2)
            else:
                payable = round((getattr(prof, 'day_wage', 0) or 0) * work_days + extra_wage(prof, extra), 2)
        _pp = piimap.get(uid)
        rows.append({'user': u, 'hotel_id': hh, 'days': days,
                     'emp_code': (_pp.emp_code if _pp else None),
                     'afm': (_pp.afm if _pp else None),
                     'locked': (bool(_pp.locked) if _pp else False),
                     'hours': round(hours, 1), 'extra': round(extra, 1),
                     'sundays': sundays, 'holidays': hol_worked,
                     'work_days': work_days, 'repo': repo, 'payable': payable})
    rows.sort(key=lambda r: (r['user'].full_name or ''))
    hotels_by_id = {h.id: h for h in Hotel.query.all()}
    groups = {}
    for r in rows:
        groups.setdefault(r['hotel_id'], []).append(r)
    def _sub(rs):
        return {'hours': round(sum(x['hours'] for x in rs), 1),
                'extra': round(sum(x['extra'] for x in rs), 1),
                'sundays': sum(x['sundays'] for x in rs),
                'holidays': sum(x['holidays'] for x in rs),
                'work_days': sum(x['work_days'] for x in rs),
                'repo': sum(x['repo'] for x in rs),
                'payable': round(sum(x['payable'] for x in rs), 2),
                'count': len(rs)}
    out = []
    for hid, rs in sorted(groups.items(),
                          key=lambda kv: (hotels_by_id.get(kv[0]).name if hotels_by_id.get(kv[0]) else 'zzz')):
        out.append({'hotel': hotels_by_id.get(hid), 'rows': rs, 'subtotal': _sub(rs)})
    return {'groups': out, 'grand': _sub(rows), 'ndays': ndays}


def _monthly_args():
    year = request.args.get('year', type=int) or date.today().year
    month = request.args.get('month', type=int) or date.today().month
    hotel_id = request.args.get('hotel_id', type=int) or 0
    dept_id = request.args.get('dept', type=int) or 0
    return year, month, hotel_id, dept_id


@app.route('/dashboard/schedule/monthly')
def schedule_monthly():
    if not _auth() or not (is_admin() or is_accountant()):
        return redirect(url_for('login'))
    user = current_user()
    year, month, hotel_id, dept_id = _monthly_args()
    view = request.args.get('view') or 'summary'
    data = _monthly_rows(year, month, hotel_id or None, dept_id or None)
    hotels = allowed_hotels(user) or Hotel.query.order_by(Hotel.name).all()
    depts = Department.query.order_by(Department.name).all()
    deptmap = {d.id: d.name for d in depts}
    hol = {h.hol_date for h in Holiday.query.all()}
    WD = ['Δε', 'Τρ', 'Τε', 'Πε', 'Πα', 'Σα', 'Κυ']
    day_hdr = []
    for d in range(1, data['ndays'] + 1):
        dt = date(year, month, d)
        day_hdr.append({'d': d, 'wd': WD[dt.weekday()], 'we': dt.weekday() >= 5,
                        'hol': dt in hol, 'iso': dt.isoformat()})
    shift_types = ShiftType.query.filter_by(active=True).order_by(ShiftType.sort).all()
    return render_template('schedule_monthly.html', data=data, year=year, month=month,
        hotel_id=hotel_id, dept_id=dept_id, view=view, hotels=hotels, depts=depts, deptmap=deptmap,
        months=MONTHS_EL, day_hdr=day_hdr, ndays=data['ndays'],
        can_edit=(can_edit_schedule() and is_admin()),
        shift_types=shift_types,
        shift_types_json=json.dumps([{'code': s.code, 'color': s.color} for s in entry_shift_types()], ensure_ascii=False),
        years=list(range(date.today().year - 2, date.today().year + 2)),
        is_admin=is_admin())


@app.route('/dashboard/schedule/monthly.xlsx')
def schedule_monthly_xlsx():
    if not _auth() or not (is_admin() or is_accountant()):
        return redirect(url_for('login'))
    import openpyxl, io
    from openpyxl.styles import Font, PatternFill
    year, month, hotel_id, dept_id = _monthly_args()
    data = _monthly_rows(year, month, hotel_id or None, dept_id or None)
    deptmap = {d.id: d.name for d in Department.query.all()}
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Μηνιαία'
    navy = PatternFill('solid', fgColor='193847')
    def boldrow(size=11):
        for c in range(1, 10):
            ws.cell(row=ws.max_row, column=c).font = Font(bold=True, size=size)
    ws.append(['Εστία — Μηνιαία συγκεντρωτική · %s %d' % (MONTHS_EL[month], year)])
    ws['A1'].font = Font(bold=True, size=14, color='193847')
    ws.append([])
    ws.append(['Ξενοδοχείο', 'Ονοματεπώνυμο', 'Τμήμα', 'Ώρες', 'Έξτρα ώρες',
               'Κυριακές', 'Εργάσιμες', 'Ρεπό', 'Πληρωτέο'])
    for c in range(1, 10):
        cc = ws.cell(row=ws.max_row, column=c); cc.font = Font(bold=True, color='FFFFFF'); cc.fill = navy
    for g in data['groups']:
        hn = g['hotel'].name if g['hotel'] else '— (χωρίς ξενοδοχείο)'
        for x in g['rows']:
            ws.append([hn, x['user'].full_name, deptmap.get(getattr(x['user'], 'department_id', None), ''),
                       x['hours'], x['extra'], x['sundays'], x['work_days'], x['repo'], x['payable']])
        s = g['subtotal']
        ws.append(['Σύνολο · %s' % hn, '', '', s['hours'], s['extra'], s['sundays'],
                   s['work_days'], s['repo'], s['payable']]); boldrow()
    gd = data['grand']
    ws.append(['ΓΕΝΙΚΟ ΣΥΝΟΛΟ', '', '', gd['hours'], gd['extra'], gd['sundays'],
               gd['work_days'], gd['repo'], gd['payable']]); boldrow(12)
    widths = [26, 30, 18, 9, 11, 10, 11, 8, 12]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    bio = io.BytesIO(); wb.save(bio); bio.seek(0)
    fn = 'estia_monthly_%d_%02d.xlsx' % (year, month)
    return Response(bio.read(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=%s' % fn})


@app.route('/dashboard/schedule/monthly.pdf')
def schedule_monthly_pdf():
    if not _auth() or not (is_admin() or is_accountant()):
        return redirect(url_for('login'))
    from fpdf import FPDF
    year, month, hotel_id, dept_id = _monthly_args()
    data = _monthly_rows(year, month, hotel_id or None, dept_id or None)
    deptmap = {d.id: d.name for d in Department.query.all()}
    NAVY = (25, 56, 71); GREY = (120, 120, 120)
    pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.set_auto_page_break(True, margin=12)
    pdf.add_font('dv', '', os.path.join(BASE_DIR, 'assets', 'fonts', 'DejaVuSans.ttf'))
    pdf.add_font('dv', 'B', os.path.join(BASE_DIR, 'assets', 'fonts', 'DejaVuSans-Bold.ttf'))
    pdf.add_page()
    try:
        pdf.image(os.path.join(BASE_DIR, 'static', 'img', 'logo.png'), x=12, y=9, h=13)
    except Exception:
        pass
    pdf.set_xy(30, 10); pdf.set_font('dv', 'B', 15); pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, 'Εστία — Μηνιαία συγκεντρωτική κατάσταση', ln=1)
    pdf.set_x(30); pdf.set_font('dv', '', 10); pdf.set_text_color(*GREY)
    pdf.cell(0, 6, '%s %d · Εκτύπωση: %s' % (MONTHS_EL[month], year, date.today().strftime('%d/%m/%Y')), ln=1)
    pdf.ln(5)
    headers = ['Ονοματεπώνυμο', 'Τμήμα', 'Ώρες', 'Έξτρα', 'Κυρ.', 'Εργάσ.', 'Ρεπό', 'Πληρωτέο']
    widths = [82, 55, 24, 24, 20, 24, 18, 30]
    def hdr():
        pdf.set_font('dv', 'B', 9); pdf.set_text_color(255, 255, 255); pdf.set_fill_color(*NAVY)
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, h, border=0, fill=True, align='L')
        pdf.ln(8)
    for g in data['groups']:
        hn = g['hotel'].name if g['hotel'] else '— (χωρίς ξενοδοχείο)'
        pdf.set_font('dv', 'B', 11); pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, hn, ln=1)
        hdr()
        fill = False
        for x in g['rows']:
            pdf.set_fill_color(243, 247, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.set_font('dv', '', 8.5); pdf.set_text_color(40, 40, 40)
            vals = [x['user'].full_name, deptmap.get(getattr(x['user'], 'department_id', None), ''),
                    x['hours'], x['extra'], x['sundays'], x['work_days'], x['repo'], x['payable']]
            for val, w in zip(vals, widths):
                s = str(val)
                while s and pdf.get_string_width(s) > w - 2 and len(s) > 3:
                    s = s[:-2]
                pdf.cell(w, 7, s, border=0, fill=True, align='L')
            pdf.ln(7); fill = not fill
        s = g['subtotal']
        pdf.set_font('dv', 'B', 9); pdf.set_text_color(*NAVY); pdf.set_fill_color(225, 235, 245)
        sub = ['Σύνολο · %s' % hn, '', s['hours'], s['extra'], s['sundays'], s['work_days'], s['repo'], s['payable']]
        for val, w in zip(sub, widths):
            ss = str(val)
            while ss and pdf.get_string_width(ss) > w - 2 and len(ss) > 3:
                ss = ss[:-2]
            pdf.cell(w, 7, ss, border=0, fill=True, align='L')
        pdf.ln(10)
    gd = data['grand']
    pdf.set_font('dv', 'B', 11); pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, 'ΓΕΝΙΚΟ ΣΥΝΟΛΟ: %s ώρες · %s έξτρα · %s Κυρ. · %s εργάσιμες · %s ρεπό · %s €'
             % (gd['hours'], gd['extra'], gd['sundays'], gd['work_days'], gd['repo'], gd['payable']), ln=1)
    out = bytes(pdf.output())
    fn = 'estia_monthly_%d_%02d.pdf' % (year, month)
    return Response(out, mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=%s' % fn})

# ── v12.116 — ΕΠΟΠΤΕΙΑ ΠΡΟΓΡΑΜΜΑΤΟΣ (τι κάνουν οι managers, μηνιαία) ───────────
def _oversight_weeks(year, month):
    import calendar as _cal
    ndays = _cal.monthrange(year, month)[1]
    first = date(year, month, 1); last = date(year, month, ndays)
    w = monday_of(first); weeks = []
    while w <= last:
        weeks.append(w); w = w + timedelta(days=7)
    return weeks


def _oversight_data(year, month):
    weeks = _oversight_weeks(year, month)
    wkmin, wkmax = weeks[0], weeks[-1]
    umap = {u.id: u for u in User.query.all()}
    def uname(uid): 
        u = umap.get(uid); return (u.full_name if u else '—')
    # WeekPlans + Submissions στο εύρος
    wps = WeekPlan.query.filter(WeekPlan.week_start >= wkmin, WeekPlan.week_start <= wkmax).all()
    subs = (ScheduleSubmission.query
            .filter(ScheduleSubmission.week_start >= wkmin, ScheduleSubmission.week_start <= wkmax).all())
    wp_idx = {}
    for wp in wps:
        wp_idx[(wp.hotel_id, wp.department_id, wp.week_start)] = wp
    sub_idx = {}
    for s in subs:
        k = (s.hotel_id, s.week_start)
        if k not in sub_idx or (s.version or 0) > (sub_idx[k].version or 0):
            sub_idx[k] = s
    STAT = {'draft': ('Πρόχειρο', '#fde68a', '#92400e'),
            'submitted': ('Υποβλήθηκε', '#bbf7d0', '#166534'),
            'locked': ('Κλειδώθηκε', '#bfdbfe', '#1e40af')}
    # ── BY HOTEL ──
    hotels = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()
    by_hotel = []
    for h in hotels:
        depts = _depts_present(h.id)
        rows = []
        done = total = 0
        for d in depts:
            cells = []
            for wk in weeks:
                wp = wp_idx.get((h.id, d.id, wk))
                total += 1
                st = wp.status if wp else None
                if st in ('submitted', 'locked'): done += 1
                cells.append({'wk': wk, 'status': st,
                              'label': (STAT.get(st, ('—', '#f1f5f9', '#94a3b8'))[0] if st else '—'),
                              'bg': (STAT.get(st, ('', '#f8fafc', ''))[1] if st else '#f8fafc'),
                              'fg': (STAT.get(st, ('', '', '#94a3b8'))[2] if st else '#94a3b8'),
                              'by': (uname(wp.updated_by) if wp and wp.updated_by else ''),
                              'when': (wp.updated_at.strftime('%d/%m %H:%M') if wp and wp.updated_at else '')})
            rows.append({'dept': d, 'cells': cells})
        sub_cells = []
        for wk in weeks:
            s = sub_idx.get((h.id, wk))
            sub_cells.append({'wk': wk, 'sub': s,
                              'by': (uname(s.submitted_by) if s and s.submitted_by else ''),
                              'when': (s.submitted_at.strftime('%d/%m %H:%M') if s and s.submitted_at else ''),
                              'ver': (s.version if s else None), 'sid': (s.id if s else None)})
        by_hotel.append({'hotel': h, 'depts': depts, 'rows': rows, 'subs': sub_cells,
                         'done': done, 'total': total})
    # ── BY MANAGER ── (όποιος έχει δραστηριότητα στην περίοδο)
    actor_ids = set([wp.updated_by for wp in wps if wp.updated_by] +
                    [s.submitted_by for s in subs if s.submitted_by])
    mgr = []
    for uid in actor_ids:
        u = umap.get(uid)
        if not u:
            continue
        my_wp = [wp for wp in wps if wp.updated_by == uid]
        my_sub = [s for s in subs if s.submitted_by == uid]
        hotel_ids = set([wp.hotel_id for wp in my_wp] + [s.hotel_id for s in my_sub])
        hotel_names = ', '.join(sorted({(Hotel.query.get(hid).name if Hotel.query.get(hid) else '—') for hid in hotel_ids}))
        times = [wp.updated_at for wp in my_wp if wp.updated_at] + [s.submitted_at for s in my_sub if s.submitted_at]
        last = max(times) if times else None
        sub_list = sorted(my_sub, key=lambda s: s.submitted_at or datetime.min, reverse=True)
        mgr.append({'user': u, 'role': u.role, 'n_wp': len(my_wp), 'n_sub': len(my_sub),
                    'hotels': hotel_names, 'last': (last.strftime('%d/%m/%Y %H:%M') if last else '—'),
                    'subs': sub_list})
    mgr.sort(key=lambda m: (-(m['n_sub'] + m['n_wp']), m['user'].full_name or ''))
    return {'weeks': weeks, 'by_hotel': by_hotel, 'by_manager': mgr}


@app.route('/dashboard/schedule/oversight')
def schedule_oversight():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    year = request.args.get('year', type=int) or date.today().year
    month = request.args.get('month', type=int) or date.today().month
    view = request.args.get('view') or 'hotel'
    data = _oversight_data(year, month)
    return render_template('schedule_oversight.html', data=data, year=year, month=month,
        view=view, months=MONTHS_EL, years=list(range(date.today().year - 2, date.today().year + 2)),
        is_admin=is_admin())






# ── IMPORT page (upload workbook) ─────────────────────────────────────────────
@app.route('/dashboard/schedule/import', methods=['GET', 'POST'])
def schedule_import():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    results = None
    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files:
            f = request.files.get('file')
            files = [f] if f else []
        only_year = None if request.form.get('all_years') else request.form.get('year', type=int)
        results = []
        for f in files:
            if not f or not f.filename:
                continue
            try:
                data = f.read()
                kind, stats = import_any(data, f.filename, only_year=only_year, created_by=session.get('user_id'))
                results.append({'name': f.filename, 'kind': kind, 'stats': stats})
            except Exception as e:
                results.append({'name': f.filename, 'kind': 'error', 'stats': {'error': str(e)}})
        seed_schedule()
        log_activity('schedule_import_multi', f'{len(results)} αρχεία')
    try:
        from payroll import EmployeePII as _PII
        _locked = {p.user_id for p in _PII.query.filter_by(locked=True).all()}
    except Exception:
        _locked = set()
    purge_count = sum(1 for u in imported_staff_query().all() if u.id not in _locked)
    pending_total = PendingShift.query.count()
    return render_template('schedule_import.html', results=results, year=date.today().year, purge_count=purge_count, pending_total=pending_total)


# ── ΤΑΥΤΟΠΟΙΗΣΗ: προθαλαμος ονοματων χωρις επιβεβαιωμενο master ────────────────
def _confirm_link(norm_name, master_id, created_by=None):
    """Ο χρηστης επιβεβαιωνει: φτιαχνει NameLink + μεταφερει ΟΛΕΣ τις PendingShift στο master."""
    master = User.query.get(master_id)
    if not master:
        return 0
    pend = PendingShift.query.filter_by(norm_name=norm_name).all()
    rawn = pend[0].raw_name if pend else None
    link = NameLink.query.filter_by(norm_name=norm_name).first()
    if link:
        link.user_id = master_id
    else:
        db.session.add(NameLink(norm_name=norm_name, user_id=master_id,
                                raw_name=rawn, created_by=created_by))
    moved = 0
    for ps in pend:
        ex = ShiftAssignment.query.filter_by(user_id=master_id, work_date=ps.work_date).first()
        if ex:
            ex.shift_code = ps.shift_code; ex.segments = ps.segments; ex.work_hotel_id = ps.work_hotel_id
        else:
            db.session.add(ShiftAssignment(user_id=master_id, work_date=ps.work_date,
                shift_code=ps.shift_code, segments=ps.segments,
                work_hotel_id=ps.work_hotel_id, created_by=created_by))
            moved += 1
        db.session.delete(ps)
    db.session.commit()
    return moved

def _pending_pii_map():
    try:
        from payroll import EmployeePII as _PII
        return {pp.user_id: pp for pp in _PII.query.all()}
    except Exception:
        return {}

@app.context_processor
def _inject_pending_identify():
    def pending_identify_count():
        try:
            return db.session.query(PendingShift.norm_name).distinct().count()
        except Exception:
            return 0
    return {'pending_identify_count': pending_identify_count}

@app.route('/dashboard/schedule/identify')
def schedule_identify():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    groups = {}
    for ps in PendingShift.query.order_by(PendingShift.work_date).all():
        g = groups.get(ps.norm_name)
        if not g:
            g = {'norm': ps.norm_name, 'raw': ps.raw_name, 'count': 0,
                 'hotel_tag': ps.hotel_tag, 'dept': ps.dept_raw, 'employer': ps.employer,
                 'dmin': ps.work_date, 'dmax': ps.work_date}
            groups[ps.norm_name] = g
        g['count'] += 1
        if ps.work_date:
            if not g['dmin'] or ps.work_date < g['dmin']: g['dmin'] = ps.work_date
            if not g['dmax'] or ps.work_date > g['dmax']: g['dmax'] = ps.work_date
    piimap = _pending_pii_map()
    locked = _locked_uids()
    items = []
    for g in groups.values():
        sugg = []
        for u, sc in _suggest_masters(g['raw'] or g['norm'], limit=5):
            pp = piimap.get(u.id)
            sugg.append({'id': u.id, 'name': u.full_name,
                         'emp_code': (pp.emp_code if pp else None),
                         'afm': (pp.afm if pp else None),
                         'locked': u.id in locked, 'score': sc})
        g['suggestions'] = sugg
        items.append(g)
    items.sort(key=lambda x: (-x['count'], x['raw'] or ''))
    return render_template('schedule_identify.html', items=items, total=len(items))

@app.route('/dashboard/schedule/identify/link', methods=['POST'])
def schedule_identify_link():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    nm = (request.form.get('norm_name') or '').strip()
    mid = request.form.get('master_id', type=int)
    if nm and mid:
        moved = _confirm_link(nm, mid, created_by=session.get('user_id'))
        u = User.query.get(mid)
        log_activity('schedule_identify_link', '%s -> %s (%d βάρδιες)' % (nm, (u.full_name if u else mid), moved))
    return redirect(url_for('schedule_identify'))

@app.route('/dashboard/schedule/identify/dismiss', methods=['POST'])
def schedule_identify_dismiss():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    nm = (request.form.get('norm_name') or '').strip()
    if nm:
        n = PendingShift.query.filter_by(norm_name=nm).delete()
        db.session.commit()
        log_activity('schedule_identify_dismiss', '%s (%s)' % (nm, n))
    return redirect(url_for('schedule_identify'))

@app.route('/dashboard/schedule/identify/search')
def schedule_identify_search():
    if not _auth() or not is_admin():
        return jsonify([])
    qraw = (request.args.get('q') or '').strip()
    q = _norm(qraw)
    if not qraw:
        return jsonify([])
    piimap = _pending_pii_map()
    locked = _locked_uids()
    res = []
    for u in User.query.filter(User.is_active == True).all():
        pp = piimap.get(u.id)
        afm = (pp.afm if pp else '') or ''
        emp = (pp.emp_code if pp else '') or ''
        if (q and q in _norm(u.full_name or '')) or (qraw in afm) or (qraw.upper() in emp.upper()):
            res.append({'id': u.id, 'name': u.full_name, 'emp_code': emp, 'afm': afm,
                        'locked': u.id in locked})
        if len(res) >= 20:
            break
    return jsonify(res)

def _exact_master_map():
    """norm_name -> λιστα ενεργων users με ΑΚΡΙΒΕΣ ιδιο ονομα."""
    m = {}
    for u in User.query.filter(User.is_active == True).all():
        nm = _norm(u.full_name or '')
        if nm:
            m.setdefault(nm, []).append(u)
    return m

def _seed_locked_links(created_by=None):
    """Ταυτοτητα (ΟΧΙ merge): NameLink καθε locked master -> στο ιδιο του το ονομα.
    Skip: ασαφη (ιδιο norm_name σε >1 locked) + οσα εχουν ηδη link."""
    locked = _locked_uids()
    by_nm = {}
    for u in User.query.filter(User.is_active == True).all():
        if u.id in locked:
            nm = _norm(u.full_name or '')
            if nm:
                by_nm.setdefault(nm, []).append(u)
    n = 0; skipped = 0
    for nm, us in by_nm.items():
        if len(us) != 1:
            skipped += 1; continue
        if NameLink.query.filter_by(norm_name=nm).first():
            continue
        db.session.add(NameLink(norm_name=nm, user_id=us[0].id,
                                raw_name=us[0].full_name, created_by=created_by))
        n += 1
    db.session.commit()
    return n, skipped

@app.route('/dashboard/schedule/identify/seed_locked', methods=['POST'])
def schedule_identify_seed_locked():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    n, skipped = _seed_locked_links(created_by=session.get('user_id'))
    log_activity('schedule_identify_seed_locked', '%d links, %d ασαφη' % (n, skipped))
    # μετα το seed, τρεξε και αυτοματη ταυτοποιηση ακριβων για οσα ηδη ειναι στον προθαλαμο
    return redirect(url_for('schedule_identify'))

@app.route('/dashboard/schedule/identify/auto', methods=['POST'])
def schedule_identify_auto():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    locked = _locked_uids()
    exact = _exact_master_map()
    norms = [r[0] for r in db.session.query(PendingShift.norm_name).distinct().all()]
    linked = 0
    for nm in norms:
        cands = exact.get(nm) or []
        target = None
        if len(cands) == 1:
            target = cands[0]
        elif len(cands) > 1:
            lk = [u for u in cands if u.id in locked]
            if len(lk) == 1:
                target = lk[0]
        if target:
            _confirm_link(nm, target.id, created_by=session.get('user_id'))
            linked += 1
    log_activity('schedule_identify_auto', '%d ακριβη ταιριασματα' % linked)
    return redirect(url_for('schedule_identify'))


@app.route('/dashboard/schedule/identify/clear_all', methods=['POST'])
def schedule_identify_clear_all():
    # v12.114 — καθαρισμος ΟΛΟΥ του προθαλαμου (1 κλικ αντι N «Αγνόησε»)· ιδανικο
    # για reset πριν σωστο re-import (π.χ. οταν τα ξενοδοχεια ηταν λαθος στην πηγη).
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    n = PendingShift.query.delete()
    db.session.commit()
    log_activity('schedule_identify_clear_all', '%d βαρδιες προθαλαμου' % (n or 0))
    return redirect(url_for('schedule_identify') + ('?embed=1' if request.args.get('embed') else ''))


@app.route('/dashboard/schedule/imported')
def schedule_imported():
    # v12.114 — ενιαια οθονη: εισηγμενα (keyless) προφιλ με badge + προταση 🔒 master
    # + κουμπια «Συγχωνευση με Master» / «Διαγραφη». Ξεχωριζει «αληθινος→merge» απο «σκουπιδι→delete».
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    locked = _locked_uids()
    piimap = _pending_pii_map()
    rows = []
    for u in imported_staff_query().filter(User.is_active == True).all():
        if u.id in locked:
            continue
        sugg = None
        for cand, sc in _suggest_masters(u.full_name or '', limit=8):
            if cand.id == u.id or cand.id not in locked:
                continue
            pp = piimap.get(cand.id)
            sugg = {'id': cand.id, 'name': cand.full_name,
                    'emp_code': (pp.emp_code if pp else None),
                    'afm': (pp.afm if pp else None), 'score': sc}
            break
        rows.append({'id': u.id, 'name': u.full_name,
                     'shifts': ShiftAssignment.query.filter_by(user_id=u.id).count(),
                     'suggestion': sugg})
    rows.sort(key=lambda r: (0 if r['suggestion'] else 1, -r['shifts'], r['name'] or ''))
    return render_template('schedule_imported.html', rows=rows, total=len(rows))


@app.route('/dashboard/schedule/imported/merge', methods=['POST'])
def schedule_imported_merge():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    drop_id = int(request.form.get('drop_id') or 0)
    master_id = int(request.form.get('master_id') or 0)
    drop = User.query.get(drop_id); master = User.query.get(master_id)
    locked = _locked_uids()
    if drop and master and drop.id != master.id and drop.id not in locked:
        # μεταφορα ΜΟΝΟ βαρδιων στο master (διπλη μερα: κραταμε του master)
        keep_dates = {a.work_date for a in ShiftAssignment.query.filter_by(user_id=master_id).all()}
        for a in ShiftAssignment.query.filter_by(user_id=drop_id).all():
            if a.work_date in keep_dates:
                db.session.delete(a)
            else:
                a.user_id = master_id; keep_dates.add(a.work_date)
        # NameLink ωστε μελλοντικα imports αυτου του ονοματος να πανε στο master
        nm = _norm(drop.full_name or '')
        if nm:
            link = NameLink.query.filter_by(norm_name=nm).first()
            if link:
                link.user_id = master_id
            else:
                db.session.add(NameLink(norm_name=nm, user_id=master_id,
                                        raw_name=drop.full_name, created_by=session.get('user_id')))
        db.session.commit()
        # τωρα ο drop ειναι χωρις βαρδιες -> πληρης διαγραφη (cascade)
        try:
            from payroll import _hard_delete_user as _hdel
            _hdel(drop_id)
        except Exception:
            db.session.rollback()
        log_activity('schedule_imported_merge', '%d -> %d' % (drop_id, master_id))
    return redirect(url_for('schedule_imported') + ('?embed=1' if request.args.get('embed') else ''))


@app.route('/dashboard/schedule/imported/delete', methods=['POST'])
def schedule_imported_delete():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    uid = int(request.form.get('uid') or 0)
    try:
        from payroll import _hard_delete_user as _hdel
        ok, _r = _hdel(uid)
        log_activity('schedule_imported_delete', '%d (%s)' % (uid, 'ok' if ok else _r))
    except Exception:
        db.session.rollback()
    return redirect(url_for('schedule_imported') + ('?embed=1' if request.args.get('embed') else ''))


# ── PASTE: μαζική επικόλληση προγράμματος από Excel (όνομα + Δ–Κ) ──────────────
def _name_index():
    ix, ixs = {}, {}
    for u in User.query.filter(User.is_active == True).all():
        if getattr(u, 'employment_active', None) is False:
            continue
        fn = u.full_name or ''
        k = _norm(fn)
        if k:
            ix.setdefault(k, []).append(u)
        toks = sorted([t for t in re.sub(r'[^a-zα-ω0-9 ]', '', _acc(fn).lower()).split() if t])
        ks = ''.join(toks)
        if ks:
            ixs.setdefault(ks, []).append(u)
    return ix, ixs

def _match_name(name, ix, ixs):
    k = _norm(name)
    if k in ix:
        return (ix[k][0], None) if len(ix[k]) == 1 else (None, 'διπλό όνομα στο Μητρώο')
    toks = sorted([t for t in re.sub(r'[^a-zα-ω0-9 ]', '', _acc(name).lower()).split() if t])
    ks = ''.join(toks)
    if ks in ixs:
        return (ixs[ks][0], None) if len(ixs[ks]) == 1 else (None, 'αμφίσημο όνομα')
    return (None, 'δεν βρέθηκε στο Μητρώο')

def _cell_label(code, segs):
    if code is None:
        return '—'
    if code == 'ΕΡΓ':
        if segs:
            return 'ΕΡΓ ' + ', '.join('%s-%s' % (x.get('start'), x.get('end')) for x in segs)
        return 'ΕΡΓ'
    return code

def _parse_paste(raw, monday):
    ix, ixs = _name_index()
    days = [monday + timedelta(days=i) for i in range(7)]
    rows = []
    for line in (raw or '').splitlines():
        if not line.strip():
            continue
        cells = line.split('	')
        name = cells[0].strip()
        if not name or _norm(name) in ('ονοματεπωνυμο', 'ονομα', 'επωνυμο', 'τμημα'):
            continue
        user = _route_name(name); warn = None if user else "προς ταυτοποίηση (μη συνδεδεμένο)"
        dayvals = cells[1:8]
        parsed = []
        for i, dt in enumerate(days):
            raw_v = dayvals[i].strip() if i < len(dayvals) else ''
            code, segs, tag = parse_cell(raw_v) if raw_v else (None, [], None)
            whid = None
            if tag:
                th = _resolve_hotel_by_code(tag); whid = th.id if th else None
            elif user is not None:
                whid = getattr(user, 'home_hotel_id', None)
            unknown = bool(raw_v) and code is None
            lbl = _cell_label(code, segs)
            if unknown and (_norm(raw_v) in ('ρεπο', 'ρεπ', 'ρ', 'off', 'repo', 'dayoff') or raw_v in ('-', '—', '/')):
                unknown = False; lbl = 'ΡΕΠΟ'   # ρεπό = κενή ημέρα (καμία ανάθεση)
            parsed.append({'date': dt, 'raw': raw_v, 'code': code, 'segs': segs,
                           'whid': whid, 'label': lbl, 'unknown': unknown})
        rows.append({'name': name, 'user': user, 'warn': warn, 'days': parsed,
                     'matched': user is not None})
    return rows, days

@app.route('/dashboard/schedule/paste', methods=['GET', 'POST'])
def schedule_paste():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    monday = _week_arg()
    rows = None; saved = None
    if request.method == 'POST':
        raw = request.form.get('data', '')
        ws = request.form.get('week_start', '')
        try:
            monday = monday_of(datetime.strptime(ws, '%Y-%m-%d').date())
        except Exception:
            monday = _week_arg()
        rows, days = _parse_paste(raw, monday)
        if request.form.get('action') == 'commit':
            user = current_user(); n_new = n_upd = 0
            for r in rows:
                if not r['user']:
                    continue
                for d in r['days']:
                    if d['code'] is None:
                        continue
                    a = ShiftAssignment.query.filter_by(user_id=r['user'].id, work_date=d['date']).first()
                    if a:
                        a.shift_code = d['code']; a.segments = json.dumps(d['segs'], ensure_ascii=False)
                        a.work_hotel_id = d['whid']; n_upd += 1
                    else:
                        db.session.add(ShiftAssignment(user_id=r['user'].id, work_date=d['date'],
                            shift_code=d['code'], segments=json.dumps(d['segs'], ensure_ascii=False),
                            work_hotel_id=d['whid'], created_by=user.id)); n_new += 1
                    u = r['user']
                    if getattr(u, 'home_hotel_id', None) and getattr(u, 'department_id', None):
                        wp = WeekPlan.query.filter_by(hotel_id=u.home_hotel_id, department_id=u.department_id, week_start=monday).first()
                        if not wp:
                            wp = WeekPlan(hotel_id=u.home_hotel_id, department_id=u.department_id, week_start=monday, status='draft'); db.session.add(wp)
                        elif wp.status in ('submitted', 'locked'):
                            wp.status = 'draft'
            db.session.commit()
            seed_schedule()
            log_activity('schedule_paste', 'νέες %d / ενημ. %d' % (n_new, n_upd))
            saved = {'new': n_new, 'upd': n_upd,
                     'unmatched': sum(1 for r in rows if not r['user'])}
    else:
        days = [monday + timedelta(days=i) for i in range(7)]
    return render_template('schedule_paste.html', rows=rows, days=days, monday=monday,
                           week_start=monday.strftime('%Y-%m-%d'), saved=saved,
                           raw=request.form.get('data', ''))



# ── ADMIN settings (κωδικοί / τμήματα / αργίες / πολιτική / κανόνες) ───────────
@app.route('/dashboard/schedule/settings', methods=['GET', 'POST'])
def schedule_settings():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    if request.method == 'POST':
        act = request.form.get('action')
        if act == 'policy':
            set_policy({k: request.form.get(k) for k in POLICY_DEFAULTS if request.form.get(k) is not None})
        elif act == 'holiday':
            try:
                hd = datetime.strptime(request.form['hol_date'], '%Y-%m-%d').date()
                if not Holiday.query.filter_by(hol_date=hd).first():
                    db.session.add(Holiday(hol_date=hd, description=request.form.get('description', '')[:120], year=hd.year))
                    db.session.commit()
            except Exception:
                db.session.rollback()
        elif act == 'holiday_del':
            h = Holiday.query.get(request.form.get('id', type=int))
            if h:
                db.session.delete(h); db.session.commit()
        elif act == 'rule_toggle':
            r = ScheduleRule.query.get(request.form.get('id', type=int))
            if r:
                r.active = not r.active; db.session.commit()
        elif act == 'shift_toggle':
            s = ShiftType.query.get(request.form.get('id', type=int))
            if s:
                s.active = not s.active; db.session.commit()
        elif act == 'entry_codes':
            codes = request.form.getlist('entry_code')
            row = Setting.query.get('sched_entry_codes')
            if not row:
                row = Setting(key='sched_entry_codes'); db.session.add(row)
            row.value = json.dumps(codes, ensure_ascii=False)
            db.session.commit()
        return redirect('/dashboard/schedule/settings?embed=1&ok=1')
    _allow = _entry_codes_setting()
    return render_template('schedule_settings.html',
        policy=get_policy(), shift_types=ShiftType.query.order_by(ShiftType.sort).all(),
        entry_codes=_allow, entry_all=(_allow is None),
        depts=Department.query.order_by(Department.sort).all(),
        holidays=Holiday.query.order_by(Holiday.hol_date).all(),
        rules=ScheduleRule.query.all(), dow_el=DOW_EL)


# ── ROUTE: Διαχείριση Προσωπικού (οργανόγραμμα: τμήμα/ξενοδοχείο/login) ────────
@app.route('/dashboard/schedule/staff', methods=['GET', 'POST'])
def schedule_staff():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    if request.method == 'POST':
        act = request.form.get('action')
        if act == 'add':
            full = (request.form.get('full_name') or '').strip()
            if full:
                base = re.sub(r'[^a-z0-9.]', '', _acc(full).lower().replace(' ', '.')) or 'emp'
                uname = base
                i = 1
                while User.query.filter_by(username=uname).first():
                    i += 1; uname = f'{base}.{i}'
                u = User(username=uname[:50], password=generate_password_hash(os.urandom(8).hex()),
                         full_name=full[:100], role='staff', approved=True, is_active=True,
                         department_id=request.form.get('department_id', type=int) or None,
                         home_hotel_id=request.form.get('home_hotel_id', type=int) or None,
                         employer=(request.form.get('employer') or '')[:120] or None,
                         login_enabled=bool(request.form.get('login_enabled')),
                         employment_active=True)
                db.session.add(u); db.session.commit()
                log_activity('staff_add', full)
        elif act == 'edit':
            u = User.query.get(request.form.get('user_id', type=int))
            if u:
                u.department_id = request.form.get('department_id', type=int) or None
                u.home_hotel_id = request.form.get('home_hotel_id', type=int) or None
                u.employer = (request.form.get('employer') or '')[:120] or None
                u.login_enabled = bool(request.form.get('login_enabled'))
                db.session.commit()
        elif act == 'toggle_active':
            u = User.query.get(request.form.get('user_id', type=int))
            if u:
                u.employment_active = not bool(getattr(u, 'employment_active', True))
                db.session.commit()
        qs = f"?embed=1&hotel_id={request.form.get('f_hotel','')}&department_id={request.form.get('f_dept','')}"
        return redirect('/dashboard/schedule/staff' + qs)
    f_hotel = request.args.get('hotel_id', type=int)
    f_dept = request.args.get('department_id', type=int)
    q = User.query.filter(User.is_active == True)
    if f_hotel:
        q = q.filter(User.home_hotel_id == f_hotel)
    if f_dept:
        q = q.filter(User.department_id == f_dept)
    users = q.order_by(User.full_name).limit(800).all()
    dup_groups = find_dup_groups()
    return render_template('schedule_staff.html',
        users=users, depts=Department.query.order_by(Department.sort).all(),
        hotels=Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all(),
        f_hotel=f_hotel, f_dept=f_dept, dup_groups=dup_groups,
        dept_map={d.id: d.name for d in Department.query.all()},
        hotel_map={h.id: h.name for h in Hotel.query.all()})


# ── ΕΚΚΑΘΑΡΙΣΗ / ΣΥΓΧΩΝΕΥΣΗ ΔΙΠΛΩΝ ΕΡΓΑΖΟΜΕΝΩΝ ──────────────────────────────
def _lev(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def _name_parts(full):
    toks = _acc(full or '').lower().split()
    sur = toks[0] if toks else ''
    first = ' '.join(toks[1:]) if len(toks) > 1 else ''
    return _norm(sur), _norm(first)

def _likely_dup(u1, u2):
    s1, f1 = _name_parts(u1.full_name)
    s2, f2 = _name_parts(u2.full_name)
    if not s1 or s1 != s2:
        return False                       # διαφορετικό επώνυμο -> όχι
    if f1 == f2:
        return True                        # ίδιο πλήρες όνομα
    if not f1 or not f2:
        return True                        # ο ένας χωρίς μικρό (π.χ. "FARO" vs "FARO ANNA")
    if f1.startswith(f2) or f2.startswith(f1):
        return True
    if _lev(f1, f2) <= 2 and min(len(f1), len(f2)) >= 3:
        return True                        # JOEY vs JOY, typos
    return False

def _names_likely_same(full_a, full_b):
    s1, f1 = _name_parts(full_a); s2, f2 = _name_parts(full_b)
    if not s1 or s1 != s2:
        return False
    if f1 == f2 or not f1 or not f2:
        return True
    if f1.startswith(f2) or f2.startswith(f1):
        return True
    pl = 0
    for a, b in zip(f1, f2):
        if a == b: pl += 1
        else: break
    if pl >= 4:                            # ΝΙΚΟΣ <-> ΝΙΚΟΛΑΟΣ (κοινο προθεμα >=4)
        return True
    if _lev(f1, f2) <= 2 and min(len(f1), len(f2)) >= 3:
        return True                        # NATALIA <-> NATALIIA
    return False

def _locked_uids():
    try:
        from payroll import EmployeePII as _PII
        return {row[0] for row in db.session.query(_PII.user_id).filter_by(locked=True).all()}
    except Exception:
        return set()

def _tok_key(name):
    return ''.join(sorted([t for t in re.sub(r'[^a-z\u03b1-\u03c90-9 ]', '', _acc(name or '').lower()).split() if t]))

def _match_existing(full):
    """Ταιριαζει το ονομα με υπαρχον προφιλ - ΠΡΟΤΕΡΑΙΟΤΗΤΑ στο master (Λογιστηριο).
    Ετσι οι βαρδιες κουμπωνουν στα master προφιλ αντι να φτιαχνονται διπλα."""
    fn = _norm(full)
    if not fn:
        return None
    users = User.query.filter(User.is_active == True).all()
    locked = _locked_uids()
    def prefer(cs):
        for u in cs:
            if u.id in locked: return u
        return cs[0] if cs else None
    ex = [u for u in users if _norm(u.full_name) == fn]
    if ex: return prefer(ex)
    tgt = _tok_key(full)
    ts = [u for u in users if tgt and _tok_key(u.full_name) == tgt]
    if ts: return prefer(ts)
    fz = [u for u in users if u.id in locked and _names_likely_same(full, u.full_name or '')]
    if fz: return fz[0]
    return None

def find_dup_groups():
    users = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    parent = {u.id: u.id for u in users}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    by_sur = {}
    for u in users:
        s, _ = _name_parts(u.full_name)
        by_sur.setdefault(s, []).append(u)
    for s, lst in by_sur.items():
        if not s or len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if _likely_dup(lst[i], lst[j]):
                    union(lst[i].id, lst[j].id)
    groups = {}
    umap = {u.id: u for u in users}
    for u in users:
        groups.setdefault(find(u.id), []).append(u)
    out = []
    for gid, members in groups.items():
        if len(members) > 1:
            # εμπλουτισμός: πλήθος βαρδιών + αν είναι κλειδωμένο (Λογιστήριο)
            try:
                from payroll import EmployeePII as _PII
                _locked = {row[0] for row in db.session.query(_PII.user_id).filter_by(locked=True).all()}
            except Exception:
                _locked = set()
            for m in members:
                m._assign_n = ShiftAssignment.query.filter_by(user_id=m.id).count()
                m._locked = m.id in _locked
            # default keep = πρώτα το κλειδωμένο (Λογιστήριο), μετά όποιος έχει τις περισσότερες βάρδιες
            members.sort(key=lambda m: (not m._locked, -m._assign_n))
            out.append(members)
    out.sort(key=lambda g: g[0].full_name or '')
    return out

def merge_users(keep_id, drop_ids):
    """v12.103 — ΜΟΝΟ βάρδιες μεταφέρονται στον keep. Θέση/τμήμα/ξενοδοχείο/προφίλ
    του keep ΜΕΝΟΥΝ ως έχουν (τα ήδη assigned στη βάση). Οι διπλοί αρχειοθετούνται."""
    keep = User.query.get(keep_id)
    if not keep:
        return 0
    moved = 0
    keep_dates = {a.work_date for a in ShiftAssignment.query.filter_by(user_id=keep_id).all()}
    for d in drop_ids:
        u = User.query.get(d)
        if not u or u.id == keep_id:
            continue
        # ΜΟΝΟ βάρδιες -> keep (διπλή μέρα: κρατάμε του keep)
        for a in ShiftAssignment.query.filter_by(user_id=d).all():
            if a.work_date in keep_dates:
                db.session.delete(a)
            else:
                a.user_id = keep_id; keep_dates.add(a.work_date); moved += 1
        # ΔΕΝ μεταφέρουμε θέση/τμήμα/ξενοδοχείο/προφίλ — καθαρίζουμε του διπλού
        dp = EmploymentProfile.query.filter_by(user_id=d).first()
        if dp:
            db.session.delete(dp)
        try:
            import faults as _flt
            for us in _flt.UserSpecialty.query.filter_by(user_id=d).all():
                db.session.delete(us)
        except Exception:
            pass
        db.session.delete(u)
    db.session.commit()
    return moved

@app.route('/dashboard/schedule/staff/merge', methods=['POST'])
def schedule_staff_merge():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    keep_id = request.form.get('keep_id', type=int)
    drop_ids = [int(x) for x in request.form.getlist('drop_ids') if x.isdigit() and int(x) != keep_id]
    if keep_id and drop_ids:
        n = merge_users(keep_id, drop_ids)
        log_activity('staff_merge', f'keep={keep_id} drop={drop_ids} moved={n}')
    return redirect('/dashboard/schedule/staff?embed=1&ok=merged')


# ── Καθαρισμός εισαγμένου προσωπικού (login ανενεργό) ─────────────────────────
def imported_staff_query():
    return User.query.filter(User.login_enabled == False)

@app.route('/dashboard/schedule/staff/purge', methods=['POST'])
def schedule_staff_purge():
    if not _auth() or not is_admin():
        return redirect(url_for('login'))
    # v12.114 — full cascade ανά χρηστη μεσω _hard_delete_user (καθαριζει ολους τους
    # σχετιζομενους πινακες + προστατευει τα κλειδωμενα)· per-user try ωστε ενα FK
    # σφαλμα να ΜΗΝ μπλοκαρει τους υπολοιπους (πριν: μερικη διαγραφη -> FK violation).
    staff = imported_staff_query().all()
    try:
        from payroll import EmployeePII as _PII, _hard_delete_user as _hdel
        locked_ids = {p.user_id for p in _PII.query.filter_by(locked=True).all()}
    except Exception:
        locked_ids = set(); _hdel = None
    staff = [u for u in staff if u.id not in locked_ids]   # v12.56: μην σβήνεις κλειδωμένους (Epsilon)
    done = 0; failed = 0
    for u in staff:
        ok = False
        if _hdel:
            try:
                ok, _r = _hdel(u.id)
            except Exception:
                db.session.rollback(); ok = False
        if ok: done += 1
        else:  failed += 1
    log_activity('schedule_staff_purge', 'v12.114: %d διαγραφηκαν, %d απετυχαν' % (done, failed))
    return redirect('/dashboard/schedule/import?embed=1&purged=' + str(done))


# ── ΕΙΣΑΓΩΓΗ ΜΗΤΡΩΟΥ ΕΡΓΑΖΟΜΕΝΩΝ (payroll «Εργαζόμενοι» — καθαρή πηγή) ─────────
REG_NAME_KEYS = {'ονοματεπωνυμο', 'επωνυμο'}
def _parse_date_cell(v):
    if v is None or v == '':
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', str(v).strip())
    if m:
        y = int(m.group(3)); y = y + 2000 if y < 100 else y
        try:
            return date(y, int(m.group(2)), int(m.group(1)))
        except Exception:
            return None
    return None

def _to_float(v):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None

def _registry_header(ws, maxr=12):
    """Βρες γραμμή-κεφαλίδα μητρώου: έχει τμημα + (επωνυμο|ονοματεπωνυμο) και ΟΧΙ ημερομηνίες."""
    REG = {'id': ['id'], 'active': ['ενεργος', 'κατασταση'], 'dept': ['τμημα'],
           'position': ['θεση', 'ειδικοτητα'], 'epon': ['επωνυμο'], 'onoma': ['ονομα'],
           'fullname': ['ονοματεπωνυμο'], 'employer': ['εταιρεια'], 'upok': ['υποκ'],
           'amount': ['συμφωνια', 'συμφωνημενοποσο'], 'days': ['ημερεσμηνα', 'ημερες'],
           'hours': ['ωρεςμερα', 'ωρες'], 'hired': ['ημπροσληψης', 'ημερομηνιαπροσληψης'],
           'left': ['ημαποχωρησης', 'ημερομηνιααποχωρησης'], 'email': ['email'], 'phone': ['τηλεφωνο']}
    for r in range(1, min(maxr, ws.max_row) + 1):
        cmap = {}; has_date = False
        for c in range(1, min(ws.max_column, 30) + 1):
            v = ws.cell(r, c).value
            nv = _norm(v)
            if isinstance(v, datetime) or (isinstance(v, str) and re.match(r'\d{1,2}/\d{1,2}/\d{4}', v.strip())):
                has_date = True
            for key, alts in REG.items():
                if nv in alts and key not in cmap:
                    cmap[key] = c
        if not has_date and 'dept' in cmap and ('epon' in cmap or 'fullname' in cmap):
            return r, cmap
    return None, None

def detect_kind(wb):
    for ws in wb.worksheets:
        # schedule = έχει ΤΜΗΜΑ + στήλες ημερομηνιών
        for r in range(1, min(6, ws.max_row) + 1):
            if _norm(ws.cell(r, 1).value) == 'τμημα':
                for c in range(1, min(ws.max_column, 30) + 1):
                    v = ws.cell(r, c).value
                    if isinstance(v, datetime) or (isinstance(v, str) and re.match(r'\d{1,2}/\d{1,2}/\d{4}', str(v).strip())):
                        return 'schedule'
    for ws in wb.worksheets:
        hr, _ = _registry_header(ws)
        if hr:
            return 'registry'
    return 'unknown'

def import_staff_registry(source, hotel_hint=None):
    import openpyxl, io
    wb = (openpyxl.load_workbook(io.BytesIO(source), data_only=True)
          if isinstance(source, (bytes, bytearray)) else openpyxl.load_workbook(source, data_only=True))
    hint_hotel = _resolve_hotel_by_code(hotel_hint) if hotel_hint else None
    stats = {'users_new': 0, 'users_upd': 0, 'profiles': 0, 'inactive': 0, 'rows': 0}
    # διάλεξε ΕΝΑ φύλλο μητρώου: προτίμησε «Εργαζόμενοι», αλλιώς το 1ο με header μητρώου
    target = None
    for ws in wb.worksheets:
        if 'εργαζομεν' in _norm(ws.title):
            if _registry_header(ws)[0]:
                target = ws; break
    if target is None:
        for ws in wb.worksheets:
            if _registry_header(ws)[0]:
                target = ws; break
    for ws in ([target] if target else []):
        hr, cm = _registry_header(ws)
        for r in range(hr + 1, ws.max_row + 1):
            def g(k):
                return ws.cell(r, cm[k]).value if cm.get(k) else None
            if cm.get('fullname'):
                full = str(g('fullname') or '').strip()
            else:
                full = (str(g('epon') or '').strip() + ' ' + str(g('onoma') or '').strip()).strip()
            if not full or _norm(full) in ('', 'συνολο', 'ονοματεπωνυμο'):
                continue
            stats['rows'] += 1
            dept = resolve_department(g('dept'))
            upok = g('upok')
            hotel = _resolve_hotel_by_code(upok) if upok else hint_hotel
            # active
            av = _norm(g('active'))
            active = True
            if av in ('οχι', 'ανενεργος', 'αποχωρησε', 'inactive', 'no'):
                active = False
            fn = _norm(full)
            user = None
            for u in User.query.all():
                if _norm(u.full_name) == fn:
                    user = u; break
            if not user:
                base = re.sub(r'[^a-z0-9.]', '', _acc(full).lower().replace(' ', '.')) or 'emp'
                un = base; i = 1
                while User.query.filter_by(username=un).first():
                    i += 1; un = f'{base}.{i}'
                user = User(username=un[:50], password=generate_password_hash(os.urandom(8).hex()),
                            full_name=full[:100], role='staff', approved=True, is_active=True,
                            login_enabled=False)
                db.session.add(user); db.session.flush()
                stats['users_new'] += 1
            else:
                stats['users_upd'] += 1
            if dept and not user.department_id:
                user.department_id = dept.id
            if hotel and not user.home_hotel_id:
                user.home_hotel_id = hotel.id
            if g('employer') and not user.employer:
                user.employer = str(g('employer'))[:120]
            if upok and not user.subunit:
                user.subunit = str(upok)[:20]
            if user.login_enabled is None:
                user.login_enabled = False
            user.employment_active = active
            if not active:
                stats['inactive'] += 1
            # EmploymentProfile
            prof = EmploymentProfile.query.filter_by(user_id=user.id).first()
            amount = _to_float(g('amount'))
            if amount or g('position') or g('hired'):
                if not prof:
                    prof = EmploymentProfile(user_id=user.id); db.session.add(prof); stats['profiles'] += 1
                if amount:
                    prof.agreement_amount = amount
                dd = _to_float(g('days'));  hh = _to_float(g('hours'))
                if dd:
                    prof.days_per_month = int(dd)
                if hh:
                    prof.hours_per_day = hh
                if g('position'):
                    prof.position = str(g('position'))[:80]
                if g('hired'):
                    prof.hired_at = _parse_date_cell(g('hired'))
                if g('left'):
                    prof.left_at = _parse_date_cell(g('left'))
                prof.status = 'Ενεργός' if active else 'Ανενεργός'
        db.session.commit()
    wb.close()
    return stats

def import_any(source, filename='', only_year=None, created_by=None):
    """Auto-detect: εισάγει ΚΑΙ μητρώο ΚΑΙ πρόγραμμα αν υπάρχουν στο ίδιο αρχείο."""
    import openpyxl, io
    wb = openpyxl.load_workbook(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source, data_only=True)
    has_reg = any(_registry_header(ws)[0] for ws in wb.worksheets)
    has_sch = False
    for ws in wb.worksheets:
        for r in range(1, min(6, ws.max_row) + 1):
            if _norm(ws.cell(r, 1).value) == 'τμημα':
                for c in range(1, min(ws.max_column, 30) + 1):
                    v = ws.cell(r, c).value
                    if isinstance(v, datetime) or (isinstance(v, str) and re.match(r'\d{1,2}/\d{1,2}/\d{4}', str(v).strip())):
                        has_sch = True; break
            if has_sch:
                break
        if has_sch:
            break
    wb.close()
    code = None
    m = re.match(r'^\s*([A-Za-zΑ-Ωα-ω]{2,4})\b', filename or '')
    if m:
        code = m.group(1).upper()
    out = {'registry': None, 'schedule': None}
    if has_reg:
        out['registry'] = import_staff_registry(source, hotel_hint=code)
    if has_sch:
        out['schedule'] = import_schedule_workbook(source, only_year=only_year, created_by=created_by)
    kind = '+'.join([k for k in ('registry', 'schedule') if out[k] is not None]) or 'unknown'
    return kind, out
