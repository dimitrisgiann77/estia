# -*- coding: utf-8 -*-
"""
Εστία — measurements.py — Ενοποίηση μετρήσεων Συντήρησης (Φ1→Φ3b-2).
Plug-in: import από το ΤΕΛΟΣ του app.py (ΠΡΙΝ το init_db: create_all να πιάσει το MonitorPeriod).

Περιεχόμενα:
  Φ1  — MonitorPeriod + seed templates «pool»/«znx» + default περίοδοι (seed_measurement_engine, boot)
  Φ2  — σημεία από Pool/WaterSystem + ΑΝΤΙΓΡΑΦΗ legacy records → Reading (idempotent)
  Φ3a — περίοδοι CRUD
  Φ3b — generic φόρμα καταχώρησης (Reading) + προτεινόμενες ενέργειες
  Φ3b-2 — granular σημεία ανά περιοχή (Option B) + ΕΝΙΑΙΑ κονσόλα ρυθμίσεων (tabs)
Καθαρά προσθετικό· οι legacy φόρμες/κονσόλα παραμένουν.
"""
from datetime import date, timedelta
from flask import request, redirect, url_for, render_template, session, Response
from app import (app, db, current_user, is_admin, can_log, scoped_hotel_ids, log_activity, area_actions,
                 MonitorTemplate, MonitorParam, Hotel, Pool, WaterSystem,
                 PoolRecord, WaterRecord, Area, Reading, FREQ_LABEL)
import json as _json


# ── Μοντέλο: περίοδοι/βάρδιες ανά template (ορίζονται από admin) ──────────────
class MonitorPeriod(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(30), db.ForeignKey('monitor_template.key'), nullable=False)
    key          = db.Column(db.String(20), nullable=False)
    label        = db.Column(db.String(40), nullable=False)
    time         = db.Column(db.String(5))
    sort         = db.Column(db.Integer, default=0)


_CLO2_LOW  = 'ClO2 {n} <1 ppm: αύξησε τη δοσομέτρηση ClO2· έλεγξε δοσομετρική αντλία/απόθεμα.'
_CLO2_HIGH = 'ClO2 {n} >2 ppm: μείωσε τη δοσομέτρηση ClO2.'

# (pkey, label, unit, min_v, max_v, action_low, action_high)
POOL_PARAMS = [
    ('free_chlorine', 'Ελεύθερο χλώριο', 'mg/L', 0.4, 1.5,
     'Χαμηλό χλώριο — κάνε χλωρίωση και επανέλεγξε σε 30΄.',
     'Υψηλό χλώριο — σταμάτα τη δοσομέτρηση/άσε να πέσει· απόφυγε χρήση μέχρι <1.5 mg/L.'),
    ('combined_chlorine', 'Συνδεδεμένο χλώριο', 'mg/L', None, 0.5, None,
     'Υψηλό δεσμευμένο χλώριο — υπερχλωρίωση (shock) + αερισμός· έλεγξε ανανέωση νερού.'),
    ('ph', 'pH', '', 7.2, 7.8,
     'Χαμηλό pH — πρόσθεσε pH plus (ανθρακική σόδα).',
     'Υψηλό pH — πρόσθεσε pH minus (οξύ), σταδιακά.'),
    ('temp', 'Θερμοκρασία', '°C', None, 32.0, None,
     'Υψηλή θερμοκρασία — έλεγξε/μείωσε θέρμανση· παρακολούθησε χλώριο.'),
    ('turbidity', 'Θολότητα', 'NTU', None, 1.0, None,
     'Θολό νερό — backwash φίλτρου, έλεγξε διήθηση/κυκλοφορία, εξέτασε κροκίδωση.'),
    ('cyanuric_acid', 'Κυανουρικό οξύ', 'mg/L', None, 75.0, None,
     'Υψηλό κυανουρικό οξύ — μερική ανανέωση νερού (αραίωση)· μείωσε σταθεροποιητή.'),
    ('total_alkalinity', 'Ολική αλκαλικότητα', 'mg/L', 80.0, 120.0,
     'Χαμηλή αλκαλικότητα — πρόσθεσε alkalinity up (ανθρακική σόδα).',
     'Υψηλή αλκαλικότητα — πρόσθεσε οξύ σταδιακά.'),
    ('orp', 'ORP', 'mV', 650.0, None,
     'Χαμηλό ORP — ανέβασε ελεύθερο χλώριο και ρύθμισε pH στο 7.2–7.6.', None),
    ('backwash_done', 'Backwash έγινε', '', None, None, None, None),
]

ZNX_PARAMS = [
    ('clo2_tank', 'ClO2 Δεξαμενή', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Δεξαμενή'), _CLO2_HIGH.format(n='Δεξαμενή')),
    ('clo2_kitchen', 'ClO2 Κουζίνα', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Κουζίνα'), _CLO2_HIGH.format(n='Κουζίνα')),
    ('clo2_remote', 'ClO2 Απομακρυσμένο', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Απομακρυσμένο'), _CLO2_HIGH.format(n='Απομακρυσμένο')),
    ('clo2_dhw_out', 'ClO2 Αναχώρηση ΖΝΧ', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Αναχώρηση ΖΝΧ'), _CLO2_HIGH.format(n='Αναχώρηση ΖΝΧ')),
    ('clo2_dhw_return', 'ClO2 Επιστροφή ΖΝΧ', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Επιστροφή ΖΝΧ'), _CLO2_HIGH.format(n='Επιστροφή ΖΝΧ')),
    ('clo2_ro', 'ClO2 Αντ. Όσμωση', 'ppm', 1.0, 2.0, _CLO2_LOW.format(n='Αντ. Όσμωση'), _CLO2_HIGH.format(n='Αντ. Όσμωση')),
    ('temp_dhw_out', 'Κολεκτέρ ΖΝΧ (Αναχ.)', '°C', 60.0, None,
     'Κολεκτέρ ΖΝΧ <60°C: ανέβασε θερμοκρασία αποθήκευσης ≥60°C (κίνδυνος legionella)· έλεγξε λέβητα/εναλλάκτη/θερμοστάτη.', None),
    ('temp_dhw_return', 'Επιστροφή ανακυκλ.', '°C', 50.0, None,
     'Επιστροφή ανακυκλοφορίας <50°C: ανεπαρκής ανακυκλοφορία· έλεγξε αντλία & βάνες· εξέτασε θερμική απολύμανση/flushing.', None),
    ('temp_kitchen_hot', 'Κουζίνα Ζεστό', '°C', 50.0, None,
     'Ζεστό Κουζίνας <50°C: flushing του σημείου· έλεγξε ανακυκλοφορία/μόνωση γραμμής.', None),
    ('temp_remote_hot', 'Απομακρυσμένο Ζεστό', '°C', 50.0, None,
     'Ζεστό Απομακρυσμένου <50°C: flushing· έλεγξε ανακυκλοφορία (κρίσιμο τελευταίο σημείο δικτύου).', None),
    ('temp_tank', 'Δεξαμενή (κρύο)', '°C', None, 20.0, None,
     'Δεξαμενή (κρύο) >20°C: εξέτασε ψύξη/μόνωση/ανανέωση νερού· κίνδυνος ανάπτυξης μικροβίων.'),
    ('temp_kitchen_cold', 'Κουζίνα Κρύο', '°C', None, None, None, None),
    ('temp_remote_cold', 'Απομακρυσμένο Κρύο', '°C', None, None, None, None),
    ('temp_ro', 'Αντ. Όσμωση (θερμ.)', '°C', None, None, None, None),
    ('ph_tank', 'pH Δεξαμενής', '', None, None, None, None),
]

# Granular templates ΖΝΧ ανά περιοχή (Option B): (key, label, [pkeys])
ZNX_LOCATIONS = [
    ('znx_tank',    'ΖΝΧ — Δεξαμενή / Μηχανοστάσιο', ['clo2_tank', 'temp_tank', 'ph_tank']),
    ('znx_kitchen', 'ΖΝΧ — Κουζίνα',                 ['clo2_kitchen', 'temp_kitchen_hot', 'temp_kitchen_cold', 'location_kitchen']),
    ('znx_remote',  'ΖΝΧ — Απομακρυσμένο',           ['clo2_remote', 'temp_remote_hot', 'temp_remote_cold', 'location_remote']),
    ('znx_dhw',     'ΖΝΧ — Αναχώρηση / Επιστροφή',   ['clo2_dhw_out', 'clo2_dhw_return', 'temp_dhw_out', 'temp_dhw_return']),
    ('znx_ro',      'ΖΝΧ — Αντίστροφη Όσμωση',       ['clo2_ro', 'temp_ro']),
]
# location_* params (text) δεν είναι στο ZNX_PARAMS με όρια — ορισμός εδώ:
_TEXT_PARAMS = {'location_kitchen': 'Σημείο Κουζίνας', 'location_remote': 'Σημείο Απομακρ.'}

DEFAULT_PERIODS = [('morning', 'Πρωί', '08:00', 1), ('afternoon', 'Απόγευμα', '17:00', 2)]


# ── helpers seed ─────────────────────────────────────────────────────────────
def _seed_template(key, name, icon, params):
    if MonitorTemplate.query.get(key):
        return False
    db.session.add(MonitorTemplate(key=key, name=name, icon=icon, frequency='twice', sort=0, is_active=True))
    db.session.flush()
    for i, (pkey, label, unit, mn, mx, low, high) in enumerate(params, start=1):
        db.session.add(MonitorParam(template_key=key, pkey=pkey, label=label, unit=unit or '',
                                    min_v=mn, max_v=mx, action_low=low, action_high=high, sort=i))
    return True


def _seed_periods(key):
    if MonitorPeriod.query.filter_by(template_key=key).first():
        return
    for pk, label, t, s in DEFAULT_PERIODS:
        db.session.add(MonitorPeriod(template_key=key, key=pk, label=label, time=t, sort=s))


def seed_measurement_engine():
    """boot (module-level) → χρειάζεται app context (όπως schedule/payroll)."""
    with app.app_context():
        try:
            created = False
            created = _seed_template('pool', 'Πισίνα', 'ti-pool', POOL_PARAMS) or created
            created = _seed_template('znx', 'ΖΝΧ / Δίκτυο νερού', 'ti-droplet', ZNX_PARAMS) or created
            db.session.commit()
            for key in ('pool', 'znx'):
                _seed_periods(key)
            db.session.commit()
            if created:
                print('[measurements] Φ1 seed: templates pool/znx + periods OK')
        except Exception as e:
            db.session.rollback()
            print(f'[measurements] seed skipped: {e}')


# ── Φ2: σημεία (coarse) + αντιγραφή legacy ───────────────────────────────────
_POOL_KEYS = ['free_chlorine', 'combined_chlorine', 'ph', 'temp', 'turbidity',
              'cyanuric_acid', 'total_alkalinity', 'orp', 'backwash_done']
_ZNX_KEYS  = ['clo2_tank', 'clo2_kitchen', 'clo2_remote', 'clo2_dhw_out', 'clo2_dhw_return',
              'clo2_ro', 'temp_dhw_out', 'temp_dhw_return', 'temp_kitchen_hot', 'temp_remote_hot',
              'temp_tank', 'temp_kitchen_cold', 'temp_remote_cold', 'temp_ro', 'ph_tank',
              'location_kitchen', 'location_remote']


def _values_from(rec, keys):
    out = {}
    for k in keys:
        v = getattr(rec, k, None)
        if v is not None and v != '':
            out[k] = v
    return out


def ensure_measurement_points():
    """coarse: ΕΝΑ Area ανά Pool (template 'pool') & WaterSystem (template 'znx'). idempotent."""
    made = 0
    for p in Pool.query.all():
        if not Area.query.filter_by(legacy_kind='pool', legacy_id=p.id, template_key='pool').first():
            db.session.add(Area(hotel_id=p.hotel_id, template_key='pool', name=p.name, location=p.location,
                                is_active=True, engine_only=True, legacy_kind='pool', legacy_id=p.id))
            made += 1
    for w in WaterSystem.query.all():
        if not Area.query.filter_by(legacy_kind='water', legacy_id=w.id, template_key='znx').first():
            db.session.add(Area(hotel_id=w.hotel_id, template_key='znx', name=w.name, location=w.location,
                                is_active=True, engine_only=True, legacy_kind='water', legacy_id=w.id))
            made += 1
    db.session.commit()
    return made


def _point_map():
    m = {}
    for a in Area.query.filter(Area.engine_only.is_(True)).all():
        if a.legacy_kind and a.legacy_id and a.template_key in ('pool', 'znx'):
            m[(a.legacy_kind, a.legacy_id)] = a.id
    return m


def migrate_legacy_records():
    ensure_measurement_points()
    pm = _point_map()
    res = {'pool': 0, 'water': 0, 'pool_skip': 0, 'water_skip': 0, 'orphan': 0}
    n = 0
    for r in PoolRecord.query.all():
        if Reading.query.filter_by(source_kind='pool', source_id=r.id).first():
            res['pool_skip'] += 1; continue
        aid = pm.get(('pool', r.pool_id))
        if not aid:
            res['orphan'] += 1; continue
        db.session.add(Reading(area_id=aid, template_key='pool', user_id=r.user_id,
                               record_date=r.record_date, period=r.period, recorded_at=r.recorded_at,
                               updated_at=r.updated_at, updated_by=r.updated_by,
                               values=_json.dumps(_values_from(r, _POOL_KEYS)), notes=r.notes,
                               source_kind='pool', source_id=r.id))
        res['pool'] += 1; n += 1
        if n % 500 == 0:
            db.session.commit()
    for r in WaterRecord.query.all():
        if Reading.query.filter_by(source_kind='water', source_id=r.id).first():
            res['water_skip'] += 1; continue
        aid = pm.get(('water', r.water_system_id))
        if not aid:
            res['orphan'] += 1; continue
        db.session.add(Reading(area_id=aid, template_key='znx', user_id=r.user_id,
                               record_date=r.record_date, period=r.period, recorded_at=r.recorded_at,
                               updated_at=r.updated_at, updated_by=r.updated_by,
                               values=_json.dumps(_values_from(r, _ZNX_KEYS)), notes=r.notes,
                               source_kind='water', source_id=r.id))
        res['water'] += 1; n += 1
        if n % 500 == 0:
            db.session.commit()
    db.session.commit()
    return res


def migration_status():
    return {
        'pool_records': PoolRecord.query.count(), 'water_records': WaterRecord.query.count(),
        'pool_migrated': Reading.query.filter_by(source_kind='pool').count(),
        'water_migrated': Reading.query.filter_by(source_kind='water').count(),
        'pools': Pool.query.count(), 'systems': WaterSystem.query.count(),
    }


# ── Φ3b-2: granular σημεία ανά περιοχή ───────────────────────────────────────
def _znx_param(pkey):
    for tup in ZNX_PARAMS:
        if tup[0] == pkey:
            return tup
    if pkey in _TEXT_PARAMS:
        return (pkey, _TEXT_PARAMS[pkey], '', None, None, None, None)
    return None


def autocreate_granular_points():
    """Σπάει το ΖΝΧ σε σημεία ανά περιοχή (sub-templates + Area/δίκτυο). idempotent.
    Πισίνες: ensure ένα σημείο/πισίνα. Coarse 'znx' σημεία → ανενεργά (μένουν ως ιστορικό)."""
    made_t = made_p = 0
    for key, label, pkeys in ZNX_LOCATIONS:
        if not MonitorTemplate.query.get(key):
            db.session.add(MonitorTemplate(key=key, name=label, icon='ti-droplet', frequency='twice', sort=5, is_active=True))
            db.session.flush()
            for i, pk in enumerate(pkeys, start=1):
                tup = _znx_param(pk)
                if tup:
                    _, lab, unit, mn, mx, low, high = tup
                    db.session.add(MonitorParam(template_key=key, pkey=pk, label=lab, unit=unit or '',
                                                min_v=mn, max_v=mx, action_low=low, action_high=high, sort=i))
            made_t += 1
        _seed_periods(key)
    db.session.commit()
    for w in WaterSystem.query.all():
        for key, label, _pk in ZNX_LOCATIONS:
            if not Area.query.filter_by(legacy_kind='water', legacy_id=w.id, template_key=key).first():
                db.session.add(Area(hotel_id=w.hotel_id, template_key=key, name=label, location=w.name,
                                    is_active=True, engine_only=True, legacy_kind='water', legacy_id=w.id))
                made_p += 1
    made_p += ensure_measurement_points()  # πισίνες (+coarse znx)
    # coarse znx σημεία → ανενεργά (ιστορικό), για να μη μπαίνουν στην καταχώρηση
    for a in Area.query.filter_by(template_key='znx', engine_only=True).all():
        a.is_active = False
    db.session.commit()
    return made_t, made_p


# ── helpers UI ───────────────────────────────────────────────────────────────
def _param_input_kind(pkey):
    if pkey == 'backwash_done':
        return 'bool'
    if pkey.startswith('location'):
        return 'text'
    return 'num'


def _entry_points():
    """Σημεία για καταχώρηση: ενεργά engine σημεία ΕΚΤΟΣ coarse 'znx'."""
    return (Area.query.filter(Area.is_active == True, Area.engine_only.is_(True),
                              Area.template_key != 'znx')
            .order_by(Area.hotel_id, Area.template_key, Area.name).all())


# ── ΕΝΙΑΙΑ ΚΟΝΣΟΛΑ ΡΥΘΜΙΣΕΩΝ ─────────────────────────────────────────────────
@app.route('/dashboard/measurements')
def measurements_console():
    if not is_admin():
        return redirect(url_for('login'))
    tab = request.args.get('tab', 'points')
    hmap = {h.id: h.name for h in Hotel.query.all()}
    # points grouped by hotel
    pts = Area.query.filter(Area.engine_only.is_(True)).order_by(Area.hotel_id, Area.template_key, Area.name).all()
    by_hotel = {}
    for a in pts:
        by_hotel.setdefault(a.hotel_id, []).append(a)
    points_by_hotel = [{'hotel': hmap.get(hid, '—'), 'areas': items} for hid, items in by_hotel.items()]
    # periods
    tpl_periods = []
    for t in MonitorTemplate.query.filter_by(is_active=True).order_by(MonitorTemplate.sort, MonitorTemplate.name).all():
        tpl_periods.append({'tpl': t, 'periods': MonitorPeriod.query.filter_by(template_key=t.key)
                            .order_by(MonitorPeriod.sort, MonitorPeriod.id).all(),
                            'nparams': len(t.params or [])})
    return render_template('measurements_console.html', tab=tab,
                           points_by_hotel=points_by_hotel, tpl_periods=tpl_periods,
                           st=migration_status(), msg=request.args.get('msg'),
                           all_hotels=Hotel.query.order_by(Hotel.name).all(),
                           all_templates=MonitorTemplate.query.filter_by(is_active=True).order_by(MonitorTemplate.name).all(),
                           param_templates=MonitorTemplate.query.order_by(MonitorTemplate.sort).all(),
                           freq_label=FREQ_LABEL)


@app.route('/dashboard/measurements/autocreate', methods=['POST'])
def measurements_autocreate():
    if not is_admin():
        return redirect(url_for('login'))
    t, p = autocreate_granular_points()
    log_activity('meas_autocreate', f'{t} templates, {p} σημεία')
    return redirect(url_for('measurements_console') + '?tab=points&msg=' + ('Δημιουργήθηκαν %d τύποι περιοχής + %d σημεία.' % (t, p)))


@app.route('/dashboard/measurements/point/save', methods=['POST'])
def measurements_point_save():
    if not is_admin():
        return redirect(url_for('login'))
    f = request.form
    pid = f.get('point_id')
    name = (f.get('name') or '').strip()
    loc = (f.get('location') or '').strip()
    if pid:
        a = Area.query.get(int(pid))
        if a and name:
            a.name = name[:120]; a.location = loc[:120]
    else:
        hid = f.get('hotel_id'); tk = f.get('template_key')
        if hid and tk and name:
            db.session.add(Area(hotel_id=int(hid), template_key=tk, name=name[:120], location=loc[:120],
                                is_active=True, engine_only=True))
    db.session.commit()
    return redirect(url_for('measurements_console') + '?tab=points')


@app.route('/dashboard/measurements/point/<int:pid>/toggle', methods=['POST'])
def measurements_point_toggle(pid):
    if not is_admin():
        return redirect(url_for('login'))
    a = Area.query.get(pid)
    if a:
        a.is_active = not bool(a.is_active); db.session.commit()
    return redirect(url_for('measurements_console') + '?tab=points')


@app.route('/dashboard/measurements/migrate', methods=['POST'])
def measurements_migrate_run():
    if not is_admin():
        return redirect(url_for('login'))
    action = request.form.get('action')
    if action == 'points':
        made = ensure_measurement_points()
        msg = 'Δημιουργήθηκαν %d σημεία (coarse).' % made
    else:
        res = migrate_legacy_records()
        msg = ('Μεταφορά — Πισίνες: %d (%d ήδη)· Νερά: %d (%d ήδη)· ορφανά: %d.'
               % (res['pool'], res['pool_skip'], res['water'], res['water_skip'], res['orphan']))
    log_activity('meas_migrate', msg)
    return redirect(url_for('measurements_console') + '?tab=migrate&msg=' + msg)


def _next_period_key(template_key):
    keys = {p.key for p in MonitorPeriod.query.filter_by(template_key=template_key).all()}
    n = 1
    while f'p{n}' in keys:
        n += 1
    return f'p{n}'


@app.route('/dashboard/measurements/period/save', methods=['POST'])
def measurements_period_save():
    if not is_admin():
        return redirect(url_for('login'))
    f = request.form
    tk = (f.get('template_key') or '').strip()
    label = (f.get('label') or '').strip()
    tm = (f.get('time') or '').strip()
    try:
        sort = int(f.get('sort') or 0)
    except (ValueError, TypeError):
        sort = 0
    pid = f.get('period_id')
    if tk and label:
        if pid:
            p = MonitorPeriod.query.get(int(pid))
            if p:
                p.label = label[:40]; p.time = tm[:5]; p.sort = sort
        else:
            db.session.add(MonitorPeriod(template_key=tk, key=_next_period_key(tk), label=label[:40], time=tm[:5], sort=sort))
        db.session.commit()
    return redirect(url_for('measurements_console') + '?tab=periods')


@app.route('/dashboard/measurements/period/<int:period_id>/delete', methods=['POST'])
def measurements_period_delete(period_id):
    if not is_admin():
        return redirect(url_for('login'))
    p = MonitorPeriod.query.get(period_id)
    if p:
        db.session.delete(p); db.session.commit()
    return redirect(url_for('measurements_console') + '?tab=periods')


# ── ΦΟΡΜΑ ΚΑΤΑΧΩΡΗΣΗΣ (operational) ──────────────────────────────────────────
@app.route('/dashboard/measurements/entry')
def measurements_entry():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    user = current_user()
    points = _entry_points()
    if not is_admin():
        _hids = scoped_hotel_ids(user)
        points = [a for a in points if a.hotel_id in _hids]
    hmap = {h.id: h.name for h in Hotel.query.all()}
    hsel = request.args.get('hotel')
    try:
        hsel = int(hsel) if hsel else None
    except (ValueError, TypeError):
        hsel = None
    hotels_with_points = sorted({a.hotel_id for a in points})
    shown = [a for a in points if (hsel is None or a.hotel_id == hsel)]
    grouped = {}
    for a in shown:
        grouped.setdefault(a.hotel_id, []).append(a)
    points_by_hotel = [{'hotel_id': hid, 'hotel': hmap.get(hid, '—'), 'areas': items} for hid, items in grouped.items()]

    sel = tpl = params = periods = None
    recent = []
    actions = []
    pid = request.args.get('point')
    if pid:
        sel = Area.query.get(int(pid))
        if sel:
            tpl = MonitorTemplate.query.get(sel.template_key)
            params = [{'pkey': p.pkey, 'label': p.label, 'unit': p.unit, 'min_v': p.min_v,
                       'max_v': p.max_v, 'low': p.action_low, 'high': p.action_high,
                       'kind': _param_input_kind(p.pkey)} for p in (tpl.params if tpl else [])]
            periods = MonitorPeriod.query.filter_by(template_key=sel.template_key).order_by(MonitorPeriod.sort, MonitorPeriod.id).all()
            recent = Reading.query.filter_by(area_id=sel.id).order_by(Reading.recorded_at.desc()).limit(10).all()
            if recent:
                try:
                    actions = area_actions(recent[0])
                except Exception:
                    actions = []
    return render_template('measurements_entry.html', points_by_hotel=points_by_hotel,
                           hotel_opts=[(hid, hmap.get(hid, '—')) for hid in hotels_with_points],
                           hsel=hsel, sel=sel, tpl=tpl, params=params, periods=periods,
                           recent=recent, actions=actions)


@app.route('/dashboard/measurements/entry/save', methods=['POST'])
def measurements_entry_save():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    f = request.form
    area = Area.query.get(int(f.get('area_id'))) if f.get('area_id') else None
    if not area:
        return redirect(url_for('measurements_entry'))
    if not is_admin() and area.hotel_id not in scoped_hotel_ids(current_user()):
        return redirect(url_for('measurements_entry'))
    tpl = MonitorTemplate.query.get(area.template_key)
    vals = {}
    for p in (tpl.params if tpl else []):
        kind = _param_input_kind(p.pkey)
        raw = f.get(p.pkey)
        if kind == 'bool':
            if f.get(p.pkey):
                vals[p.pkey] = True
        elif kind == 'text':
            if raw:
                vals[p.pkey] = raw.strip()
        else:
            if raw not in (None, ''):
                try:
                    vals[p.pkey] = float(str(raw).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
    period = (f.get('period') or 'day').strip()
    rec = Reading(area_id=area.id, template_key=area.template_key, user_id=current_user().id,
                  record_date=date.today(), period=period, values=_json.dumps(vals),
                  notes=(f.get('notes') or '').strip())
    db.session.add(rec); db.session.commit()
    log_activity('meas_entry_save', f'{area.name}/{period}')
    return redirect(url_for('measurements_entry') + '?point=%d&ok=1' % area.id)


# ── Συγκεντρωτική καταχώρηση ανά ξενοδοχείο (όλα τα σημεία μαζί) ──────────────
@app.route('/dashboard/measurements/entry-all')
def measurements_entry_all():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    user = current_user()
    points = _entry_points()
    if not is_admin():
        _hids = scoped_hotel_ids(user)
        points = [a for a in points if a.hotel_id in _hids]
    hmap = {h.id: h.name for h in Hotel.query.all()}
    hotels_with = sorted({a.hotel_id for a in points})
    hsel = request.args.get('hotel')
    try:
        hsel = int(hsel) if hsel else None
    except (ValueError, TypeError):
        hsel = None
    if hsel is None and len(hotels_with) == 1:
        hsel = hotels_with[0]
    shown = [a for a in points if (hsel is not None and a.hotel_id == hsel)]

    _ZNX = ('znx', 'znx_tank', 'znx_kitchen', 'znx_remote', 'znx_dhw', 'znx_ro')
    tname = {t.key: t.name for t in MonitorTemplate.query.all()}

    def _cat(tk):
        if tk == 'pool':
            return (tname.get('pool') or 'Πισίνες', 'ti-pool', 1)
        if tk in _ZNX:
            return (tname.get('znx') or 'Νερά Χρήσης', 'ti-droplet', 2)
        return (tname.get(tk) or 'Λοιπά', 'ti-checklist', 5)

    pcache = {}

    def _params(tk):
        if tk not in pcache:
            t = MonitorTemplate.query.get(tk)
            pcache[tk] = [{'pkey': p.pkey, 'label': p.label, 'unit': p.unit, 'min_v': p.min_v,
                           'max_v': p.max_v, 'low': p.action_low, 'high': p.action_high,
                           'kind': _param_input_kind(p.pkey)} for p in (t.params if t else [])]
        return pcache[tk]

    groups = {}
    for a in shown:
        cat, icon, order = _cat(a.template_key)
        g = groups.setdefault(cat, {'title': cat, 'icon': icon, 'order': order, 'areas': []})
        g['areas'].append({'area': a, 'params': _params(a.template_key)})
    glist = sorted(groups.values(), key=lambda x: (x['order'], x['title']))

    pk = {}
    for a in shown:
        for pr in MonitorPeriod.query.filter_by(template_key=a.template_key).order_by(MonitorPeriod.sort, MonitorPeriod.id).all():
            pk.setdefault(pr.key, {'key': pr.key, 'label': pr.label, 'time': pr.time, 'sort': pr.sort or 0})
    periods = sorted(pk.values(), key=lambda x: (x['sort'], x['key']))

    return render_template('measurements_entry_all.html', hsel=hsel,
                           hotel_name=hmap.get(hsel, '—'),
                           hotel_opts=[(hid, hmap.get(hid, '—')) for hid in hotels_with],
                           groups=glist, periods=periods, saved=request.args.get('ok'))


@app.route('/dashboard/measurements/entry-all/save', methods=['POST'])
def measurements_entry_all_save():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    f = request.form
    period = (f.get('period') or 'day').strip()
    try:
        hid = int(f.get('hotel_id')) if f.get('hotel_id') else None
    except (ValueError, TypeError):
        hid = None
    points = _entry_points()
    if not is_admin():
        _hids = scoped_hotel_ids(current_user())
        points = [a for a in points if a.hotel_id in _hids]
    saved = 0
    for a in points:
        if hid is not None and a.hotel_id != hid:
            continue
        tpl = MonitorTemplate.query.get(a.template_key)
        vals = {}
        for p in (tpl.params if tpl else []):
            kind = _param_input_kind(p.pkey)
            raw = f.get('v_%d_%s' % (a.id, p.pkey))
            if kind == 'bool':
                if raw:
                    vals[p.pkey] = True
            elif kind == 'text':
                if raw and raw.strip():
                    vals[p.pkey] = raw.strip()
            else:
                if raw not in (None, ''):
                    try:
                        vals[p.pkey] = float(str(raw).replace(',', '.'))
                    except (ValueError, TypeError):
                        pass
        if vals:
            db.session.add(Reading(area_id=a.id, template_key=a.template_key, user_id=current_user().id,
                                   record_date=date.today(), period=period, values=_json.dumps(vals),
                                   notes=(f.get('notes_%d' % a.id) or '').strip()))
            saved += 1
    db.session.commit()
    log_activity('meas_entry_all', '%d σημεία/%s' % (saved, period))
    url = url_for('measurements_entry_all') + '?ok=%d' % saved
    if hid:
        url += '&hotel=%d' % hid
    return redirect(url)


# ── Φ3c-2b: ΕΝΙΑΙΑ «Σήμερα» (engine) — σημεία ανά περιοχή + status ημέρας ─────
@app.route('/dashboard/measurements/today')
def measurements_today():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    user = current_user()
    points = _entry_points()
    if not is_admin():
        _hids = scoped_hotel_ids(user)
        points = [a for a in points if a.hotel_id in _hids]
    today = date.today()
    aids = [a.id for a in points]
    done = {}
    cnt = {}
    if aids:
        for r in Reading.query.filter(Reading.area_id.in_(aids), Reading.record_date == today).all():
            done.setdefault(r.area_id, {})[r.period] = r
            cnt[r.area_id] = cnt.get(r.area_id, 0) + 1
    hmap = {h.id: h.name for h in Hotel.query.all()}
    _pcache = {}

    def _periods(tk):
        if tk not in _pcache:
            _pcache[tk] = MonitorPeriod.query.filter_by(template_key=tk).order_by(
                MonitorPeriod.sort, MonitorPeriod.id).all()
        return _pcache[tk]

    _ZNX = ('znx', 'znx_tank', 'znx_kitchen', 'znx_remote', 'znx_dhw', 'znx_ro')
    tname = {t.key: t.name for t in MonitorTemplate.query.all()}

    def _cat(tk):
        if tk == 'pool':
            return (tname.get('pool') or 'Πισίνες', 'ti-pool', 1)
        if tk in _ZNX:
            return (tname.get('znx') or 'Νερά Χρήσης', 'ti-droplet', 2)
        return (tname.get(tk) or 'Λοιπά', 'ti-checklist', 5)

    by_hotel = {}
    alerts = []
    total = donen = 0
    for a in points:
        prs = _periods(a.template_key)
        slots = []
        for pr in prs:
            r = done.get(a.id, {}).get(pr.key)
            slots.append({'period': pr.key, 'label': pr.label, 'time': pr.time, 'done': bool(r)})
            total += 1
            if r:
                donen += 1
                try:
                    for act in area_actions(r):
                        alerts.append({'point': a.name, 'label': act.get('label'), 'action': act.get('action')})
                except Exception:
                    pass
        cat, icon, order = _cat(a.template_key)
        groups = by_hotel.setdefault(a.hotel_id, {})
        g = groups.setdefault(cat, {'title': cat, 'icon': icon, 'order': order, 'areas': []})
        g['areas'].append({'area': a, 'slots': slots, 'count': cnt.get(a.id, 0)})
    today_by_hotel = []
    for hid, groups in by_hotel.items():
        glist = sorted(groups.values(), key=lambda x: (x['order'], x['title']))
        today_by_hotel.append({'hotel': hmap.get(hid, '—'), 'hotel_id': hid, 'groups': glist})
    return render_template('measurements_today.html', today_by_hotel=today_by_hotel,
                           alerts=alerts, total=total, donen=donen)


# ── Φ4b: ΣΤΑΤΙΣΤΙΚΑ (σημείο × παράμετρος, μέσος/μέγ/ελάχ/εκτός ορίων) ──────────
def _stats_compute(points, dfrom, dto):
    aids = [a.id for a in points]
    amap = {a.id: a for a in points}
    pmeta = {}   # template_key -> {pkey: (label, unit, min, max, sort)}
    agg = {}     # (area_id, pkey) -> stats
    if aids:
        q = Reading.query.filter(Reading.area_id.in_(aids),
                                 Reading.record_date >= dfrom, Reading.record_date <= dto)
        for r in q.all():
            try:
                vals = _json.loads(r.values or '{}')
            except Exception:
                vals = {}
            tk = r.template_key
            if tk not in pmeta:
                t = MonitorTemplate.query.get(tk)
                pmeta[tk] = {p.pkey: (p.label, p.unit, p.min_v, p.max_v, p.sort)
                             for p in (t.params if t else [])}
            for pk, v in vals.items():
                try:
                    fv = float(v)
                except (ValueError, TypeError):
                    continue
                d = agg.setdefault((r.area_id, pk), {'n': 0, 'sum': 0.0, 'min': None, 'max': None, 'out': 0})
                d['n'] += 1; d['sum'] += fv
                d['min'] = fv if d['min'] is None else min(d['min'], fv)
                d['max'] = fv if d['max'] is None else max(d['max'], fv)
                meta = pmeta.get(tk, {}).get(pk)
                if meta:
                    mn, mx = meta[2], meta[3]
                    if (mn is not None and fv < mn) or (mx is not None and fv > mx):
                        d['out'] += 1
    rows = []
    for a in points:
        prm = pmeta.get(a.template_key, {})
        items = []
        for (aid, pk), d in agg.items():
            if aid != a.id:
                continue
            meta = prm.get(pk, (pk, '', None, None, 99))
            avg = d['sum'] / d['n'] if d['n'] else 0
            items.append({'label': meta[0], 'unit': meta[1] or '', 'sort': meta[4],
                          'n': d['n'], 'avg': round(avg, 2),
                          'min': d['min'], 'max': d['max'], 'out': d['out'],
                          'comp': round(100.0 * (d['n'] - d['out']) / d['n']) if d['n'] else 100})
        if items:
            items.sort(key=lambda x: (x['sort'], x['label']))
            rows.append({'point': a, 'params': items})
    return rows


def _stats_range():
    today = date.today()
    rng = request.args.get('range')
    if rng == 'day':
        return today, today
    if rng == 'week':
        return today - timedelta(days=today.weekday()), today
    if rng == 'month':
        return today.replace(day=1), today
    if rng == 'year':
        return today.replace(month=1, day=1), today
    df = request.args.get('from') or today.replace(day=1).isoformat()
    dt = request.args.get('to') or today.isoformat()
    try:
        dfrom = date.fromisoformat(df)
    except Exception:
        dfrom = today.replace(day=1)
    try:
        dto = date.fromisoformat(dt)
    except Exception:
        dto = today
    return dfrom, dto


def _coverage(points, dfrom, dto):
    """Κάλυψη: αναμενόμενες (μέρες × περίοδοι/template) vs πραγματικές (distinct ημέρα/περίοδος)."""
    days = (dto - dfrom).days + 1
    if days < 1:
        days = 1
    out = []
    for a in points:
        nper = MonitorPeriod.query.filter_by(template_key=a.template_key).count() or 1
        expected = days * nper
        actual = (db.session.query(Reading.record_date, Reading.period)
                  .filter(Reading.area_id == a.id, Reading.record_date >= dfrom, Reading.record_date <= dto)
                  .distinct().count())
        missing = max(0, expected - actual)
        cov = round(100.0 * min(actual, expected) / expected) if expected else 100
        out.append({'point': a, 'expected': expected, 'actual': actual, 'missing': missing, 'cov': cov})
    return out


def _stats_xlsx(rows, cov, dfrom, dto, hotel_name):
    """Εκτυπώσιμο Excel: τίτλος + περίοδος/ξενοδοχείο + στατιστικά ανά σημείο + κάλυψη."""
    import io as _io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.properties import PageSetupProperties
    NAVY = '193847'
    wb = Workbook(); ws = wb.active; ws.title = 'Μετρήσεις'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    thin = Side(style='thin', color='DDDDDD')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill('solid', fgColor=NAVY)
    hdr_font = Font(bold=True, color='FFFFFF', size=10)
    r = 1
    ws.cell(r, 1, 'Εστία — CONDIAN HOTELS · Αναφορά Μετρήσεων').font = Font(bold=True, size=15, color=NAVY); r += 1
    ws.cell(r, 1, '%s · Περίοδος: %s έως %s' % (hotel_name, dfrom.strftime('%d/%m/%Y'), dto.strftime('%d/%m/%Y'))).font = Font(size=10, color='777777'); r += 2
    cols = ['Σημείο', 'Παράμετρος', 'Μονάδα', 'Πλήθος', 'Μέσος', 'Ελάχ', 'Μέγ', 'Εκτός ορίων', 'Συμμόρφωση %']
    for c, h in enumerate(cols, 1):
        cell = ws.cell(r, c, h); cell.fill = hdr_fill; cell.font = hdr_font; cell.border = border
    r += 1
    for row in rows:
        for it in row['params']:
            vals = [row['point'].name, it['label'], it['unit'], it['n'], it['avg'], it['min'], it['max'], it['out'], it['comp']]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(r, c, v); cell.border = border
                if c >= 4:
                    cell.alignment = Alignment(horizontal='right')
                if c == 8 and it['out']:
                    cell.font = Font(color='B91C1C', bold=True)
            r += 1
    widths = [26, 22, 9, 9, 9, 9, 9, 12, 13]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, c).column_letter].width = w
    # Κάλυψη
    r += 2
    ws.cell(r, 1, 'Κάλυψη (τι έχει μετρηθεί / τι λείπει)').font = Font(bold=True, size=12, color=NAVY); r += 1
    for c, h in enumerate(['Σημείο', 'Αναμενόμενες', 'Έγιναν', 'Λείπουν', 'Κάλυψη %'], 1):
        cell = ws.cell(r, c, h); cell.fill = hdr_fill; cell.font = hdr_font; cell.border = border
    r += 1
    for cc in cov:
        vals = [cc['point'].name, cc['expected'], cc['actual'], cc['missing'], cc['cov']]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(r, c, v); cell.border = border
            if c >= 2:
                cell.alignment = Alignment(horizontal='right')
            if c == 4 and cc['missing']:
                cell.font = Font(color='B91C1C', bold=True)
        r += 1
    bio = _io.BytesIO(); wb.save(bio); return bio.getvalue()


@app.route('/dashboard/measurements/stats')
def measurements_stats():
    if 'user_id' not in session or not can_log():
        return redirect(url_for('login'))
    user = current_user()
    points = Area.query.filter(Area.engine_only.is_(True)).order_by(
        Area.hotel_id, Area.template_key, Area.name).all()
    if not is_admin():
        _hids = scoped_hotel_ids(user)
        points = [a for a in points if a.hotel_id in _hids]
    hmap = {h.id: h.name for h in Hotel.query.all()}
    hotel_ids = sorted({a.hotel_id for a in points})
    hsel = request.args.get('hotel')
    try:
        hsel = int(hsel) if hsel else None
    except (ValueError, TypeError):
        hsel = None
    if hsel:
        points = [a for a in points if a.hotel_id == hsel]
    dfrom, dto = _stats_range()
    rows = _stats_compute(points, dfrom, dto)
    cov = _coverage(points, dfrom, dto)
    hotel_name = hmap.get(hsel, 'Όλα τα ξενοδοχεία')
    _fmt = request.args.get('fmt')
    if _fmt == 'xlsx':
        data = _stats_xlsx(rows, cov, dfrom, dto, hotel_name)
        return Response(data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': 'attachment; filename=measurements-%s.xlsx' % dto.isoformat()})
    if _fmt == 'csv':
        lines = ['Σημείο,Παράμετρος,Μονάδα,Πλήθος,Μέσος,Ελάχ,Μέγ,Εκτός ορίων,Συμμόρφωση %']
        for r in rows:
            for it in r['params']:
                lines.append('%s,%s,%s,%d,%s,%s,%s,%d,%d' % (
                    (r['point'].name or '').replace(',', ' '), it['label'].replace(',', ' '),
                    it['unit'], it['n'], it['avg'], it['min'], it['max'], it['out'], it['comp']))
        csv = '﻿' + '\n'.join(lines)
        return Response(csv, mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=measurements-stats.csv'})
    # KPIs + δεδομένα γραφημάτων
    total_n = sum(it['n'] for r in rows for it in r['params'])
    total_out = sum(it['out'] for r in rows for it in r['params'])
    overall = round(100.0 * (total_n - total_out) / total_n) if total_n else 100
    pt_labels = []; pt_comp = []
    for r in rows:
        n = sum(it['n'] for it in r['params']); o = sum(it['out'] for it in r['params'])
        pt_labels.append(r['point'].name or '—')
        pt_comp.append(round(100.0 * (n - o) / n) if n else 100)
    param_out = {}
    for r in rows:
        for it in r['params']:
            if it['out']:
                param_out[it['label']] = param_out.get(it['label'], 0) + it['out']
    po = sorted(param_out.items(), key=lambda kv: -kv[1])[:12]
    total_missing = sum(c['missing'] for c in cov)
    kpis = {'total_n': total_n, 'total_out': total_out, 'overall': overall,
            'npoints': len(rows), 'nparams_out': len(param_out), 'missing': total_missing}
    charts = {'pt_labels': pt_labels, 'pt_comp': pt_comp,
              'po_labels': [k for k, _ in po], 'po_vals': [v for _, v in po]}
    return render_template('measurements_stats.html', rows=rows, cov=cov, kpis=kpis, charts=charts,
                           dfrom=dfrom.isoformat(), dto=dto.isoformat(),
                           hotel_opts=[(hid, hmap.get(hid, '—')) for hid in hotel_ids],
                           hsel=hsel, hotel_name=hotel_name, cur_range=request.args.get('range', ''))


print('measurements module loaded (Φ1→Φ4 ενοποίηση μετρήσεων)')
