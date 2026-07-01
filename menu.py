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
    ('meas_data',   'Κονσόλα Μετρήσεων',      'ti-table',            '/dashboard/measurements/console', False),
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
    ('sched_status', 'Κατάσταση Προσωπικού (ανά ξεν.)', 'ti-report-money', '/dashboard/schedule/staff_status', False),
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
    ('fault_set',   'Βλάβες · Ρυθμίσεις',     'ti-settings-cog',     '/dashboard/faults/settings',   False),
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

WS_ORDER = ['operations', 'staffhub', 'guestapp', 'admin']
WS_LABEL = {'operations': 'Operations', 'staffhub': 'Staff HUB', 'guestapp': 'Guest App', 'admin': 'Admin'}

# Κάθε ΟΜΑΔΑ ανήκει σε ΕΝΑ workspace (ws). Τα στοιχεία της κληρονομούν το ws της ομάδας.
# Οι ΡΟΛΟΙ ορίζονται ανά στοιχείο (⚙ → menu_meta.roles).
DEFAULT_LAYOUT = [
    {'ws': 'operations', 'title': 'Συντήρηση', 'items': ['today', 'meas_entry', 'areas_rec', 'fault_submit', 'faults_board', 'records', 'meas_stats', 'areas_dash']},
    {'ws': 'operations', 'title': 'Υποδοχή', 'items': ['surveys']},
    {'ws': 'operations', 'title': 'Πρόγραμμα & Αξιολόγηση', 'items': ['sched', 'sched_monthly', 'sched_oversight', 'evals']},
    {'ws': 'operations', 'title': 'Ενημέρωση', 'items': ['search', 'roadmap', 'help', 'feedback']},
    {'ws': 'staffhub', 'title': 'Ο χώρος μου', 'items': ['whatsnew']},
    {'ws': 'admin', 'title': 'Επισκόπηση', 'items': ['dashboard']},
    {'ws': 'admin', 'title': 'Προσωπικό (HR)', 'items': ['people', 'org', 'pay_mitroo', 'sched_status', 'sched_identify', 'sched_imported', 'dups', 'sched_staff']},
    {'ws': 'admin', 'title': 'Μισθοδοσία', 'items': ['pay_runs', 'pay_control', 'pay_grid', 'rates', 'companies', 'attention', 'sched_sub']},
    {'ws': 'admin', 'title': 'Ρυθμίσεις', 'items': ['meas_console', 'sched_set', 'fault_set', 'hotels', 'areas_admin', 'email', 'theme', 'ai', 'menu_roles', 'menu_builder']},
    {'ws': 'admin', 'title': 'Δεδομένα & Σύστημα', 'items': ['imports', 'backup', 'diag', 'users', 'activity', 'feedback_adm']},
]

# v12.239 — Προεπιλεγμένη ανάθεση workspace + ρόλων ανά στοιχείο (πλάνο μενού v3).
# admin = πάντα όλα (master). roles=[] => μόνο admin. Διακόπτης «master για όλα» ελέγχει αν ισχύει για μη-admin.
DEFAULT_META = {
    # 🟦 OPERATIONS — εργαλεία δουλειάς
    'today':          {'ws': ['operations'], 'roles': ['staff', 'manager']},
    'meas_entry':     {'ws': ['operations'], 'roles': ['staff', 'manager']},
    'areas_rec':      {'ws': ['operations'], 'roles': ['staff', 'manager']},
    'fault_submit':   {'ws': ['operations'], 'roles': ['staff', 'manager']},
    'faults_board':   {'ws': ['operations'], 'roles': ['manager']},
    'records':        {'ws': ['operations'], 'roles': ['manager']},
    'meas_stats':     {'ws': ['operations'], 'roles': ['manager']},
    'areas_dash':     {'ws': ['operations'], 'roles': ['manager']},
    'surveys':        {'ws': ['operations'], 'roles': ['manager']},
    'sched':          {'ws': ['operations'], 'roles': ['manager']},
    'sched_monthly':  {'ws': ['operations'], 'roles': ['manager']},
    'sched_oversight':{'ws': ['operations'], 'roles': ['manager']},
    'evals':          {'ws': ['operations'], 'roles': ['manager']},
    # 🟩 STAFF HUB — εργαζόμενος (κυρίως μελλοντικό)
    'whatsnew':       {'ws': ['staffhub', 'operations'], 'roles': ['staff', 'manager']},
    # 🟥 ADMIN — HR back-office (admin only)
    'people':         {'ws': ['admin'], 'roles': []},
    'pay_mitroo':     {'ws': ['admin'], 'roles': []},
    'org':            {'ws': ['admin'], 'roles': []},
    'sched_identify': {'ws': ['admin'], 'roles': []},
    'sched_imported': {'ws': ['admin'], 'roles': []},
    'dups':           {'ws': ['admin'], 'roles': []},
    'sched_staff':    {'ws': ['admin'], 'roles': []},
    'sched_status':   {'ws': ['admin'], 'roles': []},
    # 🟥 ADMIN — Μισθοδοσία (accountant)
    'pay_runs':       {'ws': ['admin'], 'roles': ['accountant']},
    'pay_control':    {'ws': ['admin'], 'roles': ['accountant']},
    'pay_grid':       {'ws': ['admin'], 'roles': ['accountant']},
    'rates':          {'ws': ['admin'], 'roles': ['accountant']},
    'companies':      {'ws': ['admin'], 'roles': ['accountant']},
    'attention':      {'ws': ['admin'], 'roles': ['accountant']},
    'sched_sub':      {'ws': ['admin'], 'roles': ['accountant']},
    # 🟥 ADMIN — ρυθμίσεις/δεδομένα/πλατφόρμα (admin only)
    'meas_console':   {'ws': ['admin'], 'roles': []},
    'sched_set':      {'ws': ['admin'], 'roles': []},
    'fault_set':      {'ws': ['admin'], 'roles': []},
    'hotels':         {'ws': ['admin'], 'roles': []},
    'areas_admin':    {'ws': ['admin'], 'roles': []},
    'email':          {'ws': ['admin'], 'roles': []},
    'theme':          {'ws': ['admin'], 'roles': []},
    'ai':             {'ws': ['admin'], 'roles': []},
    'menu_roles':     {'ws': ['admin'], 'roles': []},
    'menu_builder':   {'ws': ['admin'], 'roles': []},
    'activity':       {'ws': ['admin'], 'roles': []},
    'feedback_adm':   {'ws': ['admin'], 'roles': []},
    'imports':        {'ws': ['admin'], 'roles': []},
    'backup':         {'ws': ['admin'], 'roles': []},
    'diag':           {'ws': ['admin'], 'roles': []},
    'users':          {'ws': ['admin'], 'roles': []},
    'dashboard':      {'ws': ['admin'], 'roles': []},
    # ⬜ ΕΝΗΜΕΡΩΣΗ — παντού
    'search':         {'ws': ['operations', 'admin'], 'roles': ['manager']},
    'roadmap':        {'ws': ['operations', 'admin'], 'roles': ['manager']},
    'help':           {'ws': ['operations', 'staffhub', 'admin'], 'roles': ['staff', 'manager']},
    'feedback':       {'ws': ['operations', 'staffhub', 'admin'], 'roles': ['staff', 'manager']},
}

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
ROLE_OPTS = [('masteradmin', 'Masteradmin / Διοίκηση'), ('manager', 'Manager'), ('staff', 'Staff'), ('accountant', 'Λογιστήριο'), ('viewer', 'Viewer')]

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

def seed_menu_meta(force=False):
    """Seed προεπιλεγμένων workspace+ρόλων (DEFAULT_META). force=True ξαναγράφει (π.χ. στην Επαναφορά).
    Καλείται και στο boot (module-level) -> app context."""
    with app.app_context():
        try:
            st = Setting.query.filter_by(key='menu_meta').first()
            if st and st.value and not force:
                return
            if not st:
                st = Setting(key='menu_meta'); db.session.add(st)
            st.value = json.dumps(DEFAULT_META, ensure_ascii=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f'[menu] seed_menu_meta skipped: {e}')


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
    # Το custom μενού (Διαμόρφωση μενού) ισχύει ΠΑΝΤΑ για όλους: admin βλέπει τα πάντα·
    # οι υπόλοιποι βλέπουν μόνο όσα στοιχεία έχουν τον ρόλο τους στο ⚙.

    def _roles(iid):
        return [r for r in ((meta.get(iid) or {}).get('roles') or []) if r]

    def _label(iid, it):
        return (meta.get(iid) or {}).get('label') or it['label']

    groups = []
    present = set()
    for g in layout:
        gws = (g.get('ws') or 'operations').strip() or 'operations'
        items = []
        for iid in g.get('items', []):
            present.add(iid)
            it = CAT.get(iid)
            if not it:
                continue
            if it['master'] and not master:
                continue
            if admin:
                it2 = dict(it); it2['ws'] = gws; it2['label'] = _label(iid, it); items.append(it2)
            else:
                if role not in _roles(iid):
                    continue
                it2 = dict(it); it2['ws'] = gws; it2['label'] = _label(iid, it); items.append(it2)
        if items:
            groups.append({'title': g.get('title', ''), 'items': items, 'ws': gws})
    if admin:
        extra = []
        for k in CAT:
            if k in present:
                continue
            it = CAT[k]
            if it['master'] and not master:
                continue
            it2 = dict(it); it2['ws'] = 'admin'; extra.append(it2)
        if extra:
            groups.append({'title': '🆕 Νέα', 'items': extra, 'ws': 'admin'})
    return {'menu_custom': True, 'menu_groups': groups}


@app.route('/dashboard/menu-builder', methods=['GET', 'POST'])
def menu_builder():
    if not is_admin():
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            raw_g = json.loads(request.form.get('layout') or '[]')
            wsk0 = {w for w, _ in WS_OPTS}
            groups = []
            for g in (raw_g if isinstance(raw_g, list) else []):
                if not isinstance(g, dict) or not g.get('title'):
                    continue
                gws = g.get('ws') if g.get('ws') in wsk0 else 'operations'
                items = [i for i in (g.get('items') or []) if i in CAT]
                if items:
                    groups.append({'ws': gws, 'title': str(g.get('title', ''))[:60], 'items': items})
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
                    lbl = str(m.get('label') or '').strip()[:40]
                    if lbl:
                        clean[iid]['label'] = lbl
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
                                   meta=get_meta(), ws_opts=WS_OPTS, role_opts=ROLE_OPTS, master_ws=master_ws_on(),
                                   ws_order=WS_ORDER, ws_label=WS_LABEL)
        return redirect(url_for('menu_builder') + '?embed=1&saved=1')
    layout = get_layout() or DEFAULT_LAYOUT
    used = {i for g in layout for i in g.get('items', [])}
    unused = [iid for iid, _ in [(i[0], i) for i in MENU_CATALOG] if iid not in used]
    return render_template('menu_builder.html', layout=layout, cat=CAT, unused=unused,
                           saved=request.args.get('saved'), is_admin=is_admin(),
                           meta=get_meta(), ws_opts=WS_OPTS, role_opts=ROLE_OPTS, master_ws=master_ws_on(),
                           ws_order=WS_ORDER, ws_label=WS_LABEL)


@app.route('/dashboard/menu-builder/reset', methods=['POST'])
def menu_builder_reset():
    if not is_admin():
        return redirect(url_for('login'))
    st = Setting.query.filter_by(key='menu_layout').first()
    if st:
        db.session.delete(st); db.session.commit()
    seed_menu_meta(force=True)   # v12.239 — Επαναφορά: καθαρό layout + προεπιλεγμένα workspace/ρόλοι
    log_activity('menu_builder_reset', '')
    return redirect(url_for('menu_builder') + '?embed=1')


print('menu customizer module loaded (Διαμόρφωση μενού)')
