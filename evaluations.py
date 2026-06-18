# -*- coding: utf-8 -*-
"""Εστία — evaluations.py (Module Αξιολόγησης Προσωπικού, Φ1).
Plug-in: import από το ΤΕΛΟΣ του app.py (πριν το init_db ώστε το create_all να πιάσει τα μοντέλα).
HR/admin-only. Reference: CONDIAN Employee Evaluation Form (25 σταθμισμένα κριτήρια, κλίμακα 1-10).
"""
from datetime import datetime, date
from flask import request, redirect, url_for, render_template, session, jsonify, Response
from app import (app, db, current_user, is_admin, log_activity, role_rank, ROLE_RANK,
                 User, Hotel)

# ── Μοντέλα ───────────────────────────────────────────────────────────────────
class EvalTemplate(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(80), nullable=False)
    scope      = db.Column(db.String(40), default='general')   # 'general' | dept-key (Φ2 variants)
    scale_max  = db.Column(db.Integer, default=10)
    is_active  = db.Column(db.Boolean, default=True)
    version    = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    criteria   = db.relationship('EvalCriterion', backref='template',
                                 order_by='EvalCriterion.sort', cascade='all, delete-orphan')

class EvalCriterion(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('eval_template.id'))
    grp         = db.Column(db.String(40))      # ομάδα (Βασικά / Ξένες γλώσσες)
    label       = db.Column(db.String(200))
    weight      = db.Column(db.Float, default=0)
    sort        = db.Column(db.Integer, default=0)
    max_score   = db.Column(db.Integer, default=10)

class Evaluation(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(32), index=True)  # κοινό σε όλες τις versions
    employee_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evaluator_id  = db.Column(db.Integer, db.ForeignKey('user.id'))
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'))
    department_id = db.Column(db.Integer)
    template_id   = db.Column(db.Integer, db.ForeignKey('eval_template.id'))
    period_label  = db.Column(db.String(40))    # σαιζόν/περίοδος
    year          = db.Column(db.Integer)
    eval_date     = db.Column(db.Date, default=date.today)
    status        = db.Column(db.String(12), default='draft')   # draft | finalized
    score_pct     = db.Column(db.Float)
    band          = db.Column(db.String(24))
    prev_eval_id  = db.Column(db.Integer)       # auto trend
    general_comment = db.Column(db.Text)
    version       = db.Column(db.Integer, default=1)
    supersedes_id = db.Column(db.Integer)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    updated_at    = db.Column(db.DateTime)
    employee  = db.relationship('User', foreign_keys=[employee_id])
    evaluator = db.relationship('User', foreign_keys=[evaluator_id])
    hotel     = db.relationship('Hotel')
    template  = db.relationship('EvalTemplate')
    scores    = db.relationship('EvalScore', backref='evaluation', cascade='all, delete-orphan')

class EvalScore(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluation.id'))
    criterion_id  = db.Column(db.Integer, db.ForeignKey('eval_criterion.id'))
    score         = db.Column(db.Float)
    comment       = db.Column(db.Text)

# ── Seed προτύπου (reference CONDIAN) ─────────────────────────────────────────
_CORE = [
    ('Γνώση & Κατανόηση της δουλειάς', 0.05), ('Συνέπεια στο ωράριο', 0.06),
    ('Εργάζεται οργανωμένα / ποιοτικά / παραγωγικά, με σωστή διαχείριση χρόνου', 0.05),
    ('Ακολουθεί διαδικασίες και ποιοτικές προδιαγραφές', 0.06),
    ('Φροντίζει τον εξοπλισμό / μηχανήματα και την ασφάλειά τους', 0.04),
    ('Υπευθυνότητα χωρίς συνεχή επίβλεψη', 0.04),
    ('Ευελιξία και προσαρμοστικότητα σε αλλαγές', 0.05),
    ('Αναπτύσσει πρωτοβουλίες & προβλέπει τις ανάγκες δουλειάς και τμήματος', 0.05),
    ('Επίδειξη ικανοτήτων εξέλιξης & προαγωγής', 0.05), ('Γνώση Η/Υ', 0.04),
    ('Προσωπική φροντίδα και υγιεινή', 0.06), ('Φροντίζει την στολή του / Φοράει την κονκάρδα', 0.05),
    ('Αποδοχή συμβουλών και οδηγιών', 0.03), ('Προθυμία για εκπαίδευση και για νέες γνώσεις', 0.05),
    ('Εθελοντισμός & Ευαισθησία', 0.05), ('Προσφορά βοήθειας, προθυμία, εξυπηρέτηση συναδέλφων', 0.03),
    ('Ευγένεια και φιλικότητα', 0.05), ('Εξυπηρέτηση και προθυμία προς τους πελάτες', 0.05),
    ('Εργασία κάτω από πίεση', 0.04),
]
_LANG = [('Γερμανικά', 0.02), ('Αγγλικά', 0.025), ('Γαλλικά', 0.025),
         ('Ιταλικά', 0.01), ('Ρώσικα', 0.01), ('Άλλες ξένες γλώσσες', 0.01)]

def ensure_eval_setup():
    """Seed του κοινού προτύπου CONDIAN (idempotent)."""
    try:
      with app.app_context():
        db.create_all()
        if EvalTemplate.query.first():
            return
        t = EvalTemplate(name='Πρότυπο CONDIAN', scope='general', scale_max=10, is_active=True)
        db.session.add(t); db.session.flush()
        i = 0
        for lab, w in _CORE:
            db.session.add(EvalCriterion(template_id=t.id, grp='Βασικά κριτήρια', label=lab, weight=w, sort=i, max_score=10)); i += 1
        for lab, w in _LANG:
            db.session.add(EvalCriterion(template_id=t.id, grp='Ξένες γλώσσες', label=lab, weight=w, sort=i, max_score=10)); i += 1
        db.session.commit()
        print('[evaluations] seeded πρότυπο CONDIAN (%d κριτήρια)' % (len(_CORE)+len(_LANG)))
    except Exception as e:
        db.session.rollback(); print('[evaluations] seed skipped:', e)

# ── Helpers ───────────────────────────────────────────────────────────────────
def band_for(pct):
    if pct is None: return '—'
    if pct >= 80: return 'Εξαιρετική'
    if pct >= 60: return 'Καλή'
    return 'Χρειάζεται προσοχή'

BAND_COLOR = {'Εξαιρετική': ('#dcfce7', '#16a34a'), 'Καλή': ('#fef3c7', '#b45309'),
              'Χρειάζεται προσοχή': ('#fee2e2', '#dc2626'), '—': ('#f1f5f9', '#64748b')}

def compute_pct(scores_map, criteria):
    """scores_map: {criterion_id: score}. Σταθμισμένο % με βάση weight & max_score."""
    num = den = 0.0
    for c in criteria:
        v = scores_map.get(c.id)
        if v is None or v == '':
            continue
        try: v = float(v)
        except (TypeError, ValueError): continue
        num += v * (c.weight or 0)
        den += (c.weight or 0) * (c.max_score or 10)
    if den <= 0: return None
    return round(num / den * 100, 1)

def _gen_code(ev):
    yr = ev.year or date.today().year
    seq = Evaluation.query.filter_by(year=yr).count() + 1
    return 'EVAL-%d-%04d' % (yr, seq)

def _dept_name(did):
    if not did: return ''
    try:
        from schedule import Department
        d = Department.query.get(did)
        return d.name if d else ''
    except Exception:
        return ''

def _employees():
    """Ενεργοί εργαζόμενοι από Μητρώο (για επιλογή + autofill)."""
    out = []
    try:
        from schedule import Department
        deps = {d.id: d.name for d in Department.query.all()}
    except Exception:
        deps = {}
    hotels = {h.id: h.name for h in Hotel.query.all()}
    spec = {}
    try:
        from payroll import EmployeePII
        for p in EmployeePII.query.all():
            spec[p.user_id] = getattr(p, 'ergani_specialty', None)
    except Exception:
        pass
    q = User.query.filter(User.is_active == True)
    for u in q.order_by(User.full_name).all():
        if getattr(u, 'employment_active', None) is False:
            continue
        out.append({'id': u.id, 'name': u.full_name,
                    'department_id': getattr(u, 'department_id', None),
                    'department': deps.get(getattr(u, 'department_id', None), ''),
                    'hotel_id': getattr(u, 'home_hotel_id', None),
                    'hotel': hotels.get(getattr(u, 'home_hotel_id', None), ''),
                    'specialty': spec.get(u.id, '') or ''})
    return out

def _auth():
    return is_admin()

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/dashboard/evaluations')
def evaluations_list():
    if not _auth():
        return redirect(url_for('login'))
    f_hotel = request.args.get('hotel_id', type=int)
    f_band  = request.args.get('band', '')
    f_period= request.args.get('period', '')
    q = (request.args.get('q') or '').strip()
    qry = Evaluation.query
    if f_hotel: qry = qry.filter(Evaluation.hotel_id == f_hotel)
    if f_band:  qry = qry.filter(Evaluation.band == f_band)
    if f_period:qry = qry.filter(Evaluation.period_label == f_period)
    items = qry.order_by(Evaluation.eval_date.desc(), Evaluation.id.desc()).limit(500).all()
    if q:
        ql = q.lower()
        items = [e for e in items if e.employee and ql in (e.employee.full_name or '').lower()]
    periods = [p[0] for p in db.session.query(Evaluation.period_label).distinct().all() if p[0]]
    hotels = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()
    return render_template('evaluations_list.html', items=items, hotels=hotels,
                           periods=periods, f_hotel=f_hotel, f_band=f_band, f_period=f_period, q=q,
                           band_color=BAND_COLOR, dept_name=_dept_name)

@app.route('/dashboard/evaluations/new', methods=['GET', 'POST'])
def evaluation_new():
    if not _auth():
        return redirect(url_for('login'))
    tmpl = EvalTemplate.query.filter_by(is_active=True).order_by(EvalTemplate.id).first()
    if request.method == 'POST' and tmpl:
        return _save_evaluation(None, tmpl)
    return render_template('evaluation_form.html', ev=None, tmpl=tmpl,
                           criteria=tmpl.criteria if tmpl else [], employees=_employees(),
                           scores={}, today=date.today())

@app.route('/dashboard/evaluations/<int:eid>')
def evaluation_view(eid):
    if not _auth():
        return redirect(url_for('login'))
    ev = Evaluation.query.get_or_404(eid)
    smap = {s.criterion_id: s for s in ev.scores}
    prev = Evaluation.query.get(ev.prev_eval_id) if ev.prev_eval_id else None
    return render_template('evaluation_view.html', ev=ev, smap=smap, prev=prev,
                           band_color=BAND_COLOR, dept_name=_dept_name,
                           criteria=ev.template.criteria if ev.template else [])

@app.route('/dashboard/evaluations/<int:eid>/edit', methods=['GET', 'POST'])
def evaluation_edit(eid):
    if not _auth():
        return redirect(url_for('login'))
    ev = Evaluation.query.get_or_404(eid)
    tmpl = ev.template or EvalTemplate.query.filter_by(is_active=True).first()
    if request.method == 'POST':
        return _save_evaluation(ev, tmpl)
    scores = {s.criterion_id: s for s in ev.scores}
    return render_template('evaluation_form.html', ev=ev, tmpl=tmpl,
                           criteria=tmpl.criteria if tmpl else [], employees=_employees(),
                           scores=scores, today=date.today())

@app.route('/dashboard/evaluations/<int:eid>/delete', methods=['POST'])
def evaluation_delete(eid):
    if not _auth():
        return redirect(url_for('login'))
    ev = Evaluation.query.get_or_404(eid)
    db.session.delete(ev); db.session.commit()
    log_activity('evaluation_delete', '#%d' % eid)
    return redirect(url_for('evaluations_list') + '?embed=1')

def _save_evaluation(ev, tmpl):
    fm = request.form
    finalize = fm.get('action') == 'finalize'
    emp_id = fm.get('employee_id', type=int)
    if not emp_id or not tmpl:
        return redirect(url_for('evaluation_new') + '?embed=1')
    user = current_user()
    criteria = tmpl.criteria
    scores_map = {}
    for c in criteria:
        raw = fm.get('score_%d' % c.id, '')
        if raw != '':
            try: scores_map[c.id] = float(raw)
            except ValueError: pass
    pct = compute_pct(scores_map, criteria)
    yr = fm.get('year', type=int) or date.today().year
    # ΟΛΑ τα queries ΠΡΙΝ δημιουργήσουμε το νέο record (αποφυγή autoflush half-built)
    emp = User.query.get(emp_id)
    exclude_code = ev.code if ev else None
    _pq = Evaluation.query.filter(Evaluation.employee_id == emp_id, Evaluation.status == 'finalized')
    if exclude_code:
        _pq = _pq.filter(Evaluation.code != exclude_code)
    prev = _pq.order_by(Evaluation.eval_date.desc()).first()
    # versioning: αν επεξεργαζόμαστε ΟΡΙΣΤΙΚΟΠΟΙΗΜΕΝΗ → νέα version
    if ev and ev.status == 'finalized':
        old = ev
        ev = Evaluation(supersedes_id=old.id, version=(old.version or 1) + 1, code=old.code)
        db.session.add(ev)
    if ev is None:
        ev = Evaluation(); db.session.add(ev)
    ev.employee_id = emp_id
    ev.evaluator_id = user.id if user else None
    ev.hotel_id = getattr(emp, 'home_hotel_id', None)
    ev.department_id = getattr(emp, 'department_id', None)
    ev.template_id = tmpl.id
    ev.period_label = (fm.get('period_label') or '').strip()[:40]
    ev.year = yr
    try:
        ev.eval_date = datetime.strptime(fm.get('eval_date', ''), '%Y-%m-%d').date()
    except ValueError:
        ev.eval_date = date.today()
    ev.score_pct = pct
    ev.band = band_for(pct)
    ev.prev_eval_id = prev.id if prev else None
    ev.general_comment = (fm.get('general_comment') or '')[:4000]
    ev.status = 'finalized' if finalize else 'draft'
    ev.updated_at = datetime.now()
    db.session.flush()
    if not ev.code:
        ev.code = _gen_code(ev)
    # scores
    for s in list(ev.scores):
        db.session.delete(s)
    for c in criteria:
        if c.id in scores_map:
            db.session.add(EvalScore(evaluation_id=ev.id, criterion_id=c.id,
                                     score=scores_map[c.id],
                                     comment=(fm.get('comment_%d' % c.id) or '')[:1000]))
    db.session.commit()
    log_activity('evaluation_save', '%s %s' % (ev.code, ev.status))
    return redirect(url_for('evaluation_view', eid=ev.id) + '?embed=1')

@app.route('/dashboard/evaluations/<int:eid>/export.xlsx')
def evaluation_export(eid):
    if not _auth():
        return redirect(url_for('login'))
    ev = Evaluation.query.get_or_404(eid)
    import io, openpyxl
    from openpyxl.styles import Font, Alignment
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Αξιολόγηση'
    smap = {s.criterion_id: s for s in ev.scores}
    emp = ev.employee
    ws['A1'] = 'CONDIAN HOTELS'; ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = 'Employee Evaluation Form – Αξιολόγηση Εργαζομένου'; ws['A2'].font = Font(bold=True)
    meta = [('ΞΕΝΟΔΟΧΕΙΑΚΗ ΜΟΝΑΔΑ', ev.hotel.name if ev.hotel else ''),
            ('ΟΝΟΜΑΤΕΠΩΝΥΜΟ', emp.full_name if emp else ''),
            ('ΤΜΗΜΑ', _dept_name(ev.department_id)),
            ('ΠΕΡΙΟΔΟΣ', '%s %s' % (ev.period_label or '', ev.year or '')),
            ('ΗΜΕΡΟΜΗΝΙΑ ΑΞΙΟΛΟΓΗΣΗΣ', ev.eval_date.strftime('%d/%m/%Y') if ev.eval_date else ''),
            ('ΑΞΙΟΛΟΓΗΤΗΣ', ev.evaluator.full_name if ev.evaluator else ''),
            ('ΚΩΔΙΚΟΣ', ev.code)]
    r = 4
    for k, v in meta:
        ws.cell(r, 2, k); ws.cell(r, 3, v); r += 1
    r += 1
    hdr = ['Α/Α', 'ΚΡΙΤΗΡΙΑ', 'ΒΑΘΜΟΛΟΓΙΑ', 'ΣΥΝΤΕΛΕΣΤΗΣ', 'ΣΧΟΛΙΟ']
    for j, h in enumerate(hdr): c = ws.cell(r, j + 1, h); c.font = Font(bold=True)
    r += 1; i = 1
    for crit in (ev.template.criteria if ev.template else []):
        s = smap.get(crit.id)
        ws.cell(r, 1, i); ws.cell(r, 2, crit.label)
        ws.cell(r, 3, (s.score if s else None)); ws.cell(r, 4, crit.weight)
        ws.cell(r, 5, (s.comment if s else '')); r += 1; i += 1
    r += 1
    ws.cell(r, 2, 'ΒΑΘΜΟΛΟΓΙΑ %'); c = ws.cell(r, 3, (ev.score_pct or 0)); c.font = Font(bold=True)
    ws.cell(r + 1, 2, 'ΑΞΙΟΛΟΓΗΣΗ'); ws.cell(r + 1, 3, ev.band or '')
    ws.cell(r + 2, 2, 'ΓΕΝΙΚΟ ΣΧΟΛΙΟ'); ws.cell(r + 2, 3, ev.general_comment or '')
    ws.column_dimensions['B'].width = 55
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    log_activity('evaluation_export', ev.code)
    fname = 'evaluation-%s.xlsx' % (ev.code or ev.id)
    return Response(buf.read(),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename=' + fname})

print('[evaluations] module loaded (Αξιολόγηση Προσωπικού Φ1)')
