# -*- coding: utf-8 -*-
"""
Εστία — measurements.py — Φ1 ενοποίησης μετρήσεων Συντήρησης.
Plug-in: import από το ΤΕΛΟΣ του app.py (ΠΡΙΝ το init_db, ώστε το create_all να πιάσει το MonitorPeriod).

Φ1 = ΚΑΘΑΡΑ ΠΡΟΣΘΕΤΙΚΟ:
  - νέο μοντέλο MonitorPeriod (παραμετροποιήσιμες περίοδοι/βάρδιες ανά template)
  - seed templates «pool» (Πισίνα) & «znx» (ΖΝΧ/Δίκτυο νερού) με τις παραμέτρους/όρια/ενέργειες
    που εγκρίθηκαν στη Φ0 (από POOL_LIMITS/ACTION_RULES & WATER_ACTION_RULES)
  - default περίοδοι (Πρωί/Απόγευμα) — αλλάζουν αργότερα από οθόνη ρυθμίσεων (Φ3/Φ4)

ΔΕΝ δημιουργεί σημεία/Area (Φ2), ΔΕΝ αγγίζει παλιές φόρμες/κονσόλα/dashboards. Idempotent.
"""
from app import app, db, MonitorTemplate, MonitorParam


class MonitorPeriod(db.Model):
    """Περίοδος/βάρδια μέτρησης ανά template (ορίζεται από admin)."""
    id           = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(30), db.ForeignKey('monitor_template.key'), nullable=False)
    key          = db.Column(db.String(20), nullable=False)   # 'morning','afternoon','evening','day'...
    label        = db.Column(db.String(40), nullable=False)   # 'Πρωί','Απόγευμα','Βράδυ'...
    time         = db.Column(db.String(5))                    # 'HH:MM' ενδεικτική ώρα
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

DEFAULT_PERIODS = [('morning', 'Πρωί', '08:00', 1), ('afternoon', 'Απόγευμα', '17:00', 2)]


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
    """Idempotent Φ1 seed: templates Πισίνα/ΖΝΧ + default περίοδοι. ΔΕΝ δημιουργεί σημεία (Φ2).
    ΣΗΜ: καλείται στο boot (module-level) -> χρειάζεται app context (όπως schedule/payroll)."""
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


print('measurements module loaded (Φ1 ενοποίηση μετρήσεων Συντήρησης)')


# ════════════════════════════════════════════════════════════════════════════
#  Φ2 — Δημιουργία σημείων από Pool/WaterSystem + ΑΝΤΙΓΡΑΦΗ legacy records → Reading
#  Ασφαλές: COPY (τα παλιά μένουν), idempotent (source_kind/source_id), admin-triggered.
# ════════════════════════════════════════════════════════════════════════════
import json as _json
from flask import request, redirect, url_for, render_template
from app import (app, current_user, is_admin, log_activity,
                 Hotel, Pool, WaterSystem, PoolRecord, WaterRecord, Area, Reading)

# pkeys που αντιγράφονται από κάθε legacy record (ίδια ονόματα στηλών)
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
    """Δημιουργεί ΕΝΑ engine_only Area ανά Pool/WaterSystem (idempotent via legacy_kind/legacy_id)."""
    made = 0
    for p in Pool.query.all():
        if not Area.query.filter_by(legacy_kind='pool', legacy_id=p.id).first():
            a = Area(hotel_id=p.hotel_id, template_key='pool', name=p.name,
                             location=p.location, is_active=True, engine_only=True,
                             legacy_kind='pool', legacy_id=p.id)
            db.session.add(a); made += 1
    for w in WaterSystem.query.all():
        if not Area.query.filter_by(legacy_kind='water', legacy_id=w.id).first():
            a = Area(hotel_id=w.hotel_id, template_key='znx', name=w.name,
                     location=w.location, is_active=True, engine_only=True,
                     legacy_kind='water', legacy_id=w.id)
            db.session.add(a); made += 1
    db.session.commit()
    return made


def _point_map():
    m = {}
    for a in Area.query.filter(Area.engine_only.is_(True)).all():
        if a.legacy_kind and a.legacy_id:
            m[(a.legacy_kind, a.legacy_id)] = a.id
    return m


def migrate_legacy_records():
    """ΑΝΤΙΓΡΑΦΗ PoolRecord/WaterRecord → Reading (idempotent). Επιστρέφει counts."""
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
        'pool_records':  PoolRecord.query.count(),
        'water_records': WaterRecord.query.count(),
        'pool_migrated':  Reading.query.filter_by(source_kind='pool').count(),
        'water_migrated': Reading.query.filter_by(source_kind='water').count(),
        'points_pool':  Area.query.filter_by(legacy_kind='pool').count(),
        'points_water': Area.query.filter_by(legacy_kind='water').count(),
        'pools':  Pool.query.count(),
        'systems': WaterSystem.query.count(),
    }


@app.route('/dashboard/measurements', methods=['GET', 'POST'])
def measurements_migrate():
    if not is_admin():
        return redirect(url_for('login'))
    msg = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'points':
            made = ensure_measurement_points()
            log_activity('measurements_points', f'{made} σημεία')
            msg = f'Δημιουργήθηκαν {made} νέα σημεία μέτρησης (όσα έλειπαν).'
        elif action == 'migrate':
            res = migrate_legacy_records()
            log_activity('measurements_migrate', str(res))
            msg = ('Μεταφορά ολοκληρώθηκε — Πισίνες: %d νέες (%d ήδη)· Νερά: %d νέες (%d ήδη)· ορφανά: %d.'
                   % (res['pool'], res['pool_skip'], res['water'], res['water_skip'], res['orphan']))
        return render_template('measurements_migrate.html', st=migration_status(), msg=msg)
    return render_template('measurements_migrate.html', st=migration_status(), msg=msg)


# ════════════════════════════════════════════════════════════════════════════
#  Φ3a — Ρυθμίσεις μηχανής: διαχείριση ΠΕΡΙΟΔΩΝ (MonitorPeriod) ανά template (admin)
#  Καθαρά προσθετικό. Οι παράμετροι/όρια επεξεργάζονται στο /dashboard/templates.
# ════════════════════════════════════════════════════════════════════════════

def _next_period_key(template_key):
    keys = {p.key for p in MonitorPeriod.query.filter_by(template_key=template_key).all()}
    n = 1
    while f'p{n}' in keys:
        n += 1
    return f'p{n}'


@app.route('/dashboard/measurements/periods')
def measurements_periods():
    if not is_admin():
        return redirect(url_for('login'))
    rows = []
    for t in MonitorTemplate.query.filter_by(is_active=True).order_by(MonitorTemplate.sort, MonitorTemplate.name).all():
        periods = MonitorPeriod.query.filter_by(template_key=t.key).order_by(MonitorPeriod.sort, MonitorPeriod.id).all()
        rows.append({'tpl': t, 'periods': periods, 'nparams': len(t.params or [])})
    return render_template('measurements_periods.html', rows=rows)


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
            db.session.add(MonitorPeriod(template_key=tk, key=_next_period_key(tk),
                                         label=label[:40], time=tm[:5], sort=sort))
        db.session.commit()
        log_activity('meas_period_save', f'{tk}:{label}')
    return redirect(url_for('measurements_periods') + '?embed=1')


@app.route('/dashboard/measurements/period/<int:period_id>/delete', methods=['POST'])
def measurements_period_delete(period_id):
    if not is_admin():
        return redirect(url_for('login'))
    p = MonitorPeriod.query.get(period_id)
    if p:
        db.session.delete(p); db.session.commit()   # Α-02: readings ΔΕΝ θίγονται
        log_activity('meas_period_delete', f'{p.template_key}:{p.label}')
    return redirect(url_for('measurements_periods') + '?embed=1')
