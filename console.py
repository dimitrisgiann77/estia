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


def _org_conflicts():
    """v12.170 — διαφωνίες οργανογράμματος↔Epsilon (import_hotel_id ≠ home_hotel_id)."""
    out = []
    try:
        hotels = {h.id: h.name for h in Hotel.query.all()}
        piimap = _pii_map()
        q = (User.query.filter(User.import_hotel_id != None,
                               User.import_hotel_id != User.home_hotel_id)
             .order_by(User.full_name).all())
        for u in q:
            pii = piimap.get(u.id)
            out.append({'id': u.id, 'name': u.full_name or u.username,
                        'code': (pii.emp_code if pii else None),
                        'org_hotel': hotels.get(getattr(u, 'home_hotel_id', None), '—'),
                        'eps_hotel': hotels.get(getattr(u, 'import_hotel_id', None), '—')})
    except Exception:
        pass
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
    pending_items = _pending_items()
    dup_rows = _dup_rows()
    conflicts = _org_conflicts()
    return render_template('people_console.html', rows=rows, counts=counts,
                           pend=pend, dups=dups, pending_items=pending_items,
                           dup_rows=dup_rows, conflicts=conflicts, is_admin=is_admin())


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


@app.route('/dashboard/people/conflict/<int:uid>/keep', methods=['POST'])
def people_conflict_keep(uid):
    if not is_admin():
        return ('', 403)
    u = User.query.get(uid)
    if u and hasattr(u, 'import_hotel_id'):
        u.import_hotel_id = None; db.session.commit()
        log_activity('org_conflict_keep', str(uid))
    return jsonify(ok=True)

@app.route('/dashboard/people/conflict/<int:uid>/accept', methods=['POST'])
def people_conflict_accept(uid):
    if not is_admin():
        return ('', 403)
    u = User.query.get(uid)
    if u and getattr(u, 'import_hotel_id', None):
        import people
        people.assign_user_org(u, u.import_hotel_id, getattr(u, 'department_id', None),
                               actor_id=(current_user().id if current_user() else None),
                               reason='Epsilon (αποδοχή διαφωνίας)')
        u.import_hotel_id = None; db.session.commit()
        log_activity('org_conflict_accept', str(uid))
    return jsonify(ok=True)


print('console module loaded (Διαχείριση προσωπικού)')


# ── v12.162 — Οργανόγραμμα (HR console, drag&drop): ανάθεση τμήμα+ξενοδοχείο μαζί ──
def _hotel_codes():
    try:
        from schedule import _hotel_short
        return {h.id: _hotel_short(h.name) for h in Hotel.query.all()}
    except Exception:
        return {}

def _hotel_dept_ids(hid):
    """Σύνολο department_id που έχει το ξενοδοχείο. Κενό → None (=fallback: όλα τα ενεργά)."""
    try:
        from schedule import HotelDepartment
        ids = {hd.department_id for hd in HotelDepartment.query.filter_by(hotel_id=hid).all()}
        return ids or None
    except Exception:
        return None

@app.route('/dashboard/org')
def org_console():
    if not is_admin():
        return redirect(url_for('login'))
    from schedule import Department
    piimap = _pii_map()
    hotels = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()
    sel = request.args.get('hotel_id', type=int) or (hotels[0].id if hotels else None)
    # v12.178 — τρέχουσα θέση ανά εργαζόμενο (από MgmtAssignment)
    posmap = {}
    try:
        from payroll import MgmtAssignment
        for ma in MgmtAssignment.query.filter(MgmtAssignment.valid_to == None).order_by(MgmtAssignment.id).all():
            if ma.position:
                posmap[ma.user_id] = ma.position
    except Exception:
        pass
    active_depts = Department.query.filter_by(active=True).order_by(Department.sort, Department.name).all()
    dmap = {d.id: d for d in Department.query.all()}   # active+inactive (για ασφαλή εμφάνιση)
    hcodes = _hotel_codes()

    def card(u):
        pii = piimap.get(u.id)
        return {'id': u.id, 'name': u.full_name or u.username,
                'code': (pii.emp_code if pii else None),
                'afm': (pii.afm if pii else None),
                'role': u.role,
                'mgr': role_rank(u.role) >= ROLE_RANK['manager'],
                'avatar': getattr(u, 'avatar', None),
                'pos': posmap.get(u.id),
                'hcode': hcodes.get(getattr(u, 'home_hotel_id', None))}

    # v12.173 (#7) — στήλες = ΜΟΝΟ τα επιλεγμένα τμήματα του ξενοδοχείου (ή όλα τα ενεργά αν δεν έχει οριστεί)
    enabled = _hotel_dept_ids(sel)
    base_ids = enabled if enabled is not None else {d.id for d in active_depts}
    allu = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    bydept = {}     # dept_id (ή 0=Χωρίς τμήμα) -> [cards] για το επιλεγμένο ξενοδοχείο
    pool = []       # όσοι ΔΕΝ είναι στο επιλεγμένο ξενοδοχείο
    for u in allu:
        if getattr(u, 'employment_active', None) is False:
            continue
        if getattr(u, 'home_hotel_id', None) == sel:
            did = getattr(u, 'department_id', None)
            # μη-επιλεγμένο/άγνωστο/διαγραμμένο τμήμα → Χωρίς τμήμα (#7 edge)
            key = did if (did and did in dmap and did in base_ids) else 0
            bydept.setdefault(key, []).append(card(u))
        else:
            pool.append(card(u))
    col_ids = base_ids   # ΜΟΝΟ επιλεγμένα — όχι «όσα έχουν άτομα»
    columns = [dmap[i] for i in col_ids if i in dmap]
    columns.sort(key=lambda d: (d.sort or 0, d.name or ''))
    # v12.171 — λωρίδα Διεύθυνσης (όσα τμήματα είναι μαρκαρισμένα is_leadership)
    lead_cols = [d for d in columns if getattr(d, 'is_leadership', False)]
    columns = [d for d in columns if not getattr(d, 'is_leadership', False)]
    # v12.176 — ομαδοποίηση τμημάτων σε master groups
    from schedule import DepartmentGroup
    all_groups = DepartmentGroup.query.filter_by(active=True).order_by(DepartmentGroup.sort, DepartmentGroup.name).all()
    gmap = {g.id: g for g in all_groups}
    bucket = {}
    ungrouped = []
    for dcol in columns:
        gid = getattr(dcol, 'group_id', None)
        if gid and gid in gmap:
            bucket.setdefault(gid, []).append(dcol)
        else:
            ungrouped.append(dcol)
    grouped = [{'group': g, 'cols': bucket[g.id]} for g in all_groups if g.id in bucket]
    from schedule import JobPosition
    all_positions = JobPosition.query.filter_by(active=True).order_by(JobPosition.sort, JobPosition.name).all()
    # για τον επιλογέα «πρόσθεσε τμήμα στο ξενοδοχείο»
    enabled_set = enabled or set()
    available = [d for d in active_depts if d.id not in enabled_set]
    # v12.167 — supervisors ανά τμήμα (owner-screen = οργανόγραμμα)
    from schedule import HotelDepartment
    umap = {u.id: u for u in allu}
    supmap = {}      # dept_id -> {id,name,code}
    cursup = {}      # dept_id -> user_id (για το JS)
    for hd in HotelDepartment.query.filter_by(hotel_id=sel).all():
        if hd.supervisor_user_id:
            su = umap.get(hd.supervisor_user_id) or User.query.get(hd.supervisor_user_id)
            if su:
                sp = piimap.get(su.id)
                supmap[hd.department_id] = {'id': su.id, 'name': su.full_name or su.username,
                                            'code': (sp.emp_code if sp else None),
                                            'avatar': getattr(su, 'avatar', None)}
                cursup[hd.department_id] = su.id
    # υποψήφιοι υπεύθυνοι = προσωπικό του ξενοδοχείου + managers/admin
    cand = {}
    for u in allu:
        if getattr(u, 'home_hotel_id', None) == sel or role_rank(u.role) >= ROLE_RANK['manager']:
            cand[u.id] = {'id': u.id, 'name': u.full_name or u.username}
    sup_candidates = sorted(cand.values(), key=lambda x: (x['name'] or ''))
    return render_template('org.html', hotels=hotels, sel=sel, columns=columns,
                           bydept=bydept, pool=pool, hcodes=hcodes,
                           active_depts=active_depts, enabled_ids=list(enabled_set), available=available,
                           configured=(enabled is not None),
                           lead_cols=lead_cols, grouped=grouped, ungrouped=ungrouped, all_groups=all_groups,
                           all_positions=all_positions,
                           supmap=supmap, cursup=cursup, sup_candidates=sup_candidates)

@app.route('/dashboard/org/dept/create', methods=['POST'])
def org_dept_create():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department, HotelDepartment
    d = request.json or {}
    name = (d.get('name') or '').strip()[:60]
    color = (d.get('color') or '#64748b').strip()[:9]
    hid = d.get('hotel_id'); hid = int(hid) if hid else None
    if not name:
        return jsonify(ok=False, msg='Όνομα;'), 400
    dep = Department.query.filter(db.func.lower(Department.name) == name.lower()).first()
    if not dep:
        mx = db.session.query(db.func.max(Department.sort)).scalar() or 0
        dep = Department(name=name, name_en=name, color=color, active=True, sort=mx + 1)
        db.session.add(dep); db.session.flush()
    # ενεργοποίηση στο τρέχον ξενοδοχείο
    if hid and not HotelDepartment.query.filter_by(hotel_id=hid, department_id=dep.id).first():
        db.session.add(HotelDepartment(hotel_id=hid, department_id=dep.id))
    db.session.commit()
    log_activity('org_dept_create', '%s @hotel %s' % (name, hid))
    return jsonify(ok=True, id=dep.id)

@app.route('/dashboard/org/dept/toggle', methods=['POST'])
def org_dept_toggle():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import HotelDepartment
    d = request.json or {}
    try:
        hid = int(d['hotel_id']); did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    on = bool(d.get('on'))
    row = HotelDepartment.query.filter_by(hotel_id=hid, department_id=did).first()
    if on and not row:
        db.session.add(HotelDepartment(hotel_id=hid, department_id=did))
    elif (not on) and row:
        db.session.delete(row)
    db.session.commit()
    log_activity('org_dept_toggle', 'hotel=%s dept=%s on=%s' % (hid, did, on))
    return jsonify(ok=True)

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
    # v12.169 — ΕΝΑ write-path (helper) με ιστορικό
    import people
    people.assign_user_org(u, hid, did, actor_id=(current_user().id if current_user() else None))
    db.session.commit()
    log_activity('org_assign', '#%d -> hotel=%s dept=%s' % (u.id, hid, did))
    return jsonify(ok=True)


@app.route('/dashboard/org/supervisor', methods=['POST'])
def org_supervisor():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import HotelDepartment
    d = request.json or {}
    try:
        hid = int(d['hotel_id']); did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    uid = d.get('user_id'); uid = int(uid) if uid else None
    row = HotelDepartment.query.filter_by(hotel_id=hid, department_id=did).first()
    if not row:
        row = HotelDepartment(hotel_id=hid, department_id=did)   # ορισμός υπευθύνου ενεργοποιεί και το τμήμα
        db.session.add(row)
    row.supervisor_user_id = uid
    db.session.commit()
    log_activity('org_supervisor', 'hotel=%s dept=%s sup=%s' % (hid, did, uid))
    return jsonify(ok=True)


@app.route('/dashboard/org/dept/leadership', methods=['POST'])
def org_dept_leadership():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department
    d = request.json or {}
    try:
        did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    dep = Department.query.get(did)
    if not dep:
        return jsonify(ok=False, msg='not found'), 404
    dep.is_leadership = bool(d.get('on'))
    db.session.commit()
    log_activity('org_dept_leadership', 'dept=%s on=%s' % (did, dep.is_leadership))
    return jsonify(ok=True)


@app.route('/dashboard/org/dept/edit', methods=['POST'])
def org_dept_edit():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department
    d = request.json or {}
    try:
        did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    dep = Department.query.get(did)
    if not dep:
        return jsonify(ok=False, msg='not found'), 404
    name = (d.get('name') or '').strip()[:60]
    if name:
        ex = Department.query.filter(db.func.lower(Department.name) == name.lower(), Department.id != did).first()
        if ex:
            return jsonify(ok=False, msg='Υπάρχει ήδη τμήμα με αυτό το όνομα.'), 400
        dep.name = name
    color = (d.get('color') or '').strip()[:9]
    if color:
        dep.color = color
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(ok=False, msg='Υπάρχει ήδη τμήμα με αυτό το όνομα.'), 400
    log_activity('org_dept_edit', str(did))
    return jsonify(ok=True)

@app.route('/dashboard/org/dept/delete', methods=['POST'])
def org_dept_delete():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department, HotelDepartment
    d = request.json or {}
    try:
        did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    dep = Department.query.get(did)
    if not dep:
        return jsonify(ok=False, msg='not found'), 404
    # soft-delete: όσοι ανήκουν → Χωρίς τμήμα· αφαίρεση από ξενοδοχεία· κρατά ιστορικό (WeekPlan/shifts)
    moved = 0
    for u in User.query.filter(User.department_id == did).all():
        u.department_id = None; moved += 1
    HotelDepartment.query.filter_by(department_id=did).delete()
    dep.active = False; dep.is_leadership = False
    db.session.commit()
    log_activity('org_dept_delete', '%s moved=%d' % (did, moved))
    return jsonify(ok=True, moved=moved)

@app.route('/dashboard/org/dept/reorder', methods=['POST'])
def org_dept_reorder():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department
    d = request.json or {}
    order = d.get('order') or []
    for i, did in enumerate(order):
        try:
            dep = Department.query.get(int(did))
            if dep:
                dep.sort = i
        except Exception:
            pass
    db.session.commit()
    log_activity('org_dept_reorder', '%d depts' % len(order))
    return jsonify(ok=True)


@app.route('/dashboard/org/group/save', methods=['POST'])
def org_group_save():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import DepartmentGroup
    d = request.json or {}
    gid = d.get('group_id'); gid = int(gid) if gid else None
    name = (d.get('name') or '').strip()[:60]
    color = (d.get('color') or '').strip()[:9]
    if gid:
        g = DepartmentGroup.query.get(gid)
        if not g:
            return jsonify(ok=False, msg='not found'), 404
        if name:
            g.name = name
        if color:
            g.color = color
    else:
        if not name:
            return jsonify(ok=False, msg='Όνομα;'), 400
        g = DepartmentGroup.query.filter(db.func.lower(DepartmentGroup.name) == name.lower(), DepartmentGroup.active == True).first()
        if not g:
            mx = db.session.query(db.func.max(DepartmentGroup.sort)).scalar() or 0
            g = DepartmentGroup(name=name, name_en=name, color=color or '#64748b', active=True, sort=mx + 1)
            db.session.add(g)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(ok=False, msg='Υπάρχει ήδη ομάδα με αυτό το όνομα.'), 400
    log_activity('org_group_save', '%s' % (g.id))
    return jsonify(ok=True, id=g.id, name=g.name, color=g.color)

@app.route('/dashboard/org/group/delete', methods=['POST'])
def org_group_delete():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import DepartmentGroup, Department
    d = request.json or {}
    try:
        gid = int(d['group_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    g = DepartmentGroup.query.get(gid)
    if not g:
        return jsonify(ok=False, msg='not found'), 404
    for dep in Department.query.filter(Department.group_id == gid).all():
        dep.group_id = None
    g.active = False
    db.session.commit()
    log_activity('org_group_delete', str(gid))
    return jsonify(ok=True)

@app.route('/dashboard/org/dept/setgroup', methods=['POST'])
def org_dept_setgroup():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import Department
    d = request.json or {}
    try:
        did = int(d['department_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    dep = Department.query.get(did)
    if not dep:
        return jsonify(ok=False, msg='not found'), 404
    gid = d.get('group_id'); dep.group_id = int(gid) if gid else None
    db.session.commit()
    log_activity('org_dept_setgroup', 'dept=%s group=%s' % (did, dep.group_id))
    return jsonify(ok=True)


@app.route('/dashboard/org/positions/seed', methods=['POST'])
def org_positions_seed():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import JobPosition
    try:
        from payroll import MgmtAssignment
    except Exception:
        return jsonify(ok=False, msg='Δεν υπάρχουν δεδομένα θέσεων.'), 400
    existing = {(jp.name or '').strip().lower() for jp in JobPosition.query.all()}
    seen = set(); created = 0
    mx = db.session.query(db.func.max(JobPosition.sort)).scalar() or 0
    for ma in MgmtAssignment.query.filter(MgmtAssignment.position != None).all():
        nm = (ma.position or '').strip()
        if not nm:
            continue
        key = nm.lower()
        if key in existing or key in seen:
            seen.add(key); continue
        seen.add(key); mx += 1
        db.session.add(JobPosition(name=nm[:80], color='#64748b', active=True, sort=mx)); created += 1
    db.session.commit()
    log_activity('org_positions_seed', 'created=%d' % created)
    return jsonify(ok=True, created=created)

@app.route('/dashboard/org/position/save', methods=['POST'])
def org_position_save():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import JobPosition
    d = request.json or {}
    pid = d.get('position_id'); pid = int(pid) if pid else None
    name = (d.get('name') or '').strip()[:80]
    color = (d.get('color') or '').strip()[:9]
    gid = d.get('group_id')
    if pid:
        p = JobPosition.query.get(pid)
        if not p:
            return jsonify(ok=False, msg='not found'), 404
        if name:
            p.name = name
        if color:
            p.color = color
        if 'group_id' in d:
            p.group_id = int(gid) if gid else None
    else:
        if not name:
            return jsonify(ok=False, msg='Όνομα;'), 400
        p = JobPosition.query.filter(db.func.lower(JobPosition.name) == name.lower(), JobPosition.active == True).first()
        if not p:
            mx = db.session.query(db.func.max(JobPosition.sort)).scalar() or 0
            p = JobPosition(name=name, color=color or '#64748b', group_id=(int(gid) if gid else None), active=True, sort=mx + 1)
            db.session.add(p)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(ok=False, msg='Υπάρχει ήδη θέση με αυτό το όνομα.'), 400
    log_activity('org_position_save', str(p.id))
    return jsonify(ok=True, id=p.id)

@app.route('/dashboard/org/position/delete', methods=['POST'])
def org_position_delete():
    if not is_admin():
        return jsonify(ok=False, msg='forbidden'), 403
    from schedule import JobPosition
    d = request.json or {}
    try:
        pid = int(d['position_id'])
    except Exception:
        return jsonify(ok=False, msg='bad'), 400
    p = JobPosition.query.get(pid)
    if not p:
        return jsonify(ok=False, msg='not found'), 404
    p.active = False
    db.session.commit()
    log_activity('org_position_delete', str(pid))
    return jsonify(ok=True)
