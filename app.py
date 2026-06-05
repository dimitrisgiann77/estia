"""
SERGIOS HOTEL — Pool Management App
Backend: Flask + SQLite + SendGrid
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os, json, base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

app = Flask(__name__)

# ─── Ρυθμίσεις ───────────────────────────────────────────────
app.secret_key = os.environ.get('SECRET_KEY', 'sergios-pool-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pool.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max φωτογραφία

# Email ρυθμίσεις (βάλε στο Railway environment variables)
SENDGRID_API_KEY  = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_FROM        = os.environ.get('EMAIL_FROM', 'pool@sergioshotel.gr')
EMAIL_TO          = os.environ.get('EMAIL_TO', 'info@sergioshotel.gr')
HOTEL_NAME        = 'Sergios Hotel'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ─── Μοντέλα Βάσης Δεδομένων ─────────────────────────────────

class User(db.Model):
    """Χρήστες της εφαρμογής"""
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(50), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    full_name    = db.Column(db.String(100), nullable=False)
    role         = db.Column(db.String(20), default='staff')  # 'admin' ή 'staff'
    language     = db.Column(db.String(5), default='el')      # 'el' ή 'en'
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class DailyRecord(db.Model):
    """Ημερήσιες καταγραφές μετρήσεων"""
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_date    = db.Column(db.Date, default=date.today, nullable=False)
    recorded_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Μετρήσεις Pool Line
    ph             = db.Column(db.Float)
    alkalinity     = db.Column(db.Float)
    free_chlorine  = db.Column(db.Float)
    total_chlorine = db.Column(db.Float)
    cya            = db.Column(db.Float)
    water_temp     = db.Column(db.Float)
    swimmers       = db.Column(db.Integer)
    clarity        = db.Column(db.String(20))
    algicide_done  = db.Column(db.Boolean, default=False)

    # Συστάσεις χημικών (JSON)
    recommendations = db.Column(db.Text)

    # Checklist
    check_walls        = db.Column(db.Boolean, default=False)
    check_backwash     = db.Column(db.Boolean, default=False)
    check_pump         = db.Column(db.Boolean, default=False)
    check_skimmer      = db.Column(db.Boolean, default=False)
    check_waterline    = db.Column(db.Boolean, default=False)
    check_prefilter    = db.Column(db.Boolean, default=False)

    # Φωτογραφία + Παρατηρήσεις
    photo_filename  = db.Column(db.String(200))
    notes           = db.Column(db.Text)

    # Σχέση με χρήστη
    user = db.relationship('User', backref='records')

# ─── Βοηθητικές συναρτήσεις ──────────────────────────────────

def calculate_chemicals(ph, alk, fc, tc, cya, water_temp, swimmers, clarity, algicide_done):
    """Υπολογισμός χημικών βάσει μετρήσεων — 90m³ πισίνα"""
    VOL = 90
    AIR_TEMP = 26.0  # Μέση θερμοκρασία Χερσόνησου καλοκαίρι
    results = []

    high_temp = (AIR_TEMP > 25) or (water_temp and water_temp > 28)
    high_load = (swimmers and swimmers > 40) or high_temp
    combined  = max(0, (tc or 0) - (fc or 0)) if tc and fc else 0
    min_fc    = max(2.0, (cya or 0) * 0.075) if cya else 2.0
    needs_shock = combined > 0.5 or clarity in ['cloudy', 'green']

    # pH
    if ph:
        if ph > 7.8:
            dose = round((ph - 7.4) * VOL * 0.18)
            results.append({'product': 'pH−', 'dose': f'{dose} g',
                'note': f'Μείωσε pH {ph} → 7.4. Βράδυ ή πρωί (2h πριν ανοίξει).', 'type': 'success'})
        elif ph < 7.2:
            dose = round((7.4 - ph) * VOL * 0.14)
            results.append({'product': 'pH+', 'dose': f'{dose} g',
                'note': f'Ανύψωσε pH {ph} → 7.4.', 'type': 'info'})

    # CYA
    if cya:
        if cya > 70:
            results.append({'product': 'CYA — Αραίωση νερού', 'dose': '—',
                'note': f'CYA {cya} mg/L — αδειάσε μέρος νερού και αναπλήρωσε με φρέσκο.', 'type': 'danger'})
        elif cya < 30:
            results.append({'product': 'CYA χαμηλό', 'dose': '—',
                'note': f'CYA {cya} mg/L — οι ταμπλέτες θα το ανεβάσουν σταδιακά.', 'type': 'warning'})

    # Χλώριο
    if fc is not None:
        if needs_shock:
            dose = VOL * 10
            reasons = []
            if combined > 0.5: reasons.append(f'δεσμευμένο χλώριο {combined:.2f} mg/L')
            if clarity == 'cloudy': reasons.append('θολό νερό')
            if clarity == 'green': reasons.append('άλγη')
            results.append({'product': 'Astral Trichloro Powder — SHOCK', 'dose': f'{dose} g',
                'note': f'Λόγω: {", ".join(reasons)}. Διάλυσε σε νερό, ρίξε στην πισίνα. Βράδυ, χωρίς κολυμβητές. Είσοδος μετά 12–14 ώρες.', 'type': 'danger'})
        else:
            tabs = 2 if (fc < min_fc or high_load) else 1
            reason = f'Free Chlorine {fc} mg/L' if fc < min_fc else ('υψηλό φορτίο/θερμοκρ.' if high_load else 'maintenance')
            results.append({'product': 'Aqua Clor Ταμπλέτες 200g', 'dose': f'{tabs} τεμ.',
                'note': f'{reason}. {"1 ταμπλέτα σε κάθε skimmer." if tabs==2 else "1 ταμπλέτα σε έναν skimmer."}', 'type': 'info'})

    # Alkalinity
    if alk:
        if alk < 80:
            dose = round((80 - alk) * VOL * 0.015)
            results.append({'product': 'Sodium Bicarbonate', 'dose': f'{dose} g',
                'note': f'Alkalinity {alk} → στόχος 80–120 mg/L.', 'type': 'warning'})
        elif alk > 150:
            results.append({'product': 'Alkalinity υψηλή', 'dose': '—',
                'note': f'Alkalinity {alk} mg/L — μείωσε με pH−.', 'type': 'danger'})

    # Αλγοκτόνο
    if not algicide_done:
        dose = round(375 * VOL / 50)
        results.append({'product': 'Aqua Clor Algicide Super', 'dose': f'{dose} ml',
            'note': 'Εβδομαδιαία δόση. Τέλος ημερήσιας χρήσης, κοντά στις εισόδους νερού.', 'type': 'success'})

    if not results:
        results.append({'product': 'Όλα εντός ορίων!', 'dose': '—',
            'note': 'Δεν απαιτείται καμία ενέργεια σήμερα.', 'type': 'ok'})

    return results

def send_report_email(record, user, recommendations, photo_path=None):
    """Αποστολή email report στον admin"""
    if not SENDGRID_API_KEY:
        print("⚠ SendGrid API key δεν έχει οριστεί")
        return False

    checklist_items = {
        'Καθαρισμός τοιχίων/πυθμένα': record.check_walls,
        'Backwash φίλτρου': record.check_backwash,
        'Έλεγχος αντλίας': record.check_pump,
        'Έλεγχος skimmer': record.check_skimmer,
        'Καθαρισμός ίσαλης γραμμής': record.check_waterline,
        'Καθαρισμός προφίλτρων': record.check_prefilter,
    }

    recs_html = ''.join([
        f'<tr style="border-bottom:1px solid #eee;">'
        f'<td style="padding:8px;font-weight:500;">{r["product"]}</td>'
        f'<td style="padding:8px;">{r["dose"]}</td>'
        f'<td style="padding:8px;color:#666;">{r["note"]}</td>'
        f'</tr>' for r in recommendations
    ])

    chk_html = ''.join([
        f'<tr><td style="padding:6px;">{"✅" if v else "❌"} {k}</td></tr>'
        for k, v in checklist_items.items()
    ])

    combined = max(0, (record.total_chlorine or 0) - (record.free_chlorine or 0))

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#185FA5;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:20px;">🏊 {HOTEL_NAME} — Ημερήσιο Report Πισίνας</h1>
        <p style="margin:5px 0 0;opacity:0.8;">{record.record_date.strftime('%A, %d %B %Y')} &nbsp;|&nbsp; Υπεύθυνος: {user.full_name}</p>
      </div>

      <div style="background:#f9f9f9;padding:20px;border:1px solid #eee;">

        <h2 style="font-size:15px;color:#333;border-bottom:2px solid #185FA5;padding-bottom:6px;">📊 Μετρήσεις Pool Line</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#fff;">
            <td style="padding:8px;border:1px solid #eee;"><b>pH</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.ph or '—'}</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">Στόχος: 7.2–7.8</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:8px;border:1px solid #eee;"><b>Free Chlorine</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.free_chlorine or '—'} mg/L</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">Στόχος: 2.0–3.0</td>
          </tr>
          <tr style="background:#fff;">
            <td style="padding:8px;border:1px solid #eee;"><b>Total Chlorine</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.total_chlorine or '—'} mg/L</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">≥ Free Chlorine</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:8px;border:1px solid #eee;"><b>Δεσμευμένο χλώριο</b></td>
            <td style="padding:8px;border:1px solid #eee;">{combined:.2f} mg/L</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">Πρέπει: &lt; 0.5</td>
          </tr>
          <tr style="background:#fff;">
            <td style="padding:8px;border:1px solid #eee;"><b>Alkalinity</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.alkalinity or '—'} mg/L</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">Στόχος: 80–120</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:8px;border:1px solid #eee;"><b>CYA</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.cya or '—'} mg/L</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;">Στόχος: 30–50</td>
          </tr>
          <tr style="background:#fff;">
            <td style="padding:8px;border:1px solid #eee;"><b>Θερμοκρ. νερού</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.water_temp or '—'} °C</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;"></td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:8px;border:1px solid #eee;"><b>Κολυμβητές</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.swimmers or '—'}</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;"></td>
          </tr>
          <tr style="background:#fff;">
            <td style="padding:8px;border:1px solid #eee;"><b>Διαύγεια</b></td>
            <td style="padding:8px;border:1px solid #eee;">{record.clarity or '—'}</td>
            <td style="padding:8px;border:1px solid #eee;color:#888;"></td>
          </tr>
        </table>

        <h2 style="font-size:15px;color:#333;border-bottom:2px solid #185FA5;padding-bottom:6px;margin-top:20px;">🧪 Συστάσεις χημικών</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#185FA5;color:white;">
            <th style="padding:8px;text-align:left;">Χημικό</th>
            <th style="padding:8px;text-align:left;">Δόση</th>
            <th style="padding:8px;text-align:left;">Σημείωση</th>
          </tr>
          {recs_html}
        </table>

        <h2 style="font-size:15px;color:#333;border-bottom:2px solid #185FA5;padding-bottom:6px;margin-top:20px;">✅ Checklist εργασιών</h2>
        <table style="width:100%;border-collapse:collapse;">
          {chk_html}
        </table>

        {'<h2 style="font-size:15px;color:#333;border-bottom:2px solid #185FA5;padding-bottom:6px;margin-top:20px;">📝 Παρατηρήσεις</h2><p style="background:#fff;padding:12px;border:1px solid #eee;border-radius:4px;">' + (record.notes or '—') + '</p>' if record.notes else ''}

      </div>
      <div style="background:#f0f0f0;padding:12px;text-align:center;font-size:12px;color:#888;border-radius:0 0 8px 8px;">
        {HOTEL_NAME} · Διαχείριση Πισίνας · {record.record_date.strftime('%d/%m/%Y %H:%M')}
      </div>
    </div>
    """

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=EMAIL_TO,
        subject=f'🏊 {HOTEL_NAME} — Report Πισίνας {record.record_date.strftime("%d/%m/%Y")}',
        html_content=html
    )

    # Επισύναψη φωτογραφίας αν υπάρχει
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        ext = photo_path.split('.')[-1].lower()
        mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'
        attachment = Attachment(
            FileContent(encoded),
            FileName(f'pool_{record.record_date}.{ext}'),
            FileType(mime),
            Disposition('attachment')
        )
        message.attachment = attachment

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False

# ─── Routes ──────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.role == 'admin':
            return redirect(url_for('dashboard'))
        return redirect(url_for('pool_app'))
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
            return redirect(url_for('dashboard') if user.role == 'admin' else url_for('pool_app'))
        error = 'Λάθος username ή password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/app')
def pool_app():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Έλεγξε αν υπάρχει ήδη καταγραφή σήμερα
    today_record = DailyRecord.query.filter_by(
        user_id=user.id, record_date=date.today()
    ).first()
    return render_template('app.html', user=user, today_record=today_record)

@app.route('/submit', methods=['POST'])
def submit():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Μη εξουσιοδοτημένο'}), 401

    user = User.query.get(session['user_id'])
    data = request.form

    # Αποθήκευση φωτογραφίας
    photo_filename = None
    photo_path = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and photo.filename:
            ext = photo.filename.rsplit('.', 1)[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'heic']:
                photo_filename = f"pool_{user.id}_{date.today()}_{int(datetime.utcnow().timestamp())}.{ext}"
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(photo_filename))
                photo.save(photo_path)

    def flt(key): return float(data[key]) if data.get(key) else None
    def nt(key):  return int(data[key]) if data.get(key) else None
    def bl(key):  return data.get(key) == 'true'

    ph    = flt('ph')
    alk   = flt('alkalinity')
    fc    = flt('free_chlorine')
    tc    = flt('total_chlorine')
    cya   = flt('cya')
    wt    = flt('water_temp')
    sw    = nt('swimmers')
    cl    = data.get('clarity', '')
    algd  = bl('algicide_done')

    recommendations = calculate_chemicals(ph, alk, fc, tc, cya, wt, sw, cl, algd)

    record = DailyRecord(
        user_id=user.id,
        record_date=date.today(),
        ph=ph, alkalinity=alk, free_chlorine=fc, total_chlorine=tc,
        cya=cya, water_temp=wt, swimmers=sw, clarity=cl, algicide_done=algd,
        recommendations=json.dumps(recommendations, ensure_ascii=False),
        check_walls=bl('check_walls'), check_backwash=bl('check_backwash'),
        check_pump=bl('check_pump'), check_skimmer=bl('check_skimmer'),
        check_waterline=bl('check_waterline'), check_prefilter=bl('check_prefilter'),
        photo_filename=photo_filename,
        notes=data.get('notes', '')
    )
    db.session.add(record)
    db.session.commit()

    # Αποστολή email
    email_sent = send_report_email(record, user, recommendations, photo_path)

    return jsonify({
        'success': True,
        'message': 'Καταγραφή αποθηκεύτηκε!' + (' Email απεστάλη.' if email_sent else ''),
        'recommendations': recommendations
    })

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['el', 'en'] and 'user_id' in session:
        session['language'] = lang
        user = User.query.get(session['user_id'])
        if user:
            user.language = lang
            db.session.commit()
    return redirect(request.referrer or url_for('pool_app'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── Admin Dashboard ──────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    records = DailyRecord.query.order_by(DailyRecord.record_date.desc()).limit(30).all()
    users   = User.query.filter_by(is_active=True).all()
    today   = DailyRecord.query.filter_by(record_date=date.today()).first()
    return render_template('dashboard.html', records=records, users=users, today=today)

@app.route('/dashboard/add-user', methods=['POST'])
def add_user():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    data = request.form
    existing = User.query.filter_by(username=data['username']).first()
    if existing:
        return redirect(url_for('dashboard') + '?error=exists')
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        full_name=data['full_name'],
        role=data.get('role', 'staff'),
        language=data.get('language', 'el')
    )
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('dashboard') + '?success=user_added')

@app.route('/dashboard/delete-user/<int:user_id>')
def delete_user(user_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user and user.role != 'admin':
        user.is_active = False
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/api/history')
def api_history():
    if 'user_id' not in session:
        return jsonify([])
    records = DailyRecord.query.order_by(DailyRecord.record_date.desc()).limit(14).all()
    return jsonify([{
        'date': r.record_date.strftime('%d/%m'),
        'ph': r.ph, 'fc': r.free_chlorine,
        'alk': r.alkalinity, 'cya': r.cya
    } for r in records if r.ph or r.free_chlorine])

# ─── Αρχικοποίηση ─────────────────────────────────────────────

def init_db():
    """Δημιουργία βάσης και admin χρήστη"""
    with app.app_context():
        db.create_all()
        # Δημιουργία admin αν δεν υπάρχει
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('sergios2024'),
                full_name='Δημήτρης Γιαννουλάκης',
                role='admin',
                language='el'
            )
            db.session.add(admin)
            # Manager
            manager = User(
                username='giannhs',
                password=generate_password_hash('pool2024'),
                full_name='Γιάννης Γιακουμάκης',
                role='admin',
                language='el'
            )
            db.session.add(manager)
            db.session.commit()
            print('✅ Βάση δεδομένων και χρήστες δημιουργήθηκαν')

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
