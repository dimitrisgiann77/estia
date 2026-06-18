# -*- coding: utf-8 -*-
"""People core (v12.71) — γενικές υπηρεσίες προφίλ:
 - ProfileEvent: ιστορικότητα/audit ανά οντότητα (employee τώρα, contact αργότερα/CRM)
 - AttentionFlag: γενικό κέντρο «Χρειάζονται προσοχή» (κάθε module σπρώχνει flags)
Plug-in όπως faults/surveys: import από το ΤΕΛΟΣ του app.py, ΠΡΙΝ το init_db().
"""
from datetime import datetime
from flask import request, redirect, url_for, render_template
from app import app, db, current_user, is_admin, log_activity


def _actor():
    try:
        cu = current_user(); return cu.id if cu else None
    except Exception:
        return None


class ProfileEvent(db.Model):
    """Χρονολόγιο γεγονότων ανά προφίλ (audit). entity_type: 'employee'|'contact'..."""
    id          = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), index=True, default='employee')
    entity_id   = db.Column(db.Integer, index=True)
    event       = db.Column(db.String(40))     # created/import/match/merge/assignment/edit/status
    detail      = db.Column(db.Text)
    actor_id    = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.now)


class AttentionFlag(db.Model):
    """Σημαίες «χρειάζονται προσοχή». Idempotent ανά (entity_type, entity_id, flag_type) ανοιχτή."""
    id          = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), index=True, default='employee')
    entity_id   = db.Column(db.Integer, index=True)
    flag_type   = db.Column(db.String(40), index=True)   # no_key/no_afm/no_code/assignment_no_date/possible_dup/orphan
    severity    = db.Column(db.String(10), default='warn')  # info/warn/high
    detail      = db.Column(db.Text)
    resolved    = db.Column(db.Boolean, default=False, index=True)
    created_at  = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer)


# ── ΕΤΙΚΕΤΕΣ ────────────────────────────────────────────────────────────────
FLAG_LABELS = {
    'no_key':            'Χωρίς κλειδί (ΑΦΜ/Κωδ.)',
    'no_afm':            'Λείπει ΑΦΜ',
    'no_code':           'Λείπει Κωδ. Εργαζομένου',
    'orphan':            'Ορφανό (εκτός Λογιστηρίου)',
    'assignment_no_date':'Ανάθεση χωρίς ημερομηνία',
    'possible_dup':      'Πιθανή διπλοεγγραφή',
    'missing_amka':      'Λείπει ΑΜΚΑ',
    'missing_ika':       'Λείπει Α.Μ.ΙΚΑ',
    'missing_father':    'Λείπει πατρώνυμο',
    'missing_iban':      'Λείπει IBAN',
    'missing_bank':      'Λείπει τράπεζα',
    'missing_hire':      'Λείπει ημ. πρόσληψης',
    'missing_specialty': 'Λείπει ειδικότητα (Λογιστήριο)',
    'missing_position':  'Λείπει θέση (Management)',
    'missing_phone':     'Λείπει τηλέφωνο',
    'missing_email':     'Λείπει email',
    'missing_cc':        'Λείπει κέντρο κόστους',
    'missing_assignment':'Χωρίς ανάθεση Management',
    'missing_agreement': 'Χωρίς συμφωνία/ποσό',
}
EVENT_LABELS = {
    'created':   'Δημιουργία προφίλ',
    'import':    'Εισαγωγή',
    'match':     'Ταίριασμα κλειδιού',
    'merge':     'Συγχώνευση (merge)',
    'assignment':'Ανάθεση',
    'edit':      'Επεξεργασία στοιχείων',
    'status':    'Αλλαγή κατάστασης',
    'flag':      'Σημαία προσοχής',
}


# ── HELPERS (να τα καλούν τα modules) ───────────────────────────────────────
def log_event(entity_id, event, detail='', entity_type='employee', actor_id=None):
    if actor_id is None:
        actor_id = _actor()
    db.session.add(ProfileEvent(entity_type=entity_type, entity_id=entity_id,
                                event=event, detail=(detail or '')[:2000], actor_id=actor_id))


def add_flag(entity_id, flag_type, severity='warn', detail='', entity_type='employee'):
    ex = (AttentionFlag.query
          .filter_by(entity_type=entity_type, entity_id=entity_id, flag_type=flag_type, resolved=False)
          .first())
    if ex:
        ex.detail = (detail or '')[:500]; return ex
    f = AttentionFlag(entity_type=entity_type, entity_id=entity_id, flag_type=flag_type,
                      severity=severity, detail=(detail or '')[:500])
    db.session.add(f); return f


def clear_flags(entity_id, flag_type=None, entity_type='employee'):
    q = AttentionFlag.query.filter_by(entity_type=entity_type, entity_id=entity_id, resolved=False)
    if flag_type:
        q = q.filter_by(flag_type=flag_type)
    aid = _actor()
    for f in q.all():
        f.resolved = True; f.resolved_at = datetime.now(); f.resolved_by = aid


def events_for(entity_id, entity_type='employee'):
    return (ProfileEvent.query
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(ProfileEvent.created_at.desc(), ProfileEvent.id.desc()).all())


def open_flags_for(entity_id, entity_type='employee'):
    return (AttentionFlag.query
            .filter_by(entity_type=entity_type, entity_id=entity_id, resolved=False).all())


# ── ΣΕΛΙΔΑ «ΧΡΕΙΑΖΟΝΤΑΙ ΠΡΟΣΟΧΗ» ────────────────────────────────────────────
@app.route('/dashboard/attention')
def attention_center():
    if not is_admin():
        return redirect(url_for('login'))
    etype = request.args.get('entity', 'employee')
    ftype = request.args.get('flag')
    q = AttentionFlag.query.filter_by(resolved=False, entity_type=etype)
    if ftype:
        q = q.filter_by(flag_type=ftype)
    flags = q.order_by(AttentionFlag.flag_type, AttentionFlag.id).limit(800).all()
    # counts ανά τύπο (όλα τα ανοιχτά του entity)
    from collections import Counter
    counts = Counter(f.flag_type for f in
                     AttentionFlag.query.filter_by(resolved=False, entity_type=etype).all())
    # εμπλουτισμός με όνομα/σύνδεσμο
    try:
        import payroll as PR
    except Exception:
        PR = None
    items = []
    for f in flags:
        name = '#%s' % f.entity_id; link = None
        if etype == 'employee':
            from app import User
            u = User.query.get(f.entity_id)
            if u:
                name = u.full_name or u.username
                link = '/dashboard/payroll/employee/%d?embed=1' % u.id
        items.append({'f': f, 'name': name, 'link': link,
                      'label': FLAG_LABELS.get(f.flag_type, f.flag_type)})
    log_activity('attention_view', '%s flags' % len(items))
    return render_template('attention.html', items=items, counts=counts,
                           labels=FLAG_LABELS, etype=etype, ftype=ftype,
                           total=len(items), is_admin=is_admin())


@app.route('/dashboard/attention/resolve/<int:fid>', methods=['POST'])
def attention_resolve(fid):
    if not is_admin():
        return redirect(url_for('login'))
    f = AttentionFlag.query.get_or_404(fid)
    f.resolved = True; f.resolved_at = datetime.now()
    cu = current_user(); f.resolved_by = cu.id if cu else None
    db.session.commit()
    return redirect(url_for('attention_center', entity=f.entity_type) + '&embed=1')



class NotDuplicate(db.Model):
    """Ζεύγη προφίλ που ο χρήστης δήλωσε ΟΤΙ ΔΕΝ είναι διπλά (π.χ. αδέρφια ίδιο επώνυμο)."""
    id    = db.Column(db.Integer, primary_key=True)
    a_id  = db.Column(db.Integer, index=True)
    b_id  = db.Column(db.Integer, index=True)
    entity_type = db.Column(db.String(20), default='employee')
    created_at = db.Column(db.DateTime, default=datetime.now)

def _pair(a, b):
    return (min(a, b), max(a, b))

def dismiss_pair(a, b, entity_type='employee'):
    lo, hi = _pair(a, b)
    if not NotDuplicate.query.filter_by(a_id=lo, b_id=hi, entity_type=entity_type).first():
        db.session.add(NotDuplicate(a_id=lo, b_id=hi, entity_type=entity_type))

def is_dismissed(a, b, entity_type='employee'):
    lo, hi = _pair(a, b)
    return NotDuplicate.query.filter_by(a_id=lo, b_id=hi, entity_type=entity_type).first() is not None

print('people core module loaded (ProfileEvent/AttentionFlag/attention)')
