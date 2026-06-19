# -*- coding: utf-8 -*-
"""v12.125 — Κονσόλα «Διαχείριση προσωπικού»: ενιαία αναζήτηση/φίλτρα/ενέργειες για ΟΛΑ τα προφίλ.
Plug-in: import από το ΤΕΛΟΣ του app.py. Admin-only. Τα 🔒 Λογιστηρίου προστατεύονται (μόνο προβολή).
Phase 1: προσθετικό — οι παλιές οθόνες παραμένουν ενεργές."""
from flask import request, redirect, url_for, render_template, jsonify
from app import app, db, current_user, is_admin, log_activity, User, Hotel, role_rank, ROLE_RANK


def _pii_map():
    try:
        from payroll import EmployeePII
        return {p.user_id: p for p in EmployeePII.query.all()}
    except Exception:
        return {}

def _dept_map():
    try:
        from schedule import Department
        return {d.id: d.name for d in Department.query.all()}
    except Exception:
        return {}

def _shift_counts():
    try:
        from schedule import ShiftAssignment
        from sqlalchemy import func
        return {uid: n for uid, n in db.session.query(
            ShiftAssignment.user_id, func.count(ShiftAssignment.id)).group_by(ShiftAssignment.user_id).all()}
    except Exception:
        return {}

def _origin(u, pii):
    if pii and getattr(pii, 'locked', False):
        return 'locked'
    if (getattr(u, 'login_enabled', None) is True) or role_rank(u.role) >= ROLE_RANK['admin']:
        return 'login'
    return 'staff'

def _people_rows():
    piimap = _pii_map(); depts = _dept_map(); shifts = _shift_counts()
    hotels = {h.id: h.name for h in Hotel.query.all()}
    out = []
    for u in User.query.order_by(User.full_name).all():
        pii = piimap.get(u.id)
        out.append({
            'id': u.id, 'name': u.full_name or u.username, 'username': u.username or '',
            'role': u.role, 'active': bool(u.is_active),
            'login': (getattr(u, 'login_enabled', None) is True),
            'origin': _origin(u, pii),
            'code': (pii.emp_code if pii else None),
            'afm': (pii.afm if pii else None),
            'hotel': hotels.get(getattr(u, 'home_hotel_id', None)),
            'dept': depts.get(getattr(u, 'department_id', None)),
            'shifts': shifts.get(u.id, 0),
        })
    return out


@app.route('/dashboard/people')
def people_console():
    if not is_admin():
        return redirect(url_for('login'))
    rows = _people_rows()
    counts = {
        'all': len(rows),
        'locked': sum(1 for r in rows if r['origin'] == 'locked'),
        'login': sum(1 for r in rows if r['login']),
        'staff': sum(1 for r in rows if r['origin'] == 'staff'),
    }
    try:
        from schedule import PendingShift
        pend = db.session.query(PendingShift.norm_name).distinct().count()
    except Exception:
        pend = 0
    try:
        from payroll import _dup_pairs
        dups = len(_dup_pairs())
    except Exception:
        dups = 0
    return render_template('people_console.html', rows=rows, counts=counts,
                           pend=pend, dups=dups, is_admin=is_admin())


@app.route('/dashboard/people/card/<int:uid>')
def people_card(uid):
    if not is_admin():
        return ('', 403)
    u = User.query.get(uid)
    if not u:
        return '<div style="padding:16px;color:#94a3b8;">Δεν βρέθηκε.</div>'
    piimap = _pii_map(); pii = piimap.get(uid)
    locked = bool(pii and getattr(pii, 'locked', False))
    depts = _dept_map(); shifts = _shift_counts()
    hotels = {h.id: h.name for h in Hotel.query.all()}
    info = {
        'id': u.id, 'name': u.full_name or u.username, 'username': u.username or '',
        'role': u.role, 'active': bool(u.is_active),
        'login': (getattr(u, 'login_enabled', None) is True),
        'locked': locked,
        'code': (pii.emp_code if pii else None),
        'afm': (pii.afm if pii else None),
        'amka': (pii.amka if pii else None),
        'hotel': hotels.get(getattr(u, 'home_hotel_id', None)),
        'dept': depts.get(getattr(u, 'department_id', None)),
        'shifts': shifts.get(u.id, 0),
    }
    return render_template('people_card.html', u=info)


@app.route('/dashboard/people/login/<int:uid>', methods=['POST'])
def people_toggle_login(uid):
    if not is_admin():
        return ('', 403)
    u = User.query.get(uid)
    if not u:
        return jsonify(ok=False, msg='Δεν βρέθηκε.')
    pii = _pii_map().get(uid)
    if pii and getattr(pii, 'locked', False):
        return jsonify(ok=False, msg='Προστατευμένο προφίλ Λογιστηρίου.')
    newval = not (getattr(u, 'login_enabled', None) is True)
    u.login_enabled = newval
    if newval:
        u.approved = True; u.is_active = True
    db.session.commit()
    log_activity('people_login_toggle', '%d=%s' % (uid, newval))
    return jsonify(ok=True, login=newval)


@app.route('/dashboard/people/delete/<int:uid>', methods=['POST'])
def people_delete(uid):
    if not is_admin():
        return ('', 403)
    try:
        from payroll import _hard_delete_user as _hd
        ok, reason = _hd(uid)
        log_activity('people_delete', '%d (%s)' % (uid, 'ok' if ok else reason))
        return jsonify(ok=ok, msg=('' if ok else reason))
    except Exception as e:
        db.session.rollback()
        return jsonify(ok=False, msg=str(e)[:140])


print('console module loaded (Διαχείριση προσωπικού)')
