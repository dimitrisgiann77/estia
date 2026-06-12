// CONDIAN HOTELS — Pool Log JS

let currentPeriod = 'morning';

const LIMITS = {
  free_chlorine:     [0.4, 1.5],
  combined_chlorine: [null, 0.5],
  ph:                [7.2, 7.8],
  temp:              [null, 32.0],
  turbidity:         [null, 1.0],
  cyanuric_acid:     [null, 75.0],
  total_alkalinity:  [80.0, 120.0],
  orp:               [650.0, null],
};

document.addEventListener('DOMContentLoaded', () => {
  const d = document.getElementById('today-date');
  if (d) d.textContent = new Date().toLocaleDateString(LANG === 'en' ? 'en-GB' : 'el-GR', {
    weekday:'long', day:'numeric', month:'long', year:'numeric'
  });
  applyLanguage();
  if (typeof HOTELS !== 'undefined' && HOTELS.length) {
    buildHotels();
    setPeriod('morning');
  }
});

function applyLanguage() {
  document.querySelectorAll('[data-el]').forEach(el => {
    el.textContent = (LANG === 'en') ? el.getAttribute('data-en') : el.getAttribute('data-el');
  });
}

function buildHotels() {
  const hs = document.getElementById('hotel-select');
  hs.innerHTML = '';
  HOTELS.forEach((h, i) => {
    const o = document.createElement('option');
    o.value = i; o.textContent = h.name;
    hs.appendChild(o);
  });
  onHotelChange();
}

function onHotelChange() {
  const hi = +document.getElementById('hotel-select').value;
  const ps = document.getElementById('pool-select');
  ps.innerHTML = '';
  (HOTELS[hi]?.pools || []).forEach(p => {
    const o = document.createElement('option');
    o.value = p.id;
    o.textContent = p.location ? `${p.name} — ${p.location}` : p.name;
    ps.appendChild(o);
  });
  onPoolChange();
}

function onPoolChange() {
  const pid = document.getElementById('pool-select').value;
  const box = document.getElementById('pool-status');
  if (!box) return;
  const periods = (typeof DONE !== 'undefined' && DONE[pid]) ? DONE[pid] : [];
  const lab = { morning: LANG==='en'?'Morning ✓':'Πρωί ✓', afternoon: LANG==='en'?'Afternoon ✓':'Απόγευμα ✓' };
  box.innerHTML = '';
  ['morning','afternoon'].forEach(per => {
    if (periods.includes(per)) {
      const s = document.createElement('span');
      s.className = 'pool-pill done';
      s.textContent = lab[per];
      box.appendChild(s);
    }
  });
}

function setPeriod(period) {
  currentPeriod = period;
  document.getElementById('period-input').value = period;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + period).classList.add('active');

  const extra = document.getElementById('morning-extra');
  if (extra) extra.style.display = period === 'morning' ? 'block' : 'none';

  document.querySelectorAll('.sbadge').forEach(el => el.remove());
}

function badge(val, min_v, max_v) {
  if (isNaN(val)) return '';
  const ok = (min_v != null ? val >= min_v : true) && (max_v != null ? val <= max_v : true);
  if (!ok) return `<div class="sbadge bad"><i class="ti ti-alert-circle"></i>${LANG==='en'?'Out of range':'Εκτός ορίων'} (${val})</div>`;
  return `<div class="sbadge ok"><i class="ti ti-check"></i>${LANG==='en'?'OK':'Εντός ορίων'} (${val})</div>`;
}

function actionFor(id, val, mn, mx) {
  if (typeof ACTIONS === 'undefined' || isNaN(val)) return '';
  const rule = ACTIONS[id]; if (!rule) return '';
  let txt = null;
  if (mn != null && val < mn) txt = rule.low;
  else if (mx != null && val > mx) txt = rule.high;
  if (!txt) return '';
  return `<div class="action-tip"><i class="ti ti-arrow-right"></i><span>${txt}</span></div>`;
}
function setBadge(id) {
  const el = document.getElementById(id);
  const st = document.getElementById(id + '_st');
  if (!el || !st) return;
  const val = parseFloat(el.value);
  const [mn, mx] = LIMITS[id] || [null, null];
  st.innerHTML = isNaN(val) ? '' : (badge(val, mn, mx) + actionFor(id, val, mn, mx));
}

function validate() {
  ['free_chlorine','combined_chlorine','ph','temp','turbidity',
   'cyanuric_acid','total_alkalinity','orp'].forEach(setBadge);
}

async function submitForm() {
  const btn = document.getElementById('submit-btn');
  const msgDiv = document.getElementById('submit-msg');
  const poolSel = document.getElementById('pool-select');
  if (!poolSel || !poolSel.value) {
    msgDiv.style.display = 'block';
    msgDiv.className = 'submit-msg error';
    msgDiv.textContent = LANG==='en' ? 'Select a pool.' : 'Επίλεξε πισίνα.';
    return;
  }
  btn.disabled = true;
  btn.innerHTML = `<i class="ti ti-loader"></i> ${LANG==='en'?'Submitting...':'Αποστολή...'}`;

  const formData = new FormData(document.getElementById('pool-form'));
  formData.set('period', currentPeriod);

  try {
    const res = await fetch('/submit-pool', { method:'POST', body:formData });
    const data = await res.json();
    msgDiv.style.display = 'block';
    msgDiv.className = 'submit-msg ' + (data.success ? 'success' : 'error');
    msgDiv.textContent = data.message;
    if (data.success) {
      btn.innerHTML = `<i class="ti ti-check"></i> ${LANG==='en'?'Submitted!':'Υποβλήθηκε!'}`;
      const pid = poolSel.value;
      if (typeof DONE !== 'undefined') {
        DONE[pid] = DONE[pid] || [];
        if (!DONE[pid].includes(currentPeriod)) DONE[pid].push(currentPeriod);
      }
      onPoolChange();
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = `<i class="ti ti-send"></i> ${LANG==='en'?'Submit report':'Υποβολή αναφοράς'}`;
      }, 1500);
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
