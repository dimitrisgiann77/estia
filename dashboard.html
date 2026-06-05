<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sergios Hotel — Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/tabler-icons.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f5f5f0; color:#1a1a1a; }
  .topbar { background:#185FA5; color:white; padding:14px 24px; display:flex; align-items:center; justify-content:space-between; }
  .topbar-title { font-size:16px; font-weight:600; }
  .topbar-sub { font-size:12px; opacity:0.7; margin-top:2px; }
  .topbar-right { display:flex; gap:12px; align-items:center; }
  .topbar a { color:white; text-decoration:none; font-size:13px; padding:6px 12px; background:rgba(255,255,255,0.15); border-radius:6px; }
  .topbar a:hover { background:rgba(255,255,255,0.25); }
  .container { max-width:1100px; margin:0 auto; padding:24px; }
  .stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:24px; }
  .stat-card { background:white; border-radius:12px; padding:18px; border:1px solid #e5e5e0; }
  .stat-label { font-size:12px; color:#888; margin-bottom:6px; }
  .stat-value { font-size:28px; font-weight:600; color:#1a1a1a; }
  .stat-sub { font-size:11px; color:#aaa; margin-top:4px; }
  .stat-ok { color:#16a34a; }
  .stat-warn { color:#d97706; }
  .stat-bad { color:#dc2626; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px; }
  @media(max-width:700px){ .grid2 { grid-template-columns:1fr; } }
  .card { background:white; border-radius:12px; padding:20px; border:1px solid #e5e5e0; }
  .card-title { font-size:14px; font-weight:600; color:#333; margin-bottom:16px; display:flex; align-items:center; gap:8px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px; color:#888; font-weight:500; border-bottom:1px solid #eee; }
  td { padding:10px 8px; border-bottom:1px solid #f5f5f0; }
  tr:last-child td { border-bottom:none; }
  .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; }
  .badge-ok { background:#dcfce7; color:#16a34a; }
  .badge-warn { background:#fef3c7; color:#d97706; }
  .badge-bad { background:#fee2e2; color:#dc2626; }
  .badge-admin { background:#dbeafe; color:#185FA5; }
  .badge-staff { background:#f0f0f0; color:#666; }
  .add-user-form { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media(max-width:500px){ .add-user-form { grid-template-columns:1fr; } }
  .add-user-form input, .add-user-form select {
    padding:10px 12px; border:1px solid #e5e5e0; border-radius:8px; font-size:14px; width:100%;
  }
  .btn { padding:10px 18px; border:none; border-radius:8px; font-size:14px; font-weight:500; cursor:pointer; }
  .btn-primary { background:#185FA5; color:white; }
  .btn-primary:hover { background:#0d3d6e; }
  .btn-danger { background:#fee2e2; color:#dc2626; border:none; padding:4px 10px; border-radius:4px; font-size:12px; cursor:pointer; }
  .photo-thumb { width:40px; height:40px; border-radius:6px; object-fit:cover; }
  .section-title { font-size:16px; font-weight:600; margin-bottom:16px; color:#333; }
  .success-msg { background:#dcfce7; color:#16a34a; padding:10px 14px; border-radius:8px; margin-bottom:16px; font-size:13px; }
  .error-msg { background:#fee2e2; color:#dc2626; padding:10px 14px; border-radius:8px; margin-bottom:16px; font-size:13px; }
</style>
</head>
<body>

<div class="topbar">
  <div>
    <div class="topbar-title">🏊 SERGIOS HOTEL — Dashboard Πισίνας</div>
    <div class="topbar-sub">Διαχείριση & Ιστορικό Μετρήσεων</div>
  </div>
  <div class="topbar-right">
    <a href="/app"><i class="ti ti-device-mobile"></i> Εφαρμογή</a>
    <a href="/logout"><i class="ti ti-logout"></i> Έξοδος</a>
  </div>
</div>

<div class="container">

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="{{ 'success-msg' if cat=='success' else 'error-msg' }}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {% if request.args.get('success') == 'user_added' %}
  <div class="success-msg">✅ Χρήστης προστέθηκε επιτυχώς!</div>
  {% endif %}

  <!-- Σημερινές μετρήσεις -->
  <div class="section-title">📊 Σημερινές μετρήσεις</div>
  {% if today %}
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">pH</div>
      <div class="stat-value {{ 'stat-ok' if today.ph and 7.2 <= today.ph <= 7.8 else 'stat-bad' if today.ph else '' }}">
        {{ today.ph or '—' }}
      </div>
      <div class="stat-sub">Στόχος: 7.2–7.8</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Free Chlorine</div>
      <div class="stat-value {{ 'stat-ok' if today.free_chlorine and 2.0 <= today.free_chlorine <= 3.0 else 'stat-bad' if today.free_chlorine else '' }}">
        {{ today.free_chlorine or '—' }}
      </div>
      <div class="stat-sub">mg/L · Στόχος: 2.0–3.0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Alkalinity</div>
      <div class="stat-value {{ 'stat-ok' if today.alkalinity and 80 <= today.alkalinity <= 120 else 'stat-warn' if today.alkalinity else '' }}">
        {{ today.alkalinity or '—' }}
      </div>
      <div class="stat-sub">mg/L · Στόχος: 80–120</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">CYA</div>
      <div class="stat-value {{ 'stat-ok' if today.cya and 30 <= today.cya <= 50 else 'stat-warn' if today.cya else '' }}">
        {{ today.cya or '—' }}
      </div>
      <div class="stat-sub">mg/L · Στόχος: 30–50</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Κολυμβητές</div>
      <div class="stat-value">{{ today.swimmers or '—' }}</div>
      <div class="stat-sub">άτομα σήμερα</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Υποβλήθηκε από</div>
      <div class="stat-value" style="font-size:18px;">{{ today.user.full_name }}</div>
      <div class="stat-sub">{{ today.recorded_at.strftime('%H:%M') }}</div>
    </div>
  </div>
  {% if today.photo_filename %}
  <div class="card" style="margin-bottom:24px;">
    <div class="card-title"><i class="ti ti-camera"></i> Φωτογραφία πισίνας σήμερα</div>
    <img src="/uploads/{{ today.photo_filename }}" style="max-width:100%;border-radius:10px;max-height:300px;object-fit:cover;">
  </div>
  {% endif %}
  {% else %}
  <div class="card" style="margin-bottom:24px;text-align:center;padding:40px;color:#888;">
    <i class="ti ti-clock" style="font-size:32px;"></i>
    <p style="margin-top:10px;">Δεν υπάρχει καταγραφή για σήμερα ακόμα.</p>
  </div>
  {% endif %}

  <!-- Γραφήματα -->
  <div class="grid2">
    <div class="card">
      <div class="card-title"><i class="ti ti-chart-line"></i> pH (τελευταίες 14 ημέρες)</div>
      <canvas id="ph-chart" height="120"></canvas>
    </div>
    <div class="card">
      <div class="card-title"><i class="ti ti-chart-line"></i> Free Chlorine (τελευταίες 14 ημέρες)</div>
      <canvas id="cl-chart" height="120"></canvas>
    </div>
  </div>

  <!-- Ιστορικό -->
  <div class="card" style="margin-bottom:24px;">
    <div class="card-title"><i class="ti ti-history"></i> Ιστορικό μετρήσεων (τελευταίες 30 ημέρες)</div>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>Ημερομηνία</th>
            <th>Υπεύθυνος</th>
            <th>pH</th>
            <th>Free Cl</th>
            <th>Alkalinity</th>
            <th>CYA</th>
            <th>Κολυμβητές</th>
            <th>Φωτό</th>
            <th>Παρατηρήσεις</th>
          </tr>
        </thead>
        <tbody>
          {% for r in records %}
          <tr>
            <td>{{ r.record_date.strftime('%d/%m/%Y') }}</td>
            <td>{{ r.user.full_name }}</td>
            <td>
              {% if r.ph %}
              <span class="badge {{ 'badge-ok' if 7.2 <= r.ph <= 7.8 else 'badge-bad' }}">{{ r.ph }}</span>
              {% else %}—{% endif %}
            </td>
            <td>
              {% if r.free_chlorine %}
              <span class="badge {{ 'badge-ok' if 2.0 <= r.free_chlorine <= 3.0 else 'badge-bad' }}">{{ r.free_chlorine }}</span>
              {% else %}—{% endif %}
            </td>
            <td>
              {% if r.alkalinity %}
              <span class="badge {{ 'badge-ok' if 80 <= r.alkalinity <= 120 else 'badge-warn' }}">{{ r.alkalinity }}</span>
              {% else %}—{% endif %}
            </td>
            <td>
              {% if r.cya %}
              <span class="badge {{ 'badge-ok' if 30 <= r.cya <= 50 else 'badge-warn' }}">{{ r.cya }}</span>
              {% else %}—{% endif %}
            </td>
            <td>{{ r.swimmers or '—' }}</td>
            <td>
              {% if r.photo_filename %}
              <img src="/uploads/{{ r.photo_filename }}" class="photo-thumb">
              {% else %}—{% endif %}
            </td>
            <td style="max-width:200px;font-size:12px;color:#666;">{{ r.notes or '—' }}</td>
          </tr>
          {% endfor %}
          {% if not records %}
          <tr><td colspan="9" style="text-align:center;color:#aaa;padding:20px;">Δεν υπάρχουν καταγραφές ακόμα</td></tr>
          {% endif %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Διαχείριση χρηστών -->
  <div class="grid2">
    <div class="card">
      <div class="card-title"><i class="ti ti-users"></i> Χρήστες</div>
      <table>
        <thead><tr><th>Όνομα</th><th>Username</th><th>Ρόλος</th><th></th></tr></thead>
        <tbody>
          {% for u in users %}
          <tr>
            <td>{{ u.full_name }}</td>
            <td><code style="font-size:12px;">{{ u.username }}</code></td>
            <td><span class="badge {{ 'badge-admin' if u.role=='admin' else 'badge-staff' }}">{{ u.role }}</span></td>
            <td>
              {% if u.role != 'admin' %}
              <a href="/dashboard/delete-user/{{ u.id }}" onclick="return confirm('Διαγραφή χρήστη;')" class="btn-danger">Διαγραφή</a>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title"><i class="ti ti-user-plus"></i> Νέος χρήστης</div>
      <form method="POST" action="/dashboard/add-user">
        <div class="add-user-form">
          <input type="text" name="full_name" placeholder="Ονοματεπώνυμο" required>
          <input type="text" name="username" placeholder="Username" required>
          <input type="password" name="password" placeholder="Password" required>
          <select name="role">
            <option value="staff">Staff (υπεύθυνος)</option>
            <option value="admin">Admin (διαχειριστής)</option>
          </select>
          <select name="language">
            <option value="el">Ελληνικά</option>
            <option value="en">English</option>
          </select>
          <button type="submit" class="btn btn-primary">Προσθήκη χρήστη</button>
        </div>
      </form>
    </div>
  </div>

</div>

<script>
// Φόρτωση δεδομένων γραφημάτων
fetch('/api/history').then(r => r.json()).then(data => {
  const labels = data.map(d => d.date).reverse();
  const phData = data.map(d => d.ph).reverse();
  const clData = data.map(d => d.fc).reverse();

  new Chart(document.getElementById('ph-chart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'pH',
        data: phData,
        borderColor: '#185FA5',
        backgroundColor: 'rgba(24,95,165,0.1)',
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 6.5, max: 9.0,
          grid: { color: '#f0f0f0' }
        }
      }
    }
  });

  new Chart(document.getElementById('cl-chart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Free Chlorine',
        data: clData,
        borderColor: '#16a34a',
        backgroundColor: 'rgba(22,163,74,0.1)',
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 5,
          grid: { color: '#f0f0f0' }
        }
      }
    }
  });
});
</script>
</body>
</html>
