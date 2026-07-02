# -*- coding: utf-8 -*-
"""v12.377 — Module «Εκ περιτροπής / κοινός εργαζόμενος» (multi-hotel rotation).

Plug-in: import από το ΤΕΛΟΣ του app.py (ΠΡΙΝ το init_db → create_all πιάνει το RotationShare).
ΞΕΧΩΡΙΣΤΟ κύκλωμα από το work_hotel select του Προγράμματος (διαφορετική λειτουργία — P-054).

Φ1 (θεμέλιο — ΜΟΝΟ αποθήκευση/εμφάνιση πληροφορίας):
  • Μοντέλο RotationShare(user↔hotel↔days_week) — ΔΙΑΧΡΟΝΙΚΟ (όχι per-week· days_week=ρυθμός).
  • Ορισμός/ενεργοποίηση ΠΑΝΩ ΣΤΗΝ ΚΑΡΤΕΛΑ εργαζομένου (owner-screen, audit).
  • Συνολική overview (read-only) όλων των εκ-περιτροπής.
  • «Εκ περιτροπής» = ΠΑΡΑΓΩΓΟ (έχει ≥1 γραμμή) → ΚΑΜΙΑ αλλαγή στο μοντέλο User.

ΔΕΝ αγγίζει ακόμη Πρόγραμμα/Μισθοδοσία (Φ2: board visibility + per-day lock + σκληρό όριο·
Φ3: split monthly_settlement ανά work_hotel — με impact-note). Spec: ΠΡΓ-002 / P-054.
"""
from datetime import datetime
from flask import request, redirect, url_for, render_template, jsonify
from app import app, db, current_user, is_admin, log_activity, User, Hotel


# ── Μοντέλο (νέος πίνακας· create_all τον δημιουργεί) ─────────────────────────
class RotationShare(db.Model):
    __tablename__ = 'rotation_share'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    hotel_id   = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    days_week  = db.Column(db.Integer, default=0)   # ρυθμός: μέρες/βδομάδα σε αυτό το ξεν.
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (db.UniqueConstraint('user_id', 'hotel_id', name='uq_rotation_user_hotel'),)


# ── Helpers (read-only· τα διαβάζουν Φ2/Φ3) ──────────────────────────────────
def rotation_shares(uid):
    """[{hotel_id, hotel_name, days_week}] για εργαζόμενο, ταξινομημένα κατά όνομα ξεν."""
    rows = RotationShare.query.filter_by(user_id=uid).all()
    hn = {h.id: h.name for h in Hotel.query.all()}
    out = [{'hotel_id': r.hotel_id, 'hotel_name': hn.get(r.hotel_id, '—'),
            'days_week': r.days_week or 0} for r in rows]
    out.sort(key=lambda x: x['hotel_name'])
    return out

def is_rotational(uid):
    """True αν ο εργαζόμενος είναι εκ περιτροπής (έχει ≥1 μοίρασμα)."""
    return RotationShare.query.filter_by(user_id=uid).first() is not None

def rotational_user_ids():
    """Σύνολο user_id όλων των εκ-περιτροπής (batch — για boards)."""
    return {r.user_id for r in RotationShare.query.all()}

def share_user_ids_for_hotel(hotel_id):
    """user_id όσων μοιράζονται σε ΑΥΤΟ το ξενοδοχείο (batch)."""
    return {r.user_id for r in RotationShare.query.filter_by(hotel_id=hotel_id).all()}

def days_quota(uid, hotel_id):
    """Μέρες/βδομάδα (μερίδιο) του εργαζομένου σε ξενοδοχείο· None αν δεν μοιράζεται εκεί."""
    r = RotationShare.query.filter_by(user_id=uid, hotel_id=hotel_id).first()
    return (r.days_week or 0) if r else None

def _audit(uid, event, detail):
    try:
        import people as _PPL
        cu = current_user()
        _PPL.log_event(uid, event, detail, actor_id=(cu.id if cu else None))
    except Exception:
        pass


# ── ROUTE: ορισμός από την καρτέλα (add / remove) ─────────────────────────────
@app.route('/dashboard/rotation/save', methods=['POST'])
def rotation_save():
    if not is_admin():
        return redirect(url_for('login'))
    try:
        uid = int(request.form.get('user_id'))
    except Exception:
        return redirect(url_for('login'))
    op = (request.form.get('op') or '').strip()
    hid = request.form.get('hotel_id')
    hid = int(hid) if (hid and hid.isdigit()) else None
    u = User.query.get(uid)
    hname = None
    if hid:
        _h = Hotel.query.get(hid); hname = _h.name if _h else str(hid)

    if op == 'remove' and hid:
        RotationShare.query.filter_by(user_id=uid, hotel_id=hid).delete()
        _audit(uid, 'rotation_remove', 'Αφαίρεση εκ περιτροπής: %s' % (hname or hid))
        db.session.commit()
        log_activity('rotation_remove', (u.full_name if u else str(uid)))
    elif op == 'add' and hid:
        try:
            dw = int(request.form.get('days_week') or 0)
        except Exception:
            dw = 0
        dw = max(0, min(7, dw))
        row = RotationShare.query.filter_by(user_id=uid, hotel_id=hid).first()
        if row:
            row.days_week = dw
        else:
            db.session.add(RotationShare(user_id=uid, hotel_id=hid, days_week=dw))
        _audit(uid, 'rotation_add', 'Εκ περιτροπής: %s (%d μέρες/βδ)' % (hname or hid, dw))
        db.session.commit()
        log_activity('rotation_add', (u.full_name if u else str(uid)))
    return redirect(url_for('payroll_employee', uid=uid) + '#rotation')


# ── ROUTE: συνολική εικόνα (read-only) ───────────────────────────────────────
@app.route('/dashboard/rotation')
def rotation_overview():
    if not is_admin():
        return redirect(url_for('login'))
    hn = {h.id: h.name for h in Hotel.query.all()}
    by_user = {}
    for r in RotationShare.query.all():
        by_user.setdefault(r.user_id, []).append(r)
    rows = []
    for uid, shares in by_user.items():
        u = User.query.get(uid)
        if not u:
            continue
        home = hn.get(getattr(u, 'home_hotel_id', None))
        items = sorted(({'hotel': hn.get(s.hotel_id, '—'), 'days': s.days_week or 0}
                        for s in shares), key=lambda x: x['hotel'])
        rows.append({'uid': uid, 'name': u.full_name or u.username, 'home': home,
                     'total_days': sum(i['days'] for i in items), 'shares': items})
    rows.sort(key=lambda r: (r['name'] or ''))
    return render_template('rotation_overview.html', rows=rows)


print('rotation module loaded (εκ περιτροπής — Φ1: μοντέλο + καρτέλα + overview)')
