# -*- coding: utf-8 -*-
"""v12.80 — Διαμόρφωση μενού (menu customizer). Self-service ομαδοποίηση/σειρά/απόκρυψη.
Custom render ΜΟΝΟ όταν υπάρχει αποθηκευμένο layout ΚΑΙ ο χρήστης είναι admin (fallback=default).
"""
import json
from flask import request, redirect, url_for, render_template
from app import app, db, current_user, is_admin, log_activity, Setting

# ── Κατάλογος ΟΛΩΝ των στοιχείων (deduped). master=μόνο masteradmin ──
MENU_CATALOG = [
    ('dashboard',   'Dashboard',              'ti-layout-dashboard', '/overview',                    False),
    ('today',       'Σήμερα (Μετρήσεις)',     'ti-calendar-check',   '/dashboard/measurements/today',False),
    ('records',     'Καταγραφές - Μετρήσεις', 'ti-clipboard-data',   '/records',                     False),
    ('meas_console','Μετρήσεις · Ρυθμίσεις',   'ti-adjustments-cog',  '/dashboard/measurements',      False),
    ('meas_entry',  'Μετρήσεις · Καταχώρηση',  'ti-pencil-plus',      '/dashboard/measurements/entry', False),
    ('meas_stats',  'Μετρήσεις · Στατιστικά',  'ti-chart-histogram',  '/dashboard/measurements/stats', False),
    ('faults_board','Πίνακας Βλαβών',         'ti-alert-triangle',   '/dashboard/faults',            False),
    ('fault_submit','Δήλωση βλάβης',          'ti-tool',             '/fault',                       False),
    ('areas_rec',   'Καταγραφή τομέων',       'ti-clipboard-list',   '/areas',                       False),
    ('areas_dash',  'Πίνακας τομέων',         'ti-map-pin',          '/areas/dashboard',             False),
    ('surveys',     'Ερωτηματολόγια',         'ti-clipboard-check',  '/dashboard/surveys',           False),
    ('people',      'Διαχείριση προσωπικού',  'ti-users-group',      '/dashboard/people',            False),
    ('org',         'Οργανόγραμμα',           'ti-sitemap',          '/dashboard/org',               False),
    ('pay_mitroo',  'Μητρώο εργαζομένων',     'ti-cash',             '/dashboard/payroll',           False),
    ('evals',       'Αξιολόγηση προσωπικού',  'ti-star',             '/dashboard/evaluations',       False),
    ('pay_grid',    'Μαζική επεξεργασία',     'ti-table',            '/dashboard/payroll/grid',      False),
    ('sched',       'Πρόγραμμα Εργασίας',     'ti-calendar-week',    '/dashboard/schedule',          False),
    ('sched_sub',   'Υποβολές (Λογιστήριο)',  'ti-send',             '/dashboard/schedule/submissions',False),
    ('pay_runs',    'Μισθοδοσία · Εκτελέσεις','ti-calculator',       '/dashboard/payroll/runs',      False),
    ('pay_control', 'Έλεγχος & Έγκριση',      'ti-clipboard-check',  '/dashboard/payroll/control',   False),
    ('attention',   'Χρειάζονται προσοχή',    'ti-alert-triangle',   '/dashboard/attention',         False),
    ('dups',        'Πιθανές διπλοεγγραφές',  'ti-users',            '/dashboard/payroll/duplicates',False),
    ('companies',   'Εταιρείες',              'ti-building-bank',    '/dashboard/payroll/companies', False),
    ('rates',       'Συντελεστές',            'ti-percentage',       '/dashboard/payroll/rates',     False),
    ('sched_set',   'Πρόγραμμα · Ρυθμίσεις',  'ti-calendar-cog',     '/dashboard/schedule/settings', False),
    ('sched_staff', 'Πρόγραμμα · Προσωπικό',  'ti-users-plus',       '/dashboard/schedule/staff',    False),
    ('sched_identify','Ταυτοποίηση προσωπικού','ti-user-search',     '/dashboard/schedule/identify', False),
    ('sched_imported','Εισηγμένα προφίλ',       'ti-user-cog',         '/dashboard/schedule/imported', False),
    ('sched_monthly','Μηνιαία συγκεντρωτική',   'ti-calendar-stats',   '/dashboard/schedule/monthly',  False),
    ('sched_oversight','Εποπτεία προγράμματος', 'ti-eye-cog',          '/dashboard/schedule/oversight',False),
    ('imports',     'Κέντρο Εισαγωγής',       'ti-database-import',  '/dashboard/imports',           False),
    ('backup',      'Αντίγραφα ασφαλείας',    'ti-database-export',  '/dashboard/backup',            False),
    ('diag',        'Διαγνωστικά',            'ti-stethoscope',      '/dashboard/diag',              True),
    ('users',       'Χρήστες',                'ti-users',            '/dashboard/users',             False),
    ('menu_roles',  'Μενού ανά ρόλο',         'ti-adjustments-cog',  '/dashboard/menu-roles',        False),
    ('menu_builder','Διαμόρφωση μενού',       'ti-layout-grid',      '/dashboard/menu-builder',      False),
    ('activity',    'Καταγραφή χρηστών',      'ti-history',          '/dashboard/activity',          False),
    ('feedback_adm','Feedback χρηστών',       'ti-messages',         '/dashboard/feedback',          False),
    ('hotels',      'Ξενοδοχεία & Πισίνες',   'ti-building',         '/dashboard/hotels',            False),
    ('areas_admin', 'Διαχείριση τομέων',      'ti-map-pin',          '/dashboard/areas',             False),
    ('templates',   'Templates',              'ti-template',         '/dashboard/templates',         False),
    ('fault_set',   'Βλάβες · Ρυθμίσεις',     'ti-settings-cog',     '/dashboard/faults/settings',   False),
    ('fault_cat',   'Κατηγορίες βλαβών',      'ti-list-tree',        '/dashboard/faults/categories', False),
    ('email',       'Email',                  'ti-mail',             '/dashboard/email',             False),
    ('theme',       'Εμφάνιση',               'ti-palette',          '/dashboard/theme',             False),
    ('ai',          'AI σύνδεση',             'ti-plug',             '/dashboard/ai',                True),
    ('search',      'Αναζήτηση',              'ti-search',           '/dashboard/search',            False),
    ('roadmap',     'Roadmap',                'ti-map-2',            '/dashboard/roadmap',           False),
    ('help',        'Βοήθεια (FAQ)',          'ti-help-circle',      '/dashboard/help',              False),
    ('whatsnew',    'Τι νέο',                 'ti-sparkles',         '/dashboard/whatsnew',          False),
    ('feedback',    'Στείλε feedback',        'ti-message-2-plus',   '/feedback',                    False),
]
CAT = {i[0]: {'id': i[0], 'label': i[1], 'icon': i[2], 'url': i[3], 'master': i[4]} for i in MENU_CATALOG}

DEFAULT_LAYOUT = [
    {'title': 'Επισκόπηση', 'items': ['dashboard']},
    {'title': 'Μετρήσεις & Καταγραφές', 'items': ['today', 'meas_entry', 'areas_rec', 'records', 'meas_stats', 'areas_dash', 'meas_console']},
    {'title': 'Βλάβες', 'items': ['fault_submit', 'faults_board']},
    {'title': 'Πρόγραμμα Εργασίας', 'items': ['sched', 'sched_monthly', 'sched_oversight', 'sched_sub', 'sched_set']},
    {'title': 'Προσωπικό', 'items': ['people', 'org', 'pay_mitroo', 'evals', 'sched_identify', 'sched_imported', 'sched_staff', 'dups']},
    {'title': 'Μισθοδοσία', 'items': ['pay_runs', 'pay_control', 'pay_grid', 'rates', 'companies', 'attention']},
    {'title': 'Υποδοχή', 'items': ['surveys']},
    {'title': 'Δεδομένα & Εισαγωγές', 'items': ['imports', 'backup', 'diag']},
    {'title': 'Ρυθμίσεις συστήματος', 'items': ['users', 'hotels', 'areas_admin', 'templates', 'fault_set', 'fault_cat', 'email', 'theme', 'ai', 'menu_roles', 'menu_builder', 'activity', 'feedback_adm']},
    {'title': 'Ενημέρωση', 'items': ['search', 'roadmap', 'help', 'whatsnew', 'feedback']},
]

def get_layout():
    st = Setting.query.filter_by(key='menu_layout').first()
    if st and st.value:
        try:
            return json.loads(st.value)
        except Exception:
            pass
    return None

def save_layout(groups):
    st = Setting.query.filter_by(key='menu_layout').first()
    if not st:
        st = Setting(key='menu_layout'); db.session.add(st)
    st.value = json.dumps(groups, ensure_ascii=False)
    db.session.commit()

# ── v12.238 — Μενού ανά workspace × ρόλο (master = admin) ─────────────────────
WS_OPTS   = [('operations', 'Operations'), ('staffhub', 'Staff HUB'),
             ('guestapp', 'Guest App'), ('admin', 'Admin')]
ROLE_OPTS = [('manager', 'Manager'), ('staff', 'Staff'), ('viewer', 'Viewer')]

def get_meta():
    """{item_id: {'ws': [...], 'roles': [...]}} — workspace + ρόλοι ανά στοιχείο."""
    st = Setting.query.filter_by(key='menu_meta').first()
    if st and st.value:
        try:
            return json.loads(st.value)
        except Exception:
            pass
    return {}

def save_meta(meta):
    st = Setting.query.filter_by(key='menu_meta').first()
    if not st:
        st = Setting(key='menu_meta'); db.session.add(st)
    st.value = json.dumps(meta, ensure_ascii=False)
    db.session.commit()

def master_ws_on():
    """Αν ON: το master μενού (admin) οδηγεί ΟΛΑ τα workspaces/ρόλους. Default OFF (καμία αλλαγή)."""
    st = Setting.query.filter_by(key='menu_master_ws').first()
    return bool(st and str(st.value) == '1')


@app.context_processor
def _inject_menu_custom():
    layout = get_layout()
    cu = current_user()
    if not layout:
        return {'menu_custom': False, 'menu_groups': []}
    master = bool(cu and cu.role == 'masteradmin')
    admin = is_admin()
    role = cu.role if cu else None
    meta = get_meta()
    mon = master_ws_on()
    # Custom μενού: admin ΠΑΝΤΑ (master)· μη-admin ΜΟΝΟ αν είναι ενεργό το «master για όλα τα workspaces».
    if not admin and not mon:
        return {'menu_custom': False, 'menu_groups': []}

    def _item(iid):
        it = CAT.get(iid)
        if not it:
            return None
        if it['master'] and not master:
            return None
        m = meta.get(iid) or {}
        ws = [w for w in (m.get('ws') or []) if w]
        roles = [r for r in (m.get('roles') or []) if r]
        if admin:
            wsv = ' '.join(sorted(set(ws) | {'operations', 'admin'}))
            out = dict(it); out['ws'] = wsv or 'operations admin'; return out
        if role not in roles:
            return None
        wsv = ' '.join(ws)
        if not wsv:
            return None
        out = dict(it); out['ws'] = wsv; return out

    def _gws(items):
        s = set()
        for it in items:
            for w in (it.get('ws') or '').split():
                s.add(w)
        return ' '.join(sorted(s)) or 'operations admin'

    groups = []
    present = set()
    for g in layout:
        items = []
        for iid in g.get('items', []):
            present.add(iid)
            x = _item(iid)
            if x:
                items.append(x)
        if items:
            groups.append({'title': g.get('title', ''), 'items': items, 'ws': _gws(items)})
    if admin:
        extra = []
        for k in CAT:
            if k in present:
                continue
            x = _item(k)
            if x:
                extra.append(x)
        if extra:
            groups.append({'title': '🆕 Νέα', 'items': extra, 'ws': _gws(extra)})
    return {'menu_custom': True, 'menu_groups': groups}


@app.route('/dashboard/menu-builder', methods=['GET', 'POST'])
def menu_builder():
    if not is_admin():
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            groups = json.loads(request.form.get('layout') or '[]')
            groups = [{'title': str(g.get('title', ''))[:60], 'items': [i for i in g.get('items', []) if i in CAT]} for g in groups if g.get('title')]
            save_layout(groups)
            # v12.238 — meta (workspace + ρόλοι ανά στοιχείο)
            try:
                raw = json.loads(request.form.get('meta') or '{}')
            except Exception:
                raw = {}
            wsk = {w for w, _ in WS_OPTS}; rk = {r for r, _ in ROLE_OPTS}
            clean = {}
            if isinstance(raw, dict):
                for iid, m in raw.items():
                    if iid not in CAT or not isinstance(m, dict):
                        continue
                    clean[iid] = {'ws': [w for w in (m.get('ws') or []) if w in wsk],
                                  'roles': [r for r in (m.get('roles') or []) if r in rk]}
            save_meta(clean)
            # flag: master για όλα τα workspaces
            mw = '1' if request.form.get('master_ws') else '0'
            fst = Setting.query.filter_by(key='menu_master_ws').first()
            if not fst:
                fst = Setting(key='menu_master_ws'); db.session.add(fst)
            fst.value = mw; db.session.commit()
            log_activity('menu_builder_save', '%d ομάδες' % len(groups))
        except Exception as e:
            return render_template('menu_builder.html', layout=get_layout() or DEFAULT_LAYOUT, cat=CAT, err=str(e), is_admin=is_admin(),
                                   meta=get_meta(), ws_opts=WS_OPTS, role_opts=ROLE_OPTS, master_ws=master_ws_on())
        return redirect(url_for('menu_builder') + '?embed=1&saved=1')
    layout = get_layout() or DEFAULT_LAYOUT
    used = {i for g in layout for i in g.get('items', [])}
    unused = [iid for iid, _ in [(i[0], i) for i in MENU_CATALOG] if iid not in used]
    return render_template('menu_builder.html', layout=layout, cat=CAT, unused=unused,
                           saved=request.args.get('saved'), is_admin=is_admin(),
                           meta=get_meta(), ws_opts=WS_OPTS, role_opts=ROLE_OPTS, master_ws=master_ws_on())


@app.route('/dashboard/menu-builder/reset', methods=['POST'])
def menu_builder_reset():
    if not is_admin():
        return redirect(url_for('login'))
    st = Setting.query.filter_by(key='menu_layout').first()
    if st:
        db.session.delete(st); db.session.commit()
    log_activity('menu_builder_reset', '')
    return redirect(url_for('menu_builder') + '?embed=1')


print('menu customizer module loaded (Διαμόρφωση μενού)')
