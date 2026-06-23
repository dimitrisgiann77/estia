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
from app import db, MonitorTemplate, MonitorParam


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
    """Idempotent Φ1 seed: templates Πισίνα/ΖΝΧ + default περίοδοι. ΔΕΝ δημιουργεί σημεία (Φ2)."""
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
