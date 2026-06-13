# -*- coding: utf-8 -*-
"""
Εστία — Module Βλαβοληψία (v12.14, Φάση 1)
==========================================
Plug-in: γίνεται `import faults` από το ΤΕΛΟΣ του app.py (αφού οριστούν app/db/helpers,
πριν το init_db() ώστε το create_all να πιάσει τους νέους πίνακες).
Πηγή προδιαγραφών: 02_ΒΛΑΒΟΛΗΨΙΑ_MODULE/.
"""
import os, csv
from datetime import datetime
from flask import request, redirect, url_for, render_template, session, jsonify
from app import (app, db, current_user, is_admin, allowed_hotels, notify, notify_admins,
                 log_activity, Hotel, User, Pool, Setting, ROLE_RANK, role_rank, BASE_DIR)

# ── Σταθερές ─────────────────────────────────────────────────────────────────
PRIORITIES = ('Υψηλή', 'Κανονική', 'Χαμηλή')
STATUSES   = ('pending_assign', 'auto_assigned', 'assigned', 'in_progress',
              'paused', 'done', 'not_done', 'winter', 'resubmitted')
STATUS_LABELS = {
    'pending_assign': 'Αναμένει ανάθεση', 'auto_assigned': 'Αυτόματη ανάθεση',
    'assigned': 'Ανατέθηκε', 'in_progress': 'Προς διεκπεραίωση', 'paused': 'Σε παύση',
    'done': 'Ολοκληρώθηκε', 'not_done': 'Δεν έγινε', 'winter': 'Για χειμώνα',
    'resubmitted': 'Υποβλήθηκε ξανά',
}
STATUS_COLOR = {  # bg / text (light· dark μέσω estia-theme badges)
    'pending_assign': ('#f1f5f9', '#64748b'), 'auto_assigned': ('#e0f2fe', '#0369a1'),
    'assigned': ('#dbeafe', '#185FA5'), 'in_progress': ('#fef3c7', '#b45309'),
    'paused': ('#e2e8f0', '#475569'), 'done': ('#dcfce7', '#16a34a'),
    'not_done': ('#fee2e2', '#dc2626'), 'winter': ('#cffafe', '#0e7490'),
    'resubmitted': ('#f3e8ff', '#7e22ce'),
}
PRIORITY_COLOR = {'Υψηλή': ('#fee2e2', '#dc2626'), 'Κανονική': ('#fef3c7', '#b45309'), 'Χαμηλή': ('#f1f5f9', '#64748b')}
TERMINAL = ('done', 'not_done', 'resubmitted')
SPECIALTIES = ('Υδραυλικός', 'Ηλεκτρολόγος', 'Ψυκτικός', 'Κηπουρός',
               'Ελαιοχρωματιστής', 'Συντηρητής', 'Εξωτερικός Συνεργάτης')
TRANSITIONS = {
    'pending_assign': ('auto_assigned', 'assigned'),
    'auto_assigned':  ('assigned', 'in_progress', 'done', 'not_done', 'winter'),
    'assigned':       ('in_progress', 'paused', 'done', 'not_done', 'winter'),
    'in_progress':    ('paused', 'done', 'not_done', 'winter', 'resubmitted'),
    'paused':         ('in_progress', 'done', 'not_done'),
    'winter':         ('pending_assign', 'in_progress'),
    'done':           ('resubmitted',),
    'not_done':       ('resubmitted',),
    'resubmitted':    (),
}
HOTEL_PREFIX = {
    'Asterias Village Resort': 'AST', 'Sergios Hotel': 'SRG',
    'Central Hersonissos Hotel': 'CNT', 'Piskopiano Village': 'PSV', 'Iro Hotel': 'IRO',
}
# χάρτης level-1 κλάδου → ειδικότητα (αρχικό· admin-editable στη Φάση 2)
ROOT_SPECIALTY = {
    'Α. ΣΥΝΤΗΡΗΣΗ': 'Συντηρητής', 'Β. ΗΛΕΚΤΡΟΛΟΓΙΚΑ': 'Ηλεκτρολόγος',
    'C. ΥΔΡΑΥΛΙΚΑ': 'Υδραυλικός', 'D. ΕΠΙΤΡΑΠΕΖΙΟΣ ΕΞΟΠΛΙΣΜΟΣ': 'Ψυκτικός',
    'E. ΕΞΩΤΕΡΙΚΟΙ ΣΥΝΕΡΓΑΤΕΣ': 'Εξωτερικός Συνεργάτης',
}
SLA_DEFAULTS = {'Υψηλή': 120, 'Κανονική': 360, 'Χαμηλή': 1440}

# ── Μοντέλα ──────────────────────────────────────────────────────────────────
class FaultCategory(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('fault_category.id'), nullable=True)
    hotel_id  = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=True)
    name      = db.Column(db.String(160), nullable=False)
    level     = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    sort      = db.Column(db.Integer, default=0)
    children  = db.relationship('FaultCategory', backref=db.backref('parent', remote_side=[id]))

class FaultLocation(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('fault_location.id'), nullable=True)
    hotel_id  = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    name      = db.Column(db.String(120), nullable=False)
    kind      = db.Column(db.String(12), default='χώρος')
    is_active = db.Column(db.Boolean, default=True)
    children  = db.relationship('FaultLocation', backref=db.backref('parent', remote_side=[id]))

class Specialty(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(40), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort      = db.Column(db.Integer, default=0)

class CategorySpecialty(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('fault_category.id'), nullable=False)
    specialty   = db.Column(db.String(40), nullable=False)

class UserSpecialty(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    specialty = db.Column(db.String(40), nullable=False)

class Fault(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(24), unique=True, index=True)
    type          = db.Column(db.String(12), default='βλάβη')
    hotel_id      = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    pool_id       = db.Column(db.Integer, db.ForeignKey('pool.id'), nullable=True)
    location_id   = db.Column(db.Integer, db.ForeignKey('fault_location.id'), nullable=True)
    room_id       = db.Column(db.Integer, db.ForeignKey('fault_location.id'), nullable=True)
    geo_lat       = db.Column(db.Float, nullable=True)
    geo_lng       = db.Column(db.Float, nullable=True)
    category_id   = db.Column(db.Integer, db.ForeignKey('fault_category.id'), nullable=True)
    description   = db.Column(db.Text, nullable=False)
    priority      = db.Column(db.String(10), default='Κανονική')
    tag           = db.Column(db.String(40), nullable=True)
    due_at        = db.Column(db.DateTime, nullable=True)
    status        = db.Column(db.String(16), default='pending_assign')
    source        = db.Column(db.String(20), default='Ενδοξενοδοχειακά')
    submitted_by      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_by      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    cover_image   = db.Column(db.Text, nullable=True)
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, nullable=True)
    completed_at  = db.Column(db.DateTime, nullable=True)
    resolution_seconds = db.Column(db.Integer, nullable=True)
    imported_from = db.Column(db.String(30), nullable=True)
    legacy_from = db.Column(db.String(120)); legacy_assignee = db.Column(db.String(120))
    legacy_completed_by = db.Column(db.String(120)); legacy_category = db.Column(db.String(200))
    legacy_location = db.Column(db.String(200)); legacy_room = db.Column(db.String(80))
    category  = db.relationship('FaultCategory')
    hotel     = db.relationship('Hotel')
    submitter = db.relationship('User', foreign_keys=[submitted_by])
    assignee  = db.relationship('User', foreign_keys=[assigned_user_id])
    def can_transition(self, to):
        return to in TRANSITIONS.get(self.status, ())

class FaultCandidate(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    fault_id  = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    specialty = db.Column(db.String(40), nullable=True)
    user      = db.relationship('User')

class FaultChangeLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    fault_id    = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    change_type = db.Column(db.String(12))
    field       = db.Column(db.String(40))
    from_value  = db.Column(db.String(200))
    to_value    = db.Column(db.String(200))
    by_user_id  = db.Column(db.Integer, db.ForeignKey('user.id'))
    at          = db.Column(db.DateTime, default=datetime.utcnow)
    by_user     = db.relationship('User')

class FaultComment(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    fault_id   = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    audience   = db.Column(db.String(12), default='διοίκηση')
    text       = db.Column(db.Text)
    file_url   = db.Column(db.Text, nullable=True)
    by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    at         = db.Column(db.DateTime, default=datetime.utcnow)
    by_user    = db.relationship('User')

class FaultAttachment(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    fault_id   = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    url        = db.Column(db.Text, nullable=False)
    by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    at         = db.Column(db.DateTime, default=datetime.utcnow)

class FaultTag(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(40), unique=True, nullable=False)
    color     = db.Column(db.String(10), default='#b91c1c')
    is_active = db.Column(db.Boolean, default=True)

class SLATarget(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    scope   = db.Column(db.String(10), default='priority')
    key     = db.Column(db.String(40), nullable=False)
    minutes = db.Column(db.Integer, nullable=False)

# ── Helpers ──────────────────────────────────────────────────────────────────
def gen_code(hotel):
    year = datetime.utcnow().year
    prefix = HOTEL_PREFIX.get(hotel.name, 'GEN')
    last = (Fault.query.filter(Fault.code.like('%s-%d-%%' % (prefix, year)))
                       .order_by(Fault.id.desc()).first())
    try:
        seq = (int(last.code.split('-')[2]) + 1) if last else 1
    except Exception:
        seq = (Fault.query.filter(Fault.code.like('%s-%d-%%' % (prefix, year))).count()) + 1
    return '%s-%d-%06d' % (prefix, year, seq)

def log_change(fault, change_type, field, frm, to, user_id):
    db.session.add(FaultChangeLog(fault_id=fault.id, change_type=change_type, field=field,
                                  from_value=str(frm)[:200], to_value=str(to)[:200], by_user_id=user_id))

def cat_root_name(cat):
    seen = 0
    while cat and cat.parent_id and seen < 6:
        cat = FaultCategory.query.get(cat.parent_id); seen += 1
    return cat.name if cat else None

def user_specialty_names(user):
    return [us.specialty for us in UserSpecialty.query.filter_by(user_id=user.id).all()]

def auto_assign(fault):
    """Γέμισε δεξαμενή υποψηφίων από κατηγορία→ειδικότητα (ίδιο ξενοδοχείο)."""
    specs = [cs.specialty for cs in CategorySpecialty.query.filter_by(category_id=fault.category_id).all()]
    if not specs and fault.category_id:                       # δοκίμασε τον level-1 κλάδο
        root = cat_root_name(FaultCategory.query.get(fault.category_id))
        sp = ROOT_SPECIALTY.get(root)
        if sp:
            specs = [sp]
    if not specs:
        fault.status = 'pending_assign'
        return
    fault.status = 'auto_assigned'
    seen = set()
    for sp in specs:
        if sp in seen:
            continue
        seen.add(sp)
        db.session.add(FaultCandidate(fault_id=fault.id, specialty=sp))
        for us in UserSpecialty.query.filter_by(specialty=sp).all():
            u = User.query.get(us.user_id)
            if u and u.is_active:
                db.session.add(FaultCandidate(fault_id=fault.id, user_id=u.id))

def visible_faults_query(user):
    hids = [h.id for h in allowed_hotels(user)]
    q = Fault.query.filter(Fault.hotel_id.in_(hids or [-1]))
    if not is_admin():
        my_specs = user_specialty_names(user)
        pool_ids = [c.fault_id for c in FaultCandidate.query.filter(
            (FaultCandidate.user_id == user.id) |
            (FaultCandidate.specialty.in_(my_specs or ['__none__']))).all()]
        q = q.filter((Fault.submitted_by == user.id) | (Fault.assigned_user_id == user.id) |
                     (Fault.id.in_(pool_ids or [-1])))
    return q

def can_view(user, f):
    if f.hotel_id not in [h.id for h in allowed_hotels(user)]:
        return False
    if is_admin():
        return True
    if f.submitted_by == user.id or f.assigned_user_id == user.id:
        return True
    my = set(user_specialty_names(user))
    for c in FaultCandidate.query.filter_by(fault_id=f.id).all():
        if c.user_id == user.id or (c.specialty and c.specialty in my):
            return True
    return False

# ── Seed (idempotent) ────────────────────────────────────────────────────────
def seed_faults():
    with app.app_context():
        try:
            if Setting.query.get('seeded_faults_v1'):
                return
            # ειδικότητες
            for i, sp in enumerate(SPECIALTIES):
                if not Specialty.query.filter_by(name=sp).first():
                    db.session.add(Specialty(name=sp, sort=i))
            # SLA
            for k, m in SLA_DEFAULTS.items():
                if not SLATarget.query.filter_by(scope='priority', key=k).first():
                    db.session.add(SLATarget(scope='priority', key=k, minutes=m))
            if not Setting.query.get('fault_stale_days'):
                db.session.add(Setting(key='fault_stale_days', value='60'))
            db.session.commit()
            # κατηγορίες από CSV (δέντρο 3 επιπέδων, dedup)
            path = os.path.join(BASE_DIR, 'seed', 'fault_categories.csv')
            if os.path.exists(path) and FaultCategory.query.count() == 0:
                roots = {}; mids = {}
                with open(path, encoding='utf-8') as fh:
                    rows = list(csv.DictReader(fh))
                for r in rows:
                    l1 = (r.get('level1') or '').strip()
                    l2 = (r.get('level2') or '').strip()
                    l3 = (r.get('level3') or '').strip()
                    try: occ = int(r.get('occurrences') or 0)
                    except Exception: occ = 0
                    if not l1:
                        continue
                    if l1 not in roots:
                        c = FaultCategory(name=l1, level=1, sort=0)
                        db.session.add(c); db.session.flush(); roots[l1] = c
                    if l2:
                        key2 = (l1, l2)
                        if key2 not in mids:
                            c2 = FaultCategory(name=l2, level=2, parent_id=roots[l1].id, sort=-occ)
                            db.session.add(c2); db.session.flush(); mids[key2] = c2
                        if l3:
                            c3 = FaultCategory(name=l3, level=3, parent_id=mids[key2].id, sort=-occ)
                            db.session.add(c3)
                db.session.commit()
                # χάρτης κατηγορία(level-1)→ειδικότητα
                for name, sp in ROOT_SPECIALTY.items():
                    root = FaultCategory.query.filter_by(name=name, level=1).first()
                    if root and not CategorySpecialty.query.filter_by(category_id=root.id).first():
                        db.session.add(CategorySpecialty(category_id=root.id, specialty=sp))
                db.session.commit()
            db.session.add(Setting(key='seeded_faults_v1', value='1'))
            db.session.commit()
            print('[faults] seeded specialties/SLA/categories (%d)' % FaultCategory.query.count())
        except Exception as e:
            db.session.rollback(); print('[faults] seed skipped:', e)

# ── Routes ───────────────────────────────────────────────────────────────────
def _ctx_lists(user):
    hotels = allowed_hotels(user)
    cats = FaultCategory.query.filter_by(is_active=True).order_by(FaultCategory.level, FaultCategory.sort, FaultCategory.name).all()
    return hotels, cats

@app.route('/fault', methods=['GET', 'POST'])
def fault_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    hotels, cats = _ctx_lists(user)
    if request.method == 'POST':
        desc = (request.form.get('message') or request.form.get('description') or '').strip()
        hid = request.form.get('hotel_id', type=int)
        hotel = Hotel.query.get(hid) if hid else (hotels[0] if hotels else None)
        if not desc or not hotel:
            return render_template('fault_submit.html', done=False, error='Συμπλήρωσε ξενοδοχείο & περιγραφή',
                                   hotels=hotels, cats=cats, priorities=PRIORITIES, user=user)
        f = Fault(code=gen_code(hotel), hotel_id=hotel.id,
                  category_id=request.form.get('category_id', type=int) or None,
                  description=desc, priority=request.form.get('priority', 'Κανονική'),
                  submitted_by=user.id, source='Ενδοξενοδοχειακά', status='pending_assign')
        db.session.add(f); db.session.flush()
        log_change(f, 'πεδίο', 'δημιουργία', '', f.code, user.id)
        auto_assign(f)
        db.session.commit()
        log_activity('fault_report', f.code)
        notify_admins('Νέα βλάβη: %s' % f.code, '/dashboard/fault/%d?embed=1' % f.id)
        return render_template('fault_submit.html', done=True, code=f.code, hotels=hotels, cats=cats,
                               priorities=PRIORITIES, user=user)
    return render_template('fault_submit.html', done=False, hotels=hotels, cats=cats,
                           priorities=PRIORITIES, user=user)

@app.route('/dashboard/faults')
def faults_inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    q = visible_faults_query(user)
    f_hotel = request.args.get('hotel_id', type=int)
    f_status = request.args.get('status')
    f_priority = request.args.get('priority')
    f_assignee = request.args.get('assigned_user_id', type=int)
    search = (request.args.get('q') or '').strip()
    if f_hotel:    q = q.filter(Fault.hotel_id == f_hotel)
    if f_status:   q = q.filter(Fault.status == f_status)
    if f_priority: q = q.filter(Fault.priority == f_priority)
    if f_assignee: q = q.filter(Fault.assigned_user_id == f_assignee)
    if search:     q = q.filter((Fault.description.ilike('%%%s%%' % search)) | (Fault.code.ilike('%%%s%%' % search)))
    faults = q.order_by(Fault.id.desc()).limit(400).all()
    hotels = allowed_hotels(user)
    users = User.query.filter_by(is_active=True, approved=True).order_by(User.full_name).all()
    open_n = sum(1 for f in faults if f.status not in TERMINAL)
    return render_template('faults_list.html', faults=faults, hotels=hotels, users=users,
                           STATUS_LABELS=STATUS_LABELS, STATUS_COLOR=STATUS_COLOR, PRIORITY_COLOR=PRIORITY_COLOR,
                           PRIORITIES=PRIORITIES, STATUSES=STATUSES, is_admin=is_admin(),
                           f_hotel=f_hotel, f_status=f_status, f_priority=f_priority, f_assignee=f_assignee,
                           search=search, open_n=open_n, user=user)

@app.route('/dashboard/fault/<int:fid>')
def fault_detail(fid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    f = Fault.query.get_or_404(fid)
    if not can_view(user, f):
        return redirect(url_for('faults_inbox') + '?embed=1')
    logs = FaultChangeLog.query.filter_by(fault_id=fid).order_by(FaultChangeLog.at).all()
    comments = FaultComment.query.filter_by(fault_id=fid).order_by(FaultComment.at).all()
    if not is_admin() and f.submitted_by == user.id and f.assigned_user_id != user.id:
        comments = [c for c in comments if c.audience == 'υποβολέας']   # ο απλός υποβολέας δεν βλέπει «προς Διοίκηση»
    files = FaultAttachment.query.filter_by(fault_id=fid).all()
    cands = FaultCandidate.query.filter_by(fault_id=fid).all()
    users = User.query.filter_by(is_active=True, approved=True).order_by(User.full_name).all() if is_admin() else []
    allowed = TRANSITIONS.get(f.status, ())
    return render_template('fault_detail.html', f=f, logs=logs, comments=comments, files=files,
                           candidates=cands, users=users, allowed=allowed, is_admin=is_admin(),
                           STATUS_LABELS=STATUS_LABELS, STATUS_COLOR=STATUS_COLOR, PRIORITY_COLOR=PRIORITY_COLOR,
                           cat_path=_cat_path(f.category), user=user, me=user)

def _cat_path(cat):
    parts = []; seen = 0
    while cat and seen < 6:
        parts.append(cat.name); cat = FaultCategory.query.get(cat.parent_id) if cat.parent_id else None; seen += 1
    return ' › '.join(reversed(parts))

@app.route('/dashboard/fault/<int:fid>/status', methods=['POST'])
def fault_set_status(fid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    f = Fault.query.get_or_404(fid)
    if not can_view(user, f):
        return redirect(url_for('faults_inbox') + '?embed=1')
    to = request.form.get('to')
    if not f.can_transition(to):
        return redirect(url_for('fault_detail', fid=fid) + '?embed=1&err=1')
    frm = f.status; f.status = to; f.updated_at = datetime.utcnow()
    if to == 'done':
        f.completed_at = datetime.utcnow(); f.completed_by = user.id
        if f.submitted_at:
            f.resolution_seconds = int((f.completed_at - f.submitted_at).total_seconds())
    log_change(f, 'κατάσταση', 'status', STATUS_LABELS.get(frm, frm), STATUS_LABELS.get(to, to), user.id)
    db.session.commit()
    if f.submitted_by:
        notify(f.submitted_by, 'Βλάβη %s: %s' % (f.code, STATUS_LABELS.get(to, to)), '/dashboard/fault/%d?embed=1' % f.id)
    return redirect(url_for('fault_detail', fid=fid) + '?embed=1')

@app.route('/dashboard/fault/<int:fid>/take', methods=['POST'])
def fault_take(fid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    f = Fault.query.get_or_404(fid)
    if not can_view(user, f):
        return redirect(url_for('faults_inbox') + '?embed=1')
    f.assigned_user_id = user.id; f.updated_at = datetime.utcnow()
    log_change(f, 'σχέση', 'Ανάθεση σε', '', user.full_name, user.id)
    if f.can_transition('assigned'):
        f.status = 'assigned'
    elif f.can_transition('in_progress'):
        f.status = 'in_progress'
    db.session.commit()
    return redirect(url_for('fault_detail', fid=fid) + '?embed=1')

@app.route('/dashboard/fault/<int:fid>/assign', methods=['POST'])
def fault_assign(fid):
    if not is_admin():
        return redirect(url_for('login'))
    user = current_user()
    f = Fault.query.get_or_404(fid)
    uid = request.form.get('assignee_id', type=int)
    target = User.query.get(uid) if uid else None
    f.assigned_user_id = uid or None; f.updated_at = datetime.utcnow()
    log_change(f, 'σχέση', 'Ανάθεση σε', '', target.full_name if target else '—', user.id)
    if target and f.can_transition('assigned'):
        f.status = 'assigned'
    db.session.commit()
    if uid:
        notify(uid, 'Σου ανατέθηκε η βλάβη %s' % f.code, '/dashboard/fault/%d?embed=1' % f.id)
    return redirect(url_for('fault_detail', fid=fid) + '?embed=1')

@app.route('/dashboard/fault/<int:fid>/comment', methods=['POST'])
def fault_comment(fid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = current_user()
    f = Fault.query.get_or_404(fid)
    if not can_view(user, f):
        return redirect(url_for('faults_inbox') + '?embed=1')
    audience = request.form.get('audience', 'διοίκηση')
    if audience not in ('διοίκηση', 'υποβολέας'):
        audience = 'διοίκηση'
    text = (request.form.get('text') or '').strip()
    if text:
        db.session.add(FaultComment(fault_id=fid, audience=audience, text=text, by_user_id=user.id))
        db.session.commit()
        if audience == 'υποβολέας' and f.submitted_by:
            notify(f.submitted_by, 'Σχόλιο στη βλάβη %s' % f.code, '/dashboard/fault/%d?embed=1' % f.id)
    return redirect(url_for('fault_detail', fid=fid) + '?embed=1')

@app.route('/dashboard/faults/bulk', methods=['POST'])
def faults_bulk():
    if not is_admin():
        return redirect(url_for('login'))
    user = current_user()
    action = request.form.get('action')
    ids = request.form.getlist('fault_ids')
    if ids == ['all'] or request.form.get('all') == '1':
        ids = [str(f.id) for f in visible_faults_query(user).all()]
    n = 0
    for sid in ids:
        try: f = Fault.query.get(int(sid))
        except Exception: f = None
        if not f:
            continue
        if action == 'complete' and f.status not in TERMINAL:
            frm = f.status; f.status = 'done'
            f.completed_at = datetime.utcnow(); f.completed_by = user.id
            if f.submitted_at:
                f.resolution_seconds = int((f.completed_at - f.submitted_at).total_seconds())
            log_change(f, 'κατάσταση', 'status', STATUS_LABELS.get(frm, frm), 'Ολοκληρώθηκε', user.id); n += 1
        elif action == 'assign':
            uid = request.form.get('assignee_id', type=int)
            f.assigned_user_id = uid or None
            if uid and f.can_transition('assigned'):
                f.status = 'assigned'
            log_change(f, 'σχέση', 'Ανάθεση σε', '', uid or '—', user.id); n += 1
    db.session.commit()
    log_activity('faults_bulk', '%s x%d' % (action, n))
    return redirect(url_for('faults_inbox') + '?embed=1')

print('[faults] module loaded')
