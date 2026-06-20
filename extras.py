# -*- coding: utf-8 -*-
"""
Εστία — extras.py (v12.43): per-role μενού + Feedback χρηστών.
Plug-in: import από το ΤΕΛΟΣ του app.py (πριν το init_db ώστε το create_all να πιάσει το Feedback).
"""
import json
from datetime import datetime
from flask import request, redirect, url_for, render_template, session, jsonify
from app import (app, db, current_user, is_admin, ROLE_RANK, role_rank, log_activity, notify_admins)

# ── MENU ανά ρόλο ─────────────────────────────────────────────────────────────
# Κλειδιά λειτουργικών items (admin workspace μένει πάντα admin-only).
# ── ΚΟΙΝΟ ΜΗΤΡΩΟ ΜΕΝΟΥ (single source of truth) ───────────────────────────────
# Κάθε ρυθμιζόμενο στοιχείο ορίζεται ΜΙΑ φορά εδώ. Από αυτό τραβάνε:
#  (α) το πλαϊνό μενού (shell.html — η ομάδα «Συντήρηση» γίνεται render με loop),
#  (β) ο επεξεργαστής «Μενού ανά ρόλο» (drag & drop).
# Νέο στοιχείο «Συντήρησης» = πρόσθεσέ το εδώ -> εμφανίζεται ΑΥΤΟΜΑΤΑ και στα δύο.
# πεδία: key, label, icon, url, ws (workspaces), group
MENU_REG = [
    {'k': 'today',        'label': 'Σήμερα (Καταγραφές)', 'short': 'Σήμερα', 'icon': 'ti-layout-dashboard', 'url': '/katagrafes',       'ws': 'operations staffhub', 'group': 'Συντήρηση'},
    {'k': 'pools',        'label': 'Πισίνες',             'icon': 'ti-pool',             'url': '/pools',            'ws': 'operations staffhub', 'group': 'Συντήρηση'},
    {'k': 'water',        'label': 'Νερά Χρήσης',         'icon': 'ti-droplet',          'url': '/app',              'ws': 'operations staffhub', 'group': 'Συντήρηση'},
    {'k': 'areas',        'label': 'Καταγραφή τομέων',    'icon': 'ti-checklist',        'url': '/areas',            'ws': 'operations staffhub', 'group': 'Συντήρηση'},
    {'k': 'fault_submit', 'label': 'Δήλωση βλάβης',       'icon': 'ti-tool',             'url': '/fault',            'ws': 'operations staffhub', 'group': 'Συντήρηση'},
    {'k': 'faults_board', 'label': 'Πίνακας Βλαβών',      'icon': 'ti-alert-triangle',   'url': '/dashboard/faults', 'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'pools_dash',   'label': 'Πίνακας Πισινών',     'icon': 'ti-layout-dashboard', 'url': '/pools/dashboard',  'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'water_dash',   'label': 'Πίνακας Νερών',       'icon': 'ti-droplet-filled',   'url': '/dashboard',        'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'areas_dash',   'label': 'Πίνακας τομέων',      'icon': 'ti-clipboard-list',   'url': '/areas/dashboard',  'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'records',      'label': 'Records',             'icon': 'ti-list-details',     'url': '/records',          'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'coverage',     'label': 'Εβδομαδιαία κάλυψη',  'icon': 'ti-calendar-stats',   'url': '/pools/coverage',   'ws': 'operations',          'group': 'Συντήρηση'},
    {'k': 'surveys',      'label': 'Ερωτηματολόγια',      'icon': 'ti-clipboard-check',  'url': '/dashboard/surveys','ws': 'operations admin',    'group': 'Υποδοχή'},
    {'k': 'schedule',     'label': 'Πρόγραμμα Εργασίας',  'icon': 'ti-calendar-week',    'url': '/dashboard/schedule','ws': 'operations admin',   'group': 'HR — Ανθρώπινο Δυναμικό'},
    {'k': 'evals',        'label': 'Αξιολόγηση προσωπικού','icon': 'ti-star',            'url': '/dashboard/evaluations','ws': 'operations admin','group': 'HR — Ανθρώπινο Δυναμικό'},
    {'k': 'org',          'label': 'Οργανόγραμμα',       'icon': 'ti-sitemap',         'url': '/dashboard/org',        'ws': 'operations admin','group': 'HR — Ανθρώπινο Δυναμικό'},
    {'k': 'whatsnew',     'label': 'Τι νέο',              'icon': 'ti-sparkles',         'url': '/dashboard/whatsnew','ws': 'operations admin',   'group': 'Ενημέρωση'},
    {'k': 'info',         'label': 'Ενημέρωση (Αναζήτηση/Roadmap/FAQ)', 'icon': 'ti-info-circle', 'url': '/dashboard/search', 'ws': 'operations admin', 'group': 'Ενημέρωση'},
]
MENU_GROUPS_ORDER = ['Συντήρηση', 'Υποδοχή', 'HR — Ανθρώπινο Δυναμικό', 'Ενημέρωση']
MENU_ITEMS = [(it['k'], it['label']) for it in MENU_REG]
_REG_BY_KEY = {it['k']: it for it in MENU_REG}
ROLES_CFG = ['manager', 'staff']   # admin/masteradmin = πάντα όλα· viewer = ελάχιστα
# Προεπιλογές ορατότητας ανά ρόλο (manager = υποδοχή: πρόγραμμα/βλάβες/records/τι νέο)
DEFAULT_VIS = {
    'manager': {'today', 'records', 'faults_board', 'fault_submit', 'schedule', 'whatsnew', 'pools_dash', 'info', 'evals'},
    # v12.83 — ο συντηρητής (staff) βλέπει ΜΟΝΟ την καταγραφή: Σήμερα + φόρμες + δήλωση βλάβης/τομείς.
    'staff':   {'today', 'pools', 'water', 'fault_submit', 'areas', 'whatsnew'},
}

# ── v12.85 — Ορατότητα «πάνω κουμπιών» (workspaces) ανά ρόλο ──────────────────
WS_ITEMS = [('operations', 'Operations'), ('staffhub', 'Staff HUB'),
            ('guestapp', 'Guest App'), ('admin', 'Admin')]
DEFAULT_WS = {
    'manager': {'operations', 'staffhub', 'guestapp'},
    'staff':   {'operations', 'staffhub'},
}

def get_ws_vis():
    from app import Setting
    row = Setting.query.get('workspace_vis')
    if row and row.value:
        try:
            return json.loads(row.value)
        except Exception:
            pass
    return {r: sorted(DEFAULT_WS.get(r, set())) for r in ROLES_CFG}

def _ws_for_role(role):
    cfg = get_ws_vis()
    return set(cfg.get(role, DEFAULT_WS.get(role, set())))

@app.context_processor
def _inject_ws_show():
    u = current_user()
    role = u.role if u else None
    rank = role_rank(role) if role else -1
    if rank >= ROLE_RANK['admin']:
        allowed = {k for k, _ in WS_ITEMS}            # admin/master: όλα
    elif role in ROLES_CFG:
        allowed = _ws_for_role(role)
    elif rank >= ROLE_RANK['staff']:
        allowed = _ws_for_role('staff')
    else:
        allowed = {'operations'}                       # viewer
    return {'ws_show': (lambda key: key in allowed)}


def get_menu_vis():
    from app import Setting
    row = Setting.query.get('menu_vis')
    if row and row.value:
        try:
            return json.loads(row.value)
        except Exception:
            pass
    return {r: sorted(DEFAULT_VIS.get(r, set())) for r in ROLES_CFG}

def _vis_for_role(role):
    cfg = get_menu_vis()
    return set(cfg.get(role, DEFAULT_VIS.get(role, set())))

def menu_allows(key, user=None):
    """Ιδιο φιλτρο με το menu_show() αλλα καλειται απο routes (π.χ. guard σελιδας).
    True αν ο χρηστης επιτρεπεται να δει το στοιχειο `key` του μενου."""
    u = user or current_user()
    role = u.role if u else None
    rank = role_rank(role) if role else -1
    if rank >= ROLE_RANK['admin']:
        return True
    if role in ROLES_CFG:
        return key in _vis_for_role(role)
    if rank >= ROLE_RANK['staff']:
        return key in _vis_for_role('staff')
    return key == 'whatsnew'

@app.context_processor
def _inject_menu_show():
    u = current_user()
    role = u.role if u else None
    rank = role_rank(role) if role else -1
    if rank >= ROLE_RANK['admin']:
        allowed = {k for k, _ in MENU_ITEMS}          # admin: όλα
    elif role in ROLES_CFG:
        allowed = _vis_for_role(role)
    elif rank >= ROLE_RANK['staff']:
        allowed = _vis_for_role('staff')
    else:
        allowed = {'whatsnew'}                          # viewer
    maint_visible = [it for it in MENU_REG
                     if it['group'] == 'Συντήρηση' and it['k'] in allowed]
    return {'menu_show': (lambda key: key in allowed),
            'maint_visible': maint_visible,
            'menu_reg': MENU_REG}

@app.route('/dashboard/menu-roles', methods=['GET', 'POST'])
def menu_roles():
    if not is_admin():
        return redirect(url_for('login'))
    from app import Setting
    if request.method == 'POST':
        cfg = {}
        for r in ROLES_CFG:
            cfg[r] = [k for k, _ in MENU_ITEMS if request.form.get(f'{r}__{k}')]
        row = Setting.query.get('menu_vis')
        if not row:
            row = Setting(key='menu_vis'); db.session.add(row)
        row.value = json.dumps(cfg, ensure_ascii=False)
        # v12.85 — workspace_vis (πάνω κουμπιά) ανά ρόλο
        wcfg = {}
        for r in ROLES_CFG:
            wcfg[r] = [k for k, _ in WS_ITEMS if request.form.get(f'ws__{r}__{k}')]
        wrow = Setting.query.get('workspace_vis')
        if not wrow:
            wrow = Setting(key='workspace_vis'); db.session.add(wrow)
        wrow.value = json.dumps(wcfg, ensure_ascii=False)
        db.session.commit()
        log_activity('menu_roles_save')
        return redirect('/dashboard/menu-roles?embed=1&ok=1')
    return render_template('menu_roles.html', items=MENU_ITEMS, roles=ROLES_CFG,
                           reg=MENU_REG, groups_order=MENU_GROUPS_ORDER,
                           vis={r: _vis_for_role(r) for r in ROLES_CFG},
                           ws_items=WS_ITEMS, ws_vis={r: _ws_for_role(r) for r in ROLES_CFG},
                           role_labels={'manager': 'Manager (υποδοχή)', 'staff': 'Staff'})


# ── FEEDBACK χρηστών ──────────────────────────────────────────────────────────
class Feedback(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    kind       = db.Column(db.String(12), default='idea')   # bug | idea | other
    text       = db.Column(db.Text)
    page       = db.Column(db.String(200))
    status     = db.Column(db.String(10), default='new')    # new | seen | done
    created_at = db.Column(db.DateTime, default=datetime.now)

KIND_LABEL = {'bug': '🐞 Bug', 'idea': '💡 Ιδέα', 'other': '💬 Άλλο'}

@app.route('/feedback', methods=['GET', 'POST'])
def feedback_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    sent = False
    if request.method == 'POST':
        txt = (request.form.get('text') or '').strip()
        if txt:
            fb = Feedback(user_id=session['user_id'], kind=request.form.get('kind', 'idea'),
                          text=txt[:4000], page=(request.form.get('page') or '')[:200])
            db.session.add(fb); db.session.commit()
            try:
                u = current_user()
                notify_admins(f'Νέο feedback ({KIND_LABEL.get(fb.kind, fb.kind)}) από {u.full_name if u else "?"}',
                              '/dashboard/feedback?embed=1')
            except Exception:
                pass
            log_activity('feedback_submit', fb.kind)
            sent = True
    return render_template('feedback_form.html', sent=sent, kinds=KIND_LABEL)

@app.route('/dashboard/feedback', methods=['GET', 'POST'])
def feedback_admin():
    if not is_admin():
        return redirect(url_for('login'))
    from app import User
    if request.method == 'POST':
        fb = Feedback.query.get(request.form.get('id', type=int))
        if fb:
            fb.status = request.form.get('status', fb.status)
            db.session.commit()
        return redirect('/dashboard/feedback?embed=1')
    items = Feedback.query.order_by(Feedback.created_at.desc()).limit(400).all()
    umap = {u.id: u.full_name for u in User.query.all()}
    counts = {'new': Feedback.query.filter_by(status='new').count(),
              'total': Feedback.query.count()}
    return render_template('feedback_admin.html', items=items, umap=umap,
                           kinds=KIND_LABEL, counts=counts)
