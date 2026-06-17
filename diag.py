# -*- coding: utf-8 -*-
"""v12.74 — Διαγνωστικά & Logs + read-only SQL console + Έξυπνο Search.
Plug-in: import από το ΤΕΛΟΣ του app.py, ΠΡΙΝ το init_db(). masteradmin-only τα ευαίσθητα.
"""
import traceback
from datetime import datetime
from flask import request, redirect, url_for, render_template
from sqlalchemy import text, inspect as sa_inspect
from app import (app, db, current_user, is_admin, log_activity, User, APP_VERSION, APP_BUILD)


class ErrorLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    path       = db.Column(db.String(300))
    method     = db.Column(db.String(10))
    user_id    = db.Column(db.Integer)
    etype      = db.Column(db.String(80))
    message    = db.Column(db.Text)
    tb         = db.Column(db.Text)


def _master():
    cu = current_user()
    return bool(cu and cu.role == 'masteradmin')


# ── Καταγραφή exceptions χωρίς αλλαγή συμπεριφοράς (HTTP errors περνούν κανονικά) ──
@app.errorhandler(Exception)
def _log_exception(e):
    from werkzeug.exceptions import HTTPException
    try:
        cu = current_user()
        db.session.rollback()
        db.session.add(ErrorLog(path=request.path, method=request.method,
                                user_id=(cu.id if cu else None),
                                etype=type(e).__name__, message=str(e)[:1000],
                                tb=traceback.format_exc()[:8000]))
        db.session.commit()
    except Exception:
        try: db.session.rollback()
        except Exception: pass
    if isinstance(e, HTTPException):
        return e
    return ('Παρουσιάστηκε σφάλμα — καταγράφηκε στα Διαγνωστικά (masteradmin).', 500)


# ── READ-ONLY SQL ────────────────────────────────────────────────────────────
_FORBIDDEN = ('insert','update','delete','drop','alter','create','truncate',
              'grant','revoke','attach','pragma','replace','merge','into','vacuum','commit','--')
def run_select(sql, limit=500):
    s = (sql or '').strip().rstrip(';').strip()
    if not s:
        return None, None, 'Κενό ερώτημα.'
    low = ' ' + s.lower() + ' '
    if not (low.lstrip().startswith('select') or low.lstrip().startswith('with')):
        return None, None, 'Επιτρέπονται μόνο SELECT/WITH (read-only).'
    if ';' in s:
        return None, None, 'Ένα ερώτημα τη φορά (χωρίς ;).'
    for f in _FORBIDDEN:
        if f in low.replace('selected',''):
            return None, None, 'Απαγορευμένη λέξη: %s' % f.strip()
    if ' limit ' not in low:
        s += ' LIMIT %d' % limit
    try:
        res = db.session.execute(text(s))
        cols = list(res.keys()); rows = [list(r) for r in res.fetchall()]
        db.session.rollback()
        return cols, rows, None
    except Exception as e:
        try: db.session.rollback()
        except Exception: pass
        return None, None, 'Σφάλμα SQL: %s' % e


# ── ΕΝΤΟΛΕΣ (read-only) ──────────────────────────────────────────────────────
def _norm(s):
    import unicodedata, re
    return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFD',str(s or '').upper()) if unicodedata.category(c)!='Mn')).strip()

def run_command(cmd):
    parts = (cmd or '').strip().split(None, 1)
    if not parts: return 'Δώσε εντολή. (HELP για λίστα)'
    op = parts[0].upper(); arg = parts[1].strip() if len(parts) > 1 else ''
    insp = sa_inspect(db.engine)
    if op == 'HELP':
        return ('Εντολές: HEALTH · COUNTS · SCHEMA · TABLE <name> · EMP <αφμ/κωδ/όνομα> · '
                'FIND <κείμενο> · FLAGS · ERRORS · SQL <select…>')
    if op == 'HEALTH':
        out = ['Έκδοση: v%s (build %s)' % (APP_VERSION, APP_BUILD),
               'DB dialect: %s' % db.engine.dialect.name,
               'Πίνακες: %d' % len(insp.get_table_names())]
        import os
        for k in ('DATABASE_URL','GRAPH_CLIENT_ID','SP_HOST','ANTHROPIC_API_KEY','OPENAI_API_KEY'):
            out.append('%s: %s' % (k, 'ΟΚ' if os.environ.get(k) else '—'))
        return '\n'.join(out)
    if op == 'COUNTS':
        rows = []
        for t in sorted(insp.get_table_names()):
            try:
                n = db.session.execute(text('SELECT COUNT(*) FROM "%s"' % t)).scalar()
                rows.append('%-28s %s' % (t, n))
            except Exception:
                rows.append('%-28s ?' % t)
        db.session.rollback()
        return '\n'.join(rows)
    if op == 'SCHEMA':
        out = []
        for t in sorted(insp.get_table_names()):
            cols = ', '.join(c['name'] for c in insp.get_columns(t))
            out.append('%s: %s' % (t, cols))
        return '\n'.join(out)
    if op == 'TABLE':
        if not arg: return 'TABLE <όνομα πίνακα>'
        if arg not in insp.get_table_names(): return 'Άγνωστος πίνακας. (SCHEMA για λίστα)'
        cols, rows, err = run_select('SELECT * FROM "%s"' % arg, limit=50)
        if err: return err
        return _fmt_table(cols, rows)
    if op == 'ERRORS':
        els = ErrorLog.query.order_by(ErrorLog.id.desc()).limit(20).all()
        if not els: return 'Κανένα σφάλμα καταγεγραμμένο. ✓'
        return '\n'.join('[%s] %s %s — %s: %s' % (
            e.created_at.strftime('%d/%m %H:%M') if e.created_at else '', e.method, e.path,
            e.etype, (e.message or '')[:160]) for e in els)
    if op == 'EMP':
        return _emp_dump(arg)
    if op == 'FLAGS':
        try:
            import people as PPL
            from collections import Counter
            c = Counter(f.flag_type for f in PPL.AttentionFlag.query.filter_by(resolved=False).all())
            return '\n'.join('%-22s %d' % (PPL.FLAG_LABELS.get(k,k), v) for k,v in c.most_common()) or 'Καμία.'
        except Exception as e:
            return 'σφάλμα: %s' % e
    if op == 'FIND':
        res = do_search(arg)
        out = []
        for cat, items in res.items():
            if items: out.append('%s (%d): %s' % (cat, len(items), ' · '.join(i['label'] for i in items[:8])))
        return '\n'.join(out) or 'Κανένα αποτέλεσμα.'
    if op == 'SQL':
        cols, rows, err = run_select(arg)
        return err if err else _fmt_table(cols, rows)
    return 'Άγνωστη εντολή «%s». (HELP)' % op

def _fmt_table(cols, rows):
    if not rows: return '(0 γραμμές)\n' + ' | '.join(cols)
    out = [' | '.join(str(c) for c in cols)]
    for r in rows[:200]:
        out.append(' | '.join(('' if v is None else str(v))[:40] for v in r))
    out.append('(%d γραμμές)' % len(rows))
    return '\n'.join(out)

def _emp_dump(q):
    try:
        import payroll as PR
    except Exception:
        PR = None
    u = None
    qn = q.strip()
    if PR:
        pii = PR.EmployeePII.query.filter((PR.EmployeePII.afm == qn) | (PR.EmployeePII.emp_code == qn.upper())).first()
        if pii: u = User.query.get(pii.user_id)
    if u is None:
        cands = [x for x in User.query.all() if _norm(q) in _norm(x.full_name)]
        if len(cands) == 1: u = cands[0]
        elif len(cands) > 1:
            return 'Πολλοί: ' + ' · '.join('%s (#%d)' % (c.full_name, c.id) for c in cands[:15])
    if u is None: return 'Δεν βρέθηκε εργαζόμενος για «%s».' % q
    out = ['#%d  %s  (login=%s, active=%s, role=%s)' % (u.id, u.full_name, u.login_enabled, u.employment_active, u.role)]
    if PR:
        pii = PR.EmployeePII.query.filter_by(user_id=u.id).first()
        if pii:
            out.append('PII: ΑΦΜ=%s Κωδ=%s ΑΜΚΑ=%s ΙΚΑ=%s τράπεζα=%s κ.κόστους=%s' % (
                pii.afm, pii.emp_code, pii.amka, pii.ika_am, pii.bank_name, pii.cost_center))
        for a in PR.MgmtAssignment.query.filter_by(user_id=u.id).all():
            out.append('Ανάθεση: %s/%s %s | %s→%s | συμφ=%s' % (
                a.unit, a.department, a.position or '', a.valid_from or '—', a.valid_to or 'τρέχ', a.agreement_amount))
        nm = {}
        for li in PR.LegalNetImport.query.filter_by(user_id=u.id).all():
            nm[li.year] = nm.get(li.year, 0) + (li.net_legal or 0)
        if nm: out.append('Καθαρά Λογ.: ' + ', '.join('%s=%.0f' % (y, v) for y, v in sorted(nm.items())))
    try:
        import people as PPL
        fl = PPL.open_flags_for(u.id)
        if fl: out.append('Flags: ' + ', '.join(PPL.FLAG_LABELS.get(f.flag_type, f.flag_type) for f in fl))
        ev = PPL.events_for(u.id)[:6]
        if ev: out.append('Ιστορικό: ' + ' | '.join('%s:%s' % (e.event, (e.detail or '')[:40]) for e in ev))
    except Exception:
        pass
    return '\n'.join(out)


# ── ΕΞΥΠΝΟ SEARCH ────────────────────────────────────────────────────────────
PAGES = [
    ('Μητρώο εργαζομένων','/dashboard/payroll'), ('Εκτελέσεις μισθοδοσίας','/dashboard/payroll/runs'),
    ('Έλεγχος & Έγκριση','/dashboard/payroll/control'), ('Εταιρείες','/dashboard/payroll/companies'),
    ('Συντελεστές','/dashboard/payroll/rates'), ('Χρειάζονται προσοχή','/dashboard/attention'),
    ('Πρόγραμμα Εργασίας','/dashboard/schedule'), ('Υποβολές Λογιστηρίου','/dashboard/schedule/submissions'),
    ('Κέντρο Εισαγωγής','/dashboard/imports'), ('Διαγνωστικά','/dashboard/diag'),
    ('Βλάβες','/dashboard/faults'), ('Ερωτηματολόγια','/dashboard/surveys'),
    ('Ξενοδοχεία & Πισίνες','/dashboard/hotels'), ('Χρήστες','/dashboard/users'),
    ('Αντίγραφα ασφαλείας','/dashboard/backup'), ('Roadmap','/dashboard/roadmap'),
    ('Τι νέο','/dashboard/whatsnew'),
]
def do_search(q):
    res = {'Εργαζόμενοι': [], 'Βλάβες': [], 'Ερωτηματολόγια': [], 'Ξενοδοχεία/Τομείς': [], 'Σελίδες': []}
    if not q or len(q.strip()) < 2: return res
    qn = _norm(q); ql = q.strip().lower()
    # employees
    try:
        import payroll as PR
        seen=set()
        for pii in PR.EmployeePII.query.all():
            u = User.query.get(pii.user_id)
            if not u or u.id in seen: continue
            hay = '%s %s %s %s' % (_norm(u.full_name), pii.afm or '', pii.emp_code or '', pii.amka or '')
            if qn in hay or ql in hay.lower():
                seen.add(u.id)
                res['Εργαζόμενοι'].append({'label': '%s%s' % (u.full_name or u.username, (' · '+pii.afm) if pii.afm else ''),
                                          'url': '/dashboard/payroll/employee/%d?embed=1' % u.id})
            if len(res['Εργαζόμενοι']) >= 40: break
    except Exception:
        pass
    # faults
    try:
        import faults as F
        for ft in F.Fault.query.all():
            t = '%s %s %s' % (getattr(ft,'title','') or '', getattr(ft,'code','') or '', getattr(ft,'description','') or '')
            if ql in t.lower():
                res['Βλάβες'].append({'label': (getattr(ft,'code','') or '') + ' ' + (getattr(ft,'title','') or '')[:60],
                                      'url': '/dashboard/faults?embed=1'})
            if len(res['Βλάβες']) >= 20: break
    except Exception:
        pass
    # surveys
    try:
        import surveys as S
        for sv in S.Survey.query.all():
            if ql in (getattr(sv,'title','') or '').lower():
                res['Ερωτηματολόγια'].append({'label': sv.title, 'url': '/dashboard/surveys?embed=1'})
    except Exception:
        pass
    # hotels/areas
    try:
        from app import Hotel
        for h in Hotel.query.all():
            if ql in (h.name or '').lower():
                res['Ξενοδοχεία/Τομείς'].append({'label': h.name, 'url': '/dashboard/hotels?embed=1'})
    except Exception:
        pass
    # pages
    for name, url in PAGES:
        if ql in name.lower() or qn in _norm(name):
            res['Σελίδες'].append({'label': name, 'url': url + '?embed=1'})
    return res


# ── ROUTES ───────────────────────────────────────────────────────────────────
@app.route('/dashboard/diag', methods=['GET', 'POST'])
def diag_center():
    if not _master():
        return redirect(url_for('login'))
    output = None; mode = None; sql_cols = sql_rows = None; sql_err = None
    if request.method == 'POST':
        if request.form.get('cmd') is not None:
            mode = 'cmd'; output = run_command(request.form.get('cmd'))
        elif request.form.get('sql') is not None:
            mode = 'sql'; sql_cols, sql_rows, sql_err = run_select(request.form.get('sql'))
        log_activity('diag_run', mode or '')
    errors = ErrorLog.query.order_by(ErrorLog.id.desc()).limit(15).all()
    insp = sa_inspect(db.engine)
    info = {'version': APP_VERSION, 'build': APP_BUILD, 'dialect': db.engine.dialect.name,
            'tables': len(insp.get_table_names())}
    return render_template('diag.html', output=output, mode=mode, errors=errors, info=info,
                           sql_cols=sql_cols, sql_rows=sql_rows, sql_err=sql_err,
                           cmd_val=request.form.get('cmd',''), sql_val=request.form.get('sql',''),
                           is_admin=is_admin())


@app.route('/dashboard/search')
def search_center():
    if not is_admin():
        return redirect(url_for('login'))
    q = request.args.get('q', '').strip()
    res = do_search(q) if q else None
    total = sum(len(v) for v in res.values()) if res else 0
    log_activity('search', q)
    return render_template('search.html', q=q, res=res, total=total, is_admin=is_admin())


print('diag module loaded (Διαγνωστικά + SQL console + Search)')
