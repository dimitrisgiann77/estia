// SERGIOS HOTEL — Water Log App JS

let currentPeriod = 'morning';

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('today-date').textContent = new Date().toLocaleDateString('el-GR', {
    weekday:'long', day:'numeric', month:'long', year:'numeric'
  });
  applyLanguage();
  setPeriod('morning');
});

function applyLanguage() {
  document.querySelectorAll('[data-el]').forEach(el => {
    el.textContent = (typeof LANG !== 'undefined' && LANG === 'en')
      ? el.getAttribute('data-en') : el.getAttribute('data-el');
  });
}

function setPeriod(period) {
  currentPeriod = period;
  document.getElementById('period-input').value = period;

  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + period).classList.add('active');

  // Εμφάνιση/απόκρυψη πεδίων μόνο πρωί
  const morningOnly = ['morning-clo2-extra', 'morning-ph'];
  morningOnly.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = period === 'morning' ? 'block' : 'none';
  });

  // Καθαρισμός φόρμας
  document.getElementById('water-form').reset();
  document.getElementById('period-input').value = period;
  document.getElementById('submit-msg').style.display = 'none';
  document.getElementById('submit-btn').disabled = false;
  document.getElementById('submit-btn').innerHTML = `<i class="ti ti-send"></i> ${LANG==='en'?'Submit report':'Υποβολή αναφοράς'}`;

  // Καθαρισμός status badges
  document.querySelectorAll('.sbadge').forEach(el => el.remove());
}

function badge(val, min_v, max_v) {
  if (isNaN(val)) return '';
  const ok = (min_v ? val >= min_v : true) && (max_v ? val <= max_v : true);
  if (!ok) return `<div class="sbadge bad"><i class="ti ti-alert-circle"></i>${LANG==='en'?'Out of range':'Εκτός ορίων'} (${val})</div>`;
  return `<div class="sbadge ok"><i class="ti ti-check"></i>${LANG==='en'?'OK':'Εντός ορίων'} (${val})</div>`;
}

function setBadge(id, val, min_v, max_v) {
  const el = document.getElementById(id + '_st');
  if (el) el.innerHTML = isNaN(val) ? '' : badge(val, min_v, max_v);
}

function validate() {
  const g = id => parseFloat(document.getElementById(id)?.value);

  setBadge('clo2_tank',       g('clo2_tank'),       1.0, 2.0);
  setBadge('clo2_kitchen',    g('clo2_kitchen'),    1.0, 2.0);
  setBadge('clo2_remote',     g('clo2_remote'),     1.0, 2.0);
  setBadge('clo2_dhw_out',    g('clo2_dhw_out'),    1.0, 2.0);
  setBadge('clo2_dhw_return', g('clo2_dhw_return'), 1.0, 2.0);
  setBadge('clo2_ro',         g('clo2_ro'),         1.0, 2.0);
  setBadge('temp_tank',       g('temp_tank'),       null, 20.0);
  setBadge('temp_dhw_out',    g('temp_dhw_out'),    60.0, null);
  setBadge('temp_dhw_return', g('temp_dhw_return'), 50.0, null);
  setBadge('temp_kitchen_hot', g('temp_kitchen_hot'), 50.0, null);
  setBadge('temp_remote_hot',  g('temp_remote_hot'),  50.0, null);
}

async function submitForm() {
  const btn = document.getElementById('submit-btn');
  const msgDiv = document.getElementById('submit-msg');
  btn.disabled = true;
  btn.innerHTML = `<i class="ti ti-loader"></i> ${LANG==='en'?'Submitting...':'Αποστολή...'}`;

  const formData = new FormData(document.getElementById('water-form'));
  formData.set('period', currentPeriod);

  try {
    const res = await fetch('/submit', { method:'POST', body:formData });
    const data = await res.json();
    msgDiv.style.display = 'block';
    msgDiv.className = 'submit-msg ' + (data.success ? 'success' : 'error');
    msgDiv.textContent = data.message;
    if (data.success) {
      btn.innerHTML = `<i class="ti ti-check"></i> ${LANG==='en'?'Submitted!':'Υποβλήθηκε!'}`;
    } else {
      btn.disabled = false;
      btn.innerHTML = `<i class="ti ti-send"></i> ${LANG==='en'?'Submit report':'Υποβολή αναφοράς'}`;
    }
  } catch(e) {
    msgDiv.style.display = 'block';
    msgDiv.className = 'submit-msg error';
    msgDiv.textContent = LANG==='en' ? 'Connection error.' : 'Σφάλμα σύνδεσης.';
    btn.disabled = false;
    btn.innerHTML = `<i class="ti ti-send"></i> ${LANG==='en'?'Submit report':'Υποβολή αναφοράς'}`;
  }
}
