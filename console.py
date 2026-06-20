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


def _pending_items():
    try:
        from schedule import PendingShift, _suggest_masters, _pending_pii_map, _locked_uids
    except Exception:
        return []
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
    piimap = _pending_pii_map(); locked = _locked_uids()
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
    return items

def _dup_rows():
    try:
        from payroll import _dup_pairs, _net_summary
        out = []
        for a, pa, b, pb, reason in _dup_pairs():
            out.append({'a': a, 'b': b, 'reason': reason,
                        'a_sum': _net_summary(a.id), 'b_sum': _net_summary(b.id)})
        return out
    except Exception:
        return []


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
    pending_items = _pending_items()
    dup_rows = _dup_rows()
    return render_template('people_console.html', rows=rows, counts=counts,
                           pend=pend, dups=dups, pending_items=pending_items,
                           dup_rows=dup_rows, is_admin=is_admin())


def _work_history(uid):
    """v12.127 — ιστορικό απασχόλησης ανά έτος × ξενοδοχείο (από βάρδιες). hotel = work_hotel ή home."""
    try:
        from schedule import ShiftAssignment, is_work_code, assignment_hours, worked_hours, extra_hours
    except Exception:
        return []
    u = User.query.get(uid)
    home = getattr(u, 'home_hotel_id', None) if u else None
    hotels = {h.id: h.name for h in Hotel.query.all()}
    agg = {}
    for a in ShiftAssignment.query.filter_by(user_id=uid).all():
        if not is_work_code(a.shift_code) or not a.work_date:
            continue
        yr = a.work_date.year
        hid = a.work_hotel_id or home
        d = agg.setdefault((yr, hid), {'dates': set(), 'hours': 0.0, 'extra': 0.0, 'frm': None, 'to': None})
        d['dates'].add(a.work_date)
        d['hours'] += worked_hours(a); d['extra'] += extra_hours(assignment_hours(a))
        if not d['frm'] or a.work_date < d['frm']: d['frm'] = a.work_date
        if not d['to'] or a.work_date > d['to']: d['to'] = a.work_date
    rows = []
    for (yr, hid), d in agg.items():
        rows.append({'year': yr, 'hotel': hotels.get(hid, '—'),
                     'days': len(d['dates']), 'hours': round(d['hours'], 1), 'extra': round(d['extra'], 1),
                     'period': (d['frm'].strftime('%d/%m') + '–' + d['to'].strftime('%d/%m')) if d['frm'] else ''})
    rows.sort(key=lambda r: (-r['year'], r['hotel']))
    return rows


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
    return render_template('people_card.html', u=info, history=_work_history(uid))


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


# ── v12.162 — Οργανόγραμμα (HR console, drag&drop): ανάθεση τμήμα+ξενοδοχείο μαζί ──
def _hotel_codes():
    try:
        from schedule import _hotel_short
        return {h.id: _hotel_short(h.name) for h in Hotel.query.all()}
    except Exception:
        return {}

@app.route('/dashboard/org')
def org_console():
    if not is_admin():
        return redirect(url_for('login'))
    from schedule import Department
    piimap = _pii_map()
    hotels = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()
    sel = request.args.get('hotel_id', type=int) or (hotels[0].id if hotels else None)
    depts = Department.query.filter_by(active=True).order_by(Department.sort, Department.name).all()
    hcodes = _hotel_codes()

    def card(u):
        pii = piimap.get(u.id)
        return {'id': u.id, 'name': u.full_name or u.username,
                'code': (pii.emp_code if pii else None),
                'hcode': hcodes.get(getattr(u, 'home_hotel_id', None))}

    allu = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    bydept = {}     # dept_id (or 0) -> [cards] για το επιλεγμένο ξενοδοχείο
    pool = []       # όσοι ΔΕΝ είναι στο επιλεγμένο ξενοδοχείο
    for u in allu:
        if getattr(u, 'employment_active', None) is False:
            continue
        if getattr(u, 'home_hotel_id', None) == sel:
            bydept.setdefault(getattr(u, 'department_id', None) or 0, []).append(card(u))
        else:
            pool.append(card(u))
    return render_template('org.html', hotels=hotels, sel=sel, depts=depts,
                           bydept=bydept, pool=pool, hcodes=hcodes)

@app.route('/dashboard/org/assign', methods=['POST'])
def org_assign():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    d = request.json or {}
    try:
        u = User.query.get(int(d['user_id']))
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    if not u:
        return jsonify(ok=False, msg='not found'), 404
    hid = d.get('hotel_id'); did = d.get('department_id')
    hid = int(hid) if hid else None
    did = int(did) if did else None
    old_h, old_d = getattr(u, 'home_hotel_id', None), getattr(u, 'department_id', None)
    u.home_hotel_id = hid
    u.department_id = did
    # ιστορικό (ProfileEvent)
    try:
        import people
        from schedule import Department
        hn = (Hotel.query.get(hid).name if hid else '—')
        dn = (Department.query.get(did).name if did else '—')
        people.log_event(u.id, 'org_assign', 'Ανάθεση: %s / %s' % (hn, dn))
    except Exception:
        pass
    db.session.commit()
    log_activity('org_assign', '#%d -> hotel=%s dept=%s' % (u.id, hid, did))
    return jsonify(ok=True)
