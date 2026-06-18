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
    applyPreset();
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

function applyPreset() {
  let per = 'morning';
  try {
    if (typeof PRESET !== 'undefined' && PRESET && PRESET.id) {
      // βρες το ξενοδοχείο που έχει αυτή την πισίνα
      for (let hi=0; hi<HOTELS.length; hi++) {
        if ((HOTELS[hi].pools||[]).some(p => String(p.id)===String(PRESET.id))) {
          const hs=document.getElementById('hotel-select'); hs.value=hi; onHotelChange();
          document.getElementById('pool-select').value=PRESET.id; onPoolChange();
          break;
        }
      }
      if (PRESET.period) per = PRESET.period;
    }
  } catch(e){}
  setPeriod(per);
  try {
    if (typeof PRESET !== 'undefined' && PRESET && PRESET.values) {
      Object.keys(PRESET.values).forEach(k => {
        const el=document.querySelector('[name="'+k+'"]');
        if (!el) return;
        if (el.type==='checkbox') el.checked=!!PRESET.values[k];
        else el.value=PRESET.values[k];
      });
      validate();
    }
  } catch(e){}
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

const NS_FIELDS = ['free_chlorine','combined_chlorine','ph','temp','turbidity','cyanuric_acid','total_alkalinity','orp'];
function validate() {
  NS_FIELDS.forEach(setBadge);
  renderNextSteps();
}

function renderNextSteps() {
  const card=document.getElementById('next-steps'); if(!card) return;
  const body=document.getElementById('next-steps-body');
  const tips=[]; let anyVal=false;
  NS_FIELDS.forEach(id => {
    const el=document.getElementById(id); if(!el||el.value==='') return;
    const val=parseFloat(el.value); if(isNaN(val)) return;
    anyVal=true;
    const [mn,mx]=LIMITS[id]||[null,null];
    const rule=(typeof ACTIONS!=='undefined')?ACTIONS[id]:null; if(!rule) return;
    let txt=null;
    if(mn!=null && val<mn) txt=rule.low;
    else if(mx!=null && val>mx) txt=rule.high;
    if(txt){
      const lab=(typeof PARAM_LABELS!=='undefined'&&PARAM_LABELS[id])?PARAM_LABELS[id]:id;
      const urgent=(id==='free_chlorine'&&val<0.2)||(id==='combined_chlorine'&&val>1.0)||(id==='turbidity'&&val>2.0);
      tips.push({lab,txt,urgent});
    }
  });
  if(tips.length){
    body.innerHTML = tips.map(t =>
      '<div class="ns-item'+(t.urgent?' urgent':'')+'"><i class="ti ti-'+(t.urgent?'alert-triangle':'arrow-right')+'"></i><span><b>'+t.lab+':</b> '+t.txt+'</span></div>'
    ).join('');
    card.style.display='block';
  } else if(anyVal){
    body.innerHTML = '<div class="ns-ok"><i class="ti ti-circle-check"></i> '+(LANG==='en'?'All readings within range.':'Όλες οι τιμές εντός ορίων.')+'</div>';
    card.style.display='block';
  } else {
    card.style.display='none';
  }
}

async function askAI() {
  const btn=document.getElementById('ai-btn'); const out=document.getElementById('ai-reply');
  if(!btn||!out) return;
  const pid=document.getElementById('pool-select')?.value;
  const lines=[];
  NS_FIELDS.forEach(id => { const el=document.getElementById(id); if(el&&el.value!=='') lines.push(id+'='+el.value); });
  const notes=document.getElementById('notes')?.value||'';
  const msg='Μετρήσεις πισίνας ('+currentPeriod+'): '+lines.join(', ')+(notes?('. Σημειώσεις: '+notes):'')+'. Δώσε σύντομες, πρακτικές ενέργειες για εύρυθμη λειτουργία.';
  btn.disabled=true; const orig=btn.innerHTML; btn.innerHTML='<i class="ti ti-loader"></i> '+(LANG==='en'?'Thinking...':'Ανάλυση...');
  try{
    const res=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({pool_id:pid,messages:[{role:'user',content:msg}]})});
    const data=await res.json();
    out.style.display='block';
    out.textContent=data.reply||(data.error==='not_configured'?(LANG==='en'?'AI not configured.':'Το AI δεν έχει ρυθμιστεί.'):(LANG==='en'?'No response.':'Καμία απάντηση.'));
  }catch(e){ out.style.display='block'; out.textContent=(LANG==='en'?'Connection error.':'Σφάλμα σύνδεσης.'); }
  btn.disabled=false; btn.innerHTML=orig;
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
