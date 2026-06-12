"""
CONDIAN HOTELS - Water & Pool Log App v3
Backend: Flask + PostgreSQL + SMTP

Modules:
  - Water Log (νερά χρήσης) — single hotel (Sergios)
  - Pool Log (πισίνες) — multi-hotel / multi-pool
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os, smtplib, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sergios-water-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///water.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SMTP_SERVER    = 'condian.gr'
SMTP_PORT      = 465
EMAIL_FROM     = os.environ.get('EMAIL_FROM', 'report@condian.gr')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_TO_LIST  = ['dimitris@condianhotels.gr', 'm.xypakis@condianhotels.gr', 'g.giakoumakis@condianhotels.gr']
HOTEL_NAME     = 'Sergios Hotel'

db = SQLAlchemy(app)

# ──────────────────────────────────────────────────────────────────────────
#  POOL LIMITS  (min, max) — None means no limit on that side.
#  Βασισμένα σε τυπικά όρια πισινών ξενοδοχείων (ρυθμίσιμα).
# ──────────────────────────────────────────────────────────────────────────
POOL_LIMITS = {
    'free_chlorine':     (0.4, 1.5),    # mg/L ελεύθερο υπολειμματικό χλώριο
    'combined_chlorine': (None, 0.5),   # mg/L συνδεδεμένο χλώριο (max)
    'ph':                (7.2, 7.8),     # pH
    'temp':              (None, 32.0),   # °C θερμοκρασία νερού
    'turbidity':         (None, 1.0),    # NTU θολότητα (max)
    'cyanuric_acid':     (None, 75.0),   # mg/L κυανουρικό οξύ (max)
    'total_alkalinity':  (80.0, 120.0),  # mg/L ολική αλκαλικότητα
    'orp':               (650.0, None),  # mV δυναμικό οξειδοαναγωγής (min)
}

# ──────────────────────────────────────────────────────────────────────────
#  MODELS
# ──────────────────────────────────────────────────────────────────────────
class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(50), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    full_name  = db.Column(db.String(100), nullable=False)
    role       = db.Column(db.String(20), default='staff')
    language   = db.Column(db.String(5), default='el')
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WaterRecord(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_date = db.Column(db.Date, default=date.today, nullable=False)
    period      = db.Column(db.String(10), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, nullable=True)
    updated_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # CLO2
    clo2_tank        = db.Column(db.Float)
    clo2_kitchen     = db.Column(db.Float)
    clo2_remote      = db.Column(db.Float)
    clo2_dhw_out     = db.Column(db.Float)
    clo2_dhw_return  = db.Column(db.Float)
    clo2_ro          = db.Column(db.Float)

    # Σημεία
    location_kitchen = db.Column(db.String(100))
    location_remote  = db.Column(db.String(100))

    # Θερμοκρασία
    temp_tank         = db.Column(db.Float)
    temp_dhw_out      = db.Column(db.Float)
    temp_dhw_return   = db.Column(db.Float)
    temp_ro           = db.Column(db.Float)
    temp_kitchen_cold = db.Column(db.Float)
    temp_kitchen_hot  = db.Column(db.Float)
    temp_remote_cold  = db.Column(db.Float)
    temp_remote_hot   = db.Column(db.Float)

    ph_tank = db.Column(db.Float)
    notes   = db.Column(db.Text)

    user         = db.relationship('User', foreign_keys=[user_id], backref='water_records')
    updated_user = db.relationship('User', foreign_keys=[updated_by])


class Hotel(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), unique=True, nullable=False)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pools = db.relationship('Pool', backref='hotel', order_by='Pool.name')


class Pool(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    hotel_id   = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    name       = db.Column(db.String(120), nullable=False)   # π.χ. Κύρια Πισίνα, Jacuzzi
    location   = db.Column(db.String(120))                   # σημείο / περιοχή
    pool_type  = db.Column(db.String(20), default='pool')    # pool / kids / jacuzzi / indoor
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PoolRecord(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    pool_id     = db.Column(db.Integer, db.ForeignKey('pool.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_date = db.Column(db.Date, default=date.today, nullable=False)
    period      = db.Column(db.String(10), nullable=False)   # morning / afternoon
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, nullable=True)
    updated_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Μετρήσεις ανά περίοδο
    free_chlorine     = db.Column(db.Float)   # mg/L
    combined_chlorine = db.Column(db.Float)   # mg/L
    ph                = db.Column(db.Float)
    temp              = db.Column(db.Float)    # °C
    turbidity         = db.Column(db.Float)    # NTU

    # Περιοδικά (πρωί)
    cyanuric_acid     = db.Column(db.Float)    # mg/L
    total_alkalinity  = db.Column(db.Float)    # mg/L
    orp               = db.Column(db.Float)    # mV

    # Λειτουργικά
    backwash_done     = db.Column(db.Boolean, default=False)
    notes             = db.Column(db.Text)

    pool         = db.relationship('Pool')
    user         = db.relationship('User', foreign_keys=[user_id])
    updated_user = db.relationship('User', foreign_keys=[updated_by])


def flt(data, key):
    try:
        return float(data[key]) if data.get(key) not in (None, '') else None
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────────────────────────────────
#  WATER LOG  (αμετάβλητο)
# ──────────────────────────────────────────────────────────────────────────
def apply_record(record, data, period):
    record.clo2_tank        = flt(data, 'clo2_tank')
    record.clo2_kitchen     = flt(data, 'clo2_kitchen')
    record.clo2_remote      = flt(data, 'clo2_remote')
    record.location_kitchen = data.get('location_kitchen', '')
    record.location_remote  = data.get('location_remote', '')
    record.temp_tank        = flt(data, 'temp_tank')
    record.temp_dhw_out     = flt(data, 'temp_dhw_out')
    record.temp_dhw_return  = flt(data, 'temp_dhw_return')
    record.temp_ro          = flt(data, 'temp_ro')
    record.temp_kitchen_cold = flt(data, 'temp_kitchen_cold')
    record.temp_kitchen_hot  = flt(data, 'temp_kitchen_hot')
    record.temp_remote_cold  = flt(data, 'temp_remote_cold')
    record.temp_remote_hot   = flt(data, 'temp_remote_hot')
    record.notes = data.get('notes', '')
    if period == 'morning':
        record.clo2_dhw_out    = flt(data, 'clo2_dhw_out')
        record.clo2_dhw_return = flt(data, 'clo2_dhw_return')
        record.clo2_ro         = flt(data, 'clo2_ro')
        record.ph_tank         = flt(data, 'ph_tank')

def send_report_email(record, user):
    if not EMAIL_PASSWORD:
        return False
    period_gr = 'Πρωι' if record.period == 'morning' else 'Απογευμα'

    def row(label, val, unit='', min_v=None, max_v=None):
        if val is None:
            return f'<tr><td style="padding:7px 8px;border:1px solid #eee;">{label}</td><td style="padding:7px 8px;border:1px solid #eee;">-</td><td style="padding:7px 8px;border:1px solid #eee;color:#888;">{unit}</td></tr>'
        ok = (min_v is None or val >= min_v) and (max_v is None or val <= max_v)
        color = '#16a34a' if ok else '#dc2626'
        icon  = 'OK' if ok else 'ΠΡΟΣΟΧΗ'
        limit = f'min {min_v}{unit}' if min_v else (f'max {max_v}{unit}' if max_v else '')
        return f'<tr><td style="padding:7px 8px;border:1px solid #eee;">{label}</td><td style="padding:7px 8px;border:1px solid #eee;color:{color};font-weight:500;">{icon}: {val} {unit}</td><td style="padding:7px 8px;border:1px solid #eee;color:#888;">{limit}</td></tr>'

    loc_kit = f' ({record.location_kitchen})' if record.location_kitchen else ''
    loc_rem = f' ({record.location_remote})' if record.location_remote else ''

    clo2_rows  = row('Δεξαμενη', record.clo2_tank, 'ppm', 1.0, 2.0)
    clo2_rows += row(f'Κουζινα{loc_kit}', record.clo2_kitchen, 'ppm', 1.0, 2.0)
    clo2_rows += row(f'Απομακρυσμενο{loc_rem}', record.clo2_remote, 'ppm', 1.0, 2.0)
    if record.period == 'morning':
        clo2_rows += row('Αναχωρηση ΖΝΧ', record.clo2_dhw_out, 'ppm', 1.0, 2.0)
        clo2_rows += row('Επιστροφη ΖΝΧ', record.clo2_dhw_return, 'ppm', 1.0, 2.0)
        clo2_rows += row('Αντ. Οσμωση', record.clo2_ro, 'ppm', 1.0, 2.0)

    temp_rows  = row('Δεξαμενη', record.temp_tank, 'C', None, 20.0)
    temp_rows += row('Κολεκτερ ΖΝΧ (Αναχ.)', record.temp_dhw_out, 'C', 60.0, None)
    temp_rows += row('Κολεκτερ Ανακυκλ. (Επιστρ.)', record.temp_dhw_return, 'C', 50.0, None)
    temp_rows += row('Αντ. Οσμωση', record.temp_ro, 'C')
    temp_rows += row(f'Κουζινα Κρυο{loc_kit}', record.temp_kitchen_cold, 'C')
    temp_rows += row(f'Κουζινα Ζεστο{loc_kit}', record.temp_kitchen_hot, 'C', 50.0, None)
    temp_rows += row(f'Απομακρυσμενο Κρυο{loc_rem}', record.temp_remote_cold, 'C')
    temp_rows += row(f'Απομακρυσμενο Ζεστο{loc_rem}', record.temp_remote_hot, 'C', 50.0, None)

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;">
      <div style="background:#0369a1;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:20px;">Sergios Hotel - Water Log {period_gr}</h1>
        <p style="margin:5px 0 0;opacity:0.8;">{record.record_date.strftime('%d/%m/%Y')} | Υπευθυνος: {user.full_name}</p>
      </div>
      <div style="background:#f9f9f9;padding:20px;border:1px solid #eee;">
        <h2 style="font-size:15px;color:#333;border-bottom:2px solid #0369a1;padding-bottom:6px;">CLO2 (ppm) - Στοχος: 1.0-2.0 ppm</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#0369a1;color:white;"><th style="padding:8px;text-align:left;">Σημειο</th><th style="padding:8px;text-align:left;">Μετρηση</th><th style="padding:8px;text-align:left;">Ορια</th></tr>
          {clo2_rows}
        </table>
        <h2 style="font-size:15px;color:#333;border-bottom:2px solid #0369a1;padding-bottom:6px;margin-top:20px;">Θερμοκρασια (C)</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#0369a1;color:white;"><th style="padding:8px;text-align:left;">Σημειο</th><th style="padding:8px;text-align:left;">Μετρηση</th><th style="padding:8px;text-align:left;">Ορια</th></tr>
          {temp_rows}
        </table>
        {f'<h2 style="font-size:15px;color:#333;margin-top:20px;">pH</h2><p style="background:#fff;padding:10px;border:1px solid #eee;">Δεξαμενη: {record.ph_tank}</p>' if record.period == 'morning' and record.ph_tank else ''}
        {f'<h2 style="font-size:15px;color:#333;margin-top:20px;">Παρατηρησεις</h2><p style="background:#fff;padding:10px;border:1px solid #eee;">{record.notes}</p>' if record.notes else ''}
      </div>
      <div style="background:#f0f0f0;padding:12px;text-align:center;font-size:12px;color:#888;border-radius:0 0 8px 8px;">
        Sergios Hotel - Water Log - {record.record_date.strftime('%d/%m/%Y')} - {period_gr}
      </div>
    </div>"""

    try:
        msg = MIMEMultipart()
        msg['From']    = EMAIL_FROM
        msg['To']      = ', '.join(EMAIL_TO_LIST)
        msg['Subject'] = f'Sergios Hotel - Water Log {period_gr} {record.record_date.strftime("%d/%m/%Y")}'
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        s = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, EMAIL_TO_LIST, msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False


# ──────────────────────────────────────────────────────────────────────────
#  POOL LOG
# ──────────────────────────────────────────────────────────────────────────
def apply_pool_record(record, data, period):
    record.free_chlorine     = flt(data, 'free_chlorine')
    record.combined_chlorine = flt(data, 'combined_chlorine')
    record.ph                = flt(data, 'ph')
    record.temp              = flt(data, 'temp')
    record.turbidity         = flt(data, 'turbidity')
    record.backwash_done     = data.get('backwash_done') in ('1', 'on', 'true', 'True')
    record.notes             = data.get('notes', '')
    if period == 'morning':
        record.cyanuric_acid    = flt(data, 'cyanuric_acid')
        record.total_alkalinity = flt(data, 'total_alkalinity')
        record.orp              = flt(data, 'orp')


def send_pool_report_email(record, user):
    if not EMAIL_PASSWORD:
        return False
    period_gr = 'Πρωι' if record.period == 'morning' else 'Απογευμα'
    pool   = record.pool
    hotel  = pool.hotel.name if pool and pool.hotel else ''
    point  = f' — {pool.location}' if pool and pool.location else ''

    def row(label, val, unit, key):
        min_v, max_v = POOL_LIMITS.get(key, (None, None))
        if val is None:
            return f'<tr><td style="padding:7px 8px;border:1px solid #eee;">{label}</td><td style="padding:7px 8px;border:1px solid #eee;">-</td><td style="padding:7px 8px;border:1px solid #eee;color:#888;">{unit}</td></tr>'
        ok = (min_v is None or val >= min_v) and (max_v is None or val <= max_v)
        color = '#16a34a' if ok else '#dc2626'
        icon  = 'OK' if ok else 'ΠΡΟΣΟΧΗ'
        if min_v is not None and max_v is not None:
            limit = f'{min_v}-{max_v} {unit}'
        elif min_v is not None:
            limit = f'min {min_v} {unit}'
        elif max_v is not None:
            limit = f'max {max_v} {unit}'
        else:
            limit = unit
        return f'<tr><td style="padding:7px 8px;border:1px solid #eee;">{label}</td><td style="padding:7px 8px;border:1px solid #eee;color:{color};font-weight:500;">{icon}: {val} {unit}</td><td style="padding:7px 8px;border:1px solid #eee;color:#888;">{limit}</td></tr>'

    rows  = row('Ελευθερο χλωριο', record.free_chlorine, 'mg/L', 'free_chlorine')
    rows += row('Συνδεδεμενο χλωριο', record.combined_chlorine, 'mg/L', 'combined_chlorine')
    rows += row('pH', record.ph, '', 'ph')
    rows += row('Θερμοκρασια', record.temp, 'C', 'temp')
    rows += row('Θολοτητα', record.turbidity, 'NTU', 'turbidity')
    if record.period == 'morning':
        rows += row('Κυανουρικο οξυ', record.cyanuric_acid, 'mg/L', 'cyanuric_acid')
        rows += row('Ολικη αλκαλικοτητα', record.total_alkalinity, 'mg/L', 'total_alkalinity')
        rows += row('ORP (Redox)', record.orp, 'mV', 'orp')

    backwash = 'Ναι' if record.backwash_done else 'Οχι'

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;">
      <div style="background:#0e7490;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:20px;">{hotel} - Πισινα {period_gr}</h1>
        <p style="margin:5px 0 0;opacity:0.85;">{pool.name if pool else ''}{point}</p>
        <p style="margin:5px 0 0;opacity:0.8;">{record.record_date.strftime('%d/%m/%Y')} | Υπευθυνος: {user.full_name}</p>
      </div>
      <div style="background:#f9f9f9;padding:20px;border:1px solid #eee;">
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#0e7490;color:white;"><th style="padding:8px;text-align:left;">Παραμετρος</th><th style="padding:8px;text-align:left;">Μετρηση</th><th style="padding:8px;text-align:left;">Ορια</th></tr>
          {rows}
        </table>
        <p style="margin-top:14px;font-size:13px;color:#555;">Ανταποπλυση φιλτρου (backwash): <b>{backwash}</b></p>
        {f'<h2 style="font-size:15px;color:#333;margin-top:16px;">Παρατηρησεις</h2><p style="background:#fff;padding:10px;border:1px solid #eee;">{record.notes}</p>' if record.notes else ''}
      </div>
      <div style="background:#f0f0f0;padding:12px;text-align:center;font-size:12px;color:#888;border-radius:0 0 8px 8px;">
        {hotel} - Πισινα {pool.name if pool else ''} - {record.record_date.strftime('%d/%m/%Y')} - {period_gr}
      </div>
    </div>"""

    try:
        msg = MIMEMultipart()
        msg['From']    = EMAIL_FROM
        msg['To']      = ', '.join(EMAIL_TO_LIST)
        msg['Subject'] = f'{hotel} - Πισινα {pool.name if pool else ""} {period_gr} {record.record_date.strftime("%d/%m/%Y")}'
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        s = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, EMAIL_TO_LIST, msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f'Pool email error: {e}')
        return False


# ──────────────────────────────────────────────────────────────────────────
#  AUTH
# ──────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.role == 'admin':
            return redirect(url_for('dashboard'))
        return redirect(url_for('water_app'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and check_password_hash(user.password, password):
            session['user_id']   = user.id
            session['user_name'] = user.full_name
            session['user_role'] = user.role
            session['language']  = user.language
            return redirect(url_for('dashboard') if user.role == 'admin' else url_for('water_app'))
        error = 'Λαθος username η password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ──────────────────────────────────────────────────────────────────────────
#  WATER LOG ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/app')
def water_app():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    today_morning   = WaterRecord.query.filter_by(record_date=date.today(), period='morning').first()
    today_afternoon = WaterRecord.query.filter_by(record_date=date.today(), period='afternoon').first()
    return render_template('app.html', user=user,
                           today_morning=today_morning,
                           today_afternoon=today_afternoon)

@app.route('/submit', methods=['POST'])
def submit():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Μη εξουσιοδοτημενο'}), 401

    user   = User.query.get(session['user_id'])
    data   = request.form
    period = data.get('period', 'morning')

    record = WaterRecord.query.filter_by(record_date=date.today(), period=period).first()
    if record:
        apply_record(record, data, period)
        record.updated_at = datetime.utcnow()
        record.updated_by = user.id
    else:
        record = WaterRecord(user_id=user.id, record_date=date.today(), period=period)
        apply_record(record, data, period)
        db.session.add(record)

    db.session.commit()
    t = threading.Thread(target=send_report_email, args=(record, user))
    t.daemon = True
    t.start()

    period_gr = 'Πρωι' if period == 'morning' else 'Απογευμα'
    return jsonify({'success': True, 'message': f'Καταγραφη {period_gr} αποθηκευτηκε!'})

@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user   = User.query.get(session['user_id'])
    record = WaterRecord.query.get_or_404(record_id)

    if user.role != 'admin' and record.record_date != date.today():
        return redirect(url_for('water_app'))

    if request.method == 'POST':
        apply_record(record, request.form, record.period)
        record.updated_at = datetime.utcnow()
        record.updated_by = user.id
        db.session.commit()
        if user.role == 'admin':
            return redirect(url_for('dashboard') + '?success=updated')
        return redirect(url_for('water_app'))

    return render_template('edit.html', user=user, record=record)

@app.route('/api/record/<int:record_id>')
def api_record(record_id):
    if 'user_id' not in session:
        return jsonify({}), 401
    r = WaterRecord.query.get_or_404(record_id)
    return jsonify({
        'id': r.id, 'period': r.period,
        'record_date': r.record_date.strftime('%d/%m/%Y'),
        'clo2_tank': r.clo2_tank, 'clo2_kitchen': r.clo2_kitchen,
        'clo2_remote': r.clo2_remote, 'clo2_dhw_out': r.clo2_dhw_out,
        'clo2_dhw_return': r.clo2_dhw_return, 'clo2_ro': r.clo2_ro,
        'location_kitchen': r.location_kitchen, 'location_remote': r.location_remote,
        'temp_tank': r.temp_tank, 'temp_dhw_out': r.temp_dhw_out,
        'temp_dhw_return': r.temp_dhw_return, 'temp_ro': r.temp_ro,
        'temp_kitchen_cold': r.temp_kitchen_cold, 'temp_kitchen_hot': r.temp_kitchen_hot,
        'temp_remote_cold': r.temp_remote_cold, 'temp_remote_hot': r.temp_remote_hot,
        'ph_tank': r.ph_tank, 'notes': r.notes or ''
    })

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['el', 'en'] and 'user_id' in session:
        session['language'] = lang
        user = User.query.get(session['user_id'])
        if user:
            user.language = lang
            db.session.commit()
    return redirect(request.referrer or url_for('water_app'))


# ──────────────────────────────────────────────────────────────────────────
#  POOL LOG ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/pools')
def pools_app():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user   = User.query.get(session['user_id'])
    hotels = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()

    # σημερινές καταγραφές ανά (pool_id, period) για ένδειξη "✓"
    todays = PoolRecord.query.filter_by(record_date=date.today()).all()
    done = {}
    for r in todays:
        done.setdefault(str(r.pool_id), []).append(r.period)

    hotels_json = [{
        'id': h.id, 'name': h.name,
        'pools': [{'id': p.id, 'name': p.name, 'location': p.location or '', 'type': p.pool_type}
                  for p in h.pools if p.is_active]
    } for h in hotels]

    return render_template('pools.html', user=user, hotels=hotels,
                           hotels_json=hotels_json, done=done, limits=POOL_LIMITS)

@app.route('/submit-pool', methods=['POST'])
def submit_pool():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Μη εξουσιοδοτημενο'}), 401

    user   = User.query.get(session['user_id'])
    data   = request.form
    period = data.get('period', 'morning')
    pool_id = data.get('pool_id')

    pool = Pool.query.filter_by(id=pool_id, is_active=True).first() if pool_id else None
    if not pool:
        return jsonify({'success': False, 'message': 'Επιλεξτε πισινα'}), 400

    record = PoolRecord.query.filter_by(pool_id=pool.id, record_date=date.today(), period=period).first()
    if record:
        apply_pool_record(record, data, period)
        record.updated_at = datetime.utcnow()
        record.updated_by = user.id
    else:
        record = PoolRecord(pool_id=pool.id, user_id=user.id, record_date=date.today(), period=period)
        apply_pool_record(record, data, period)
        db.session.add(record)

    db.session.commit()
    t = threading.Thread(target=send_pool_report_email, args=(record, user))
    t.daemon = True
    t.start()

    period_gr = 'Πρωι' if period == 'morning' else 'Απογευμα'
    return jsonify({'success': True, 'message': f'Καταγραφη {pool.name} ({period_gr}) αποθηκευτηκε!'})

@app.route('/pools/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_pool_record(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user   = User.query.get(session['user_id'])
    record = PoolRecord.query.get_or_404(record_id)

    if user.role != 'admin' and record.record_date != date.today():
        return redirect(url_for('pools_app'))

    if request.method == 'POST':
        apply_pool_record(record, request.form, record.period)
        record.updated_at = datetime.utcnow()
        record.updated_by = user.id
        db.session.commit()
        if user.role == 'admin':
            return redirect(url_for('pools_dashboard') + '?success=updated')
        return redirect(url_for('pools_app'))

    return render_template('pool_edit.html', user=user, record=record, limits=POOL_LIMITS)

@app.route('/api/pool-record/<int:record_id>')
def api_pool_record(record_id):
    if 'user_id' not in session:
        return jsonify({}), 401
    r = PoolRecord.query.get_or_404(record_id)
    return jsonify({
        'id': r.id, 'period': r.period, 'pool_id': r.pool_id,
        'record_date': r.record_date.strftime('%d/%m/%Y'),
        'free_chlorine': r.free_chlorine, 'combined_chlorine': r.combined_chlorine,
        'ph': r.ph, 'temp': r.temp, 'turbidity': r.turbidity,
        'cyanuric_acid': r.cyanuric_acid, 'total_alkalinity': r.total_alkalinity,
        'orp': r.orp, 'backwash_done': r.backwash_done, 'notes': r.notes or ''
    })


# ──────────────────────────────────────────────────────────────────────────
#  ADMIN DASHBOARDS
# ──────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    records = WaterRecord.query.order_by(WaterRecord.record_date.desc(), WaterRecord.period).limit(60).all()
    users   = User.query.filter_by(is_active=True).all()
    today_m = WaterRecord.query.filter_by(record_date=date.today(), period='morning').first()
    today_a = WaterRecord.query.filter_by(record_date=date.today(), period='afternoon').first()
    return render_template('dashboard.html', records=records, users=users,
                           today_morning=today_m, today_afternoon=today_a)

@app.route('/pools/dashboard')
def pools_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    hotels  = Hotel.query.filter_by(is_active=True).order_by(Hotel.name).all()
    pools   = Pool.query.filter_by(is_active=True).all()
    records = (PoolRecord.query
               .order_by(PoolRecord.record_date.desc(), PoolRecord.recorded_at.desc())
               .limit(80).all())
    return render_template('pools_dashboard.html', hotels=hotels, pools=pools,
                           records=records, limits=POOL_LIMITS)

@app.route('/dashboard/add-user', methods=['POST'])
def add_user():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    data = request.form
    if not User.query.filter_by(username=data['username']).first():
        db.session.add(User(
            username=data['username'],
            password=generate_password_hash(data['password']),
            full_name=data['full_name'],
            role=data.get('role', 'staff'),
            language=data.get('language', 'el')
        ))
        db.session.commit()
    return redirect(url_for('dashboard') + '?success=user_added')

@app.route('/dashboard/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user and user.role != 'admin':
        user.is_active = False
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard/add-hotel', methods=['POST'])
def add_hotel():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    name = request.form.get('name', '').strip()
    if name and not Hotel.query.filter_by(name=name).first():
        db.session.add(Hotel(name=name))
        db.session.commit()
    return redirect(url_for('pools_dashboard') + '?success=hotel_added')

@app.route('/dashboard/delete-hotel/<int:hotel_id>', methods=['POST'])
def delete_hotel(hotel_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    hotel = Hotel.query.get(hotel_id)
    if hotel:
        hotel.is_active = False
        for p in hotel.pools:
            p.is_active = False
        db.session.commit()
    return redirect(url_for('pools_dashboard'))

@app.route('/dashboard/add-pool', methods=['POST'])
def add_pool():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    data = request.form
    hotel_id = data.get('hotel_id')
    name = data.get('name', '').strip()
    if hotel_id and name:
        db.session.add(Pool(
            hotel_id=int(hotel_id),
            name=name,
            location=data.get('location', '').strip(),
            pool_type=data.get('pool_type', 'pool')
        ))
        db.session.commit()
    return redirect(url_for('pools_dashboard') + '?success=pool_added')

@app.route('/dashboard/delete-pool/<int:pool_id>', methods=['POST'])
def delete_pool(pool_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    pool = Pool.query.get(pool_id)
    if pool:
        pool.is_active = False
        db.session.commit()
    return redirect(url_for('pools_dashboard'))


# ──────────────────────────────────────────────────────────────────────────
#  CHART APIs
# ──────────────────────────────────────────────────────────────────────────
@app.route('/api/history')
def api_history():
    if 'user_id' not in session:
        return jsonify([])
    records = WaterRecord.query.filter_by(period='morning').order_by(WaterRecord.record_date.desc()).limit(14).all()
    return jsonify([{
        'date': r.record_date.strftime('%d/%m'),
        'clo2_tank': r.clo2_tank,
        'temp_dhw_out': r.temp_dhw_out,
        'temp_dhw_return': r.temp_dhw_return,
        'temp_tank': r.temp_tank,
    } for r in records])

@app.route('/api/pool-history/<int:pool_id>')
def api_pool_history(pool_id):
    if 'user_id' not in session:
        return jsonify([])
    records = (PoolRecord.query.filter_by(pool_id=pool_id, period='morning')
               .order_by(PoolRecord.record_date.desc()).limit(14).all())
    return jsonify([{
        'date': r.record_date.strftime('%d/%m'),
        'free_chlorine': r.free_chlorine,
        'ph': r.ph,
        'temp': r.temp,
    } for r in records])


# ──────────────────────────────────────────────────────────────────────────
#  INIT
# ──────────────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('sergios2024'), full_name='Δημητρης Γιαννουλακης', role='admin', language='el'))
            db.session.add(User(username='giannhs', password=generate_password_hash('pool2024'), full_name='Γιαννης Γιακουμακης', role='admin', language='el'))
            db.session.add(User(username='xypakis', password=generate_password_hash('water2024'), full_name='Μανος Χυπακης', role='staff', language='el'))
            db.session.commit()
            print('Βαση δεδομενων και χρηστες δημιουργηθηκαν')

        # Seed example hotel + pools (μόνο αν δεν υπάρχουν ξενοδοχεια)
        if not Hotel.query.first():
            sergios = Hotel(name='Sergios Hotel')
            db.session.add(sergios)
            db.session.flush()
            db.session.add(Pool(hotel_id=sergios.id, name='Κύρια Πισίνα', location='Pool bar', pool_type='pool'))
            db.session.add(Pool(hotel_id=sergios.id, name='Παιδική Πισίνα', location='Pool bar', pool_type='kids'))
            db.session.commit()
            print('Δημιουργηθηκε δειγμα ξενοδοχειου & πισινων')


if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
