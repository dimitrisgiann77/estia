// ΕΣΤΙΑ (CONDIAN) — Νερά Χρήσης module JS

let currentPeriod = 'morning';

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('today-date').textContent = new Date().toLocaleDateString('el-GR', {
    weekday:'long', day:'numeric', month:'long', year:'numeric'
  });
  applyLanguage();
  if (typeof HOTELS !== 'undefined') buildHotels();   // v12.3 — επιλογέας δικτύου
  applyPreset();
});

function applyLanguage() {
  document.querySelectorAll('[data-el]').forEach(el => {
    el.textContent = (typeof LANG !== 'undefined' && LANG === 'en')
      ? el.getAttribute('data-en') : el.getAttribute('data-el');
  });
}

// ── v12.3 — Επιλογέας Ξενοδοχείου / Δικτύου Νερού (mirror pools.js) ──
function buildHotels() {
  const hs = document.getElementById('hotel-select');
  if (!hs) return;
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
  const ss = document.getElementById('system-select');
  if (!ss) return;
  ss.innerHTML = '';
  (HOTELS[hi]?.systems || []).forEach(s => {
    const o = document.createElement('option');
    o.value = s.id;
    o.textContent = s.location ? `${s.name} — ${s.location}` : s.name;
    ss.appendChild(o);
  });
  onSystemChange();
}

function onSystemChange() {
  refreshSystemUI();
}

function selectedNames() {
  const hs = document.getElementById('hotel-select');
  const ss = document.getElementById('system-select');
  const h = HOTELS[+(hs?.value || 0)];
  const s = (h?.systems || []).find(x => String(x.id) === String(ss?.value));
  return { hotel: h?.name || '', system: s?.name || '' };
}

// Δείξε καθαρά το επιλεγμένο δίκτυο: header + pills + done-dots + edit badges
function refreshSystemUI() {
  const ss = document.getElementById('system-select');
  const sid = ss ? ss.value : '';
  const n = selectedNames();
  const hdr = document.getElementById('hdr-net');
  if (hdr) hdr.textContent = n.system ? `${n.hotel} — ${n.system}` : (n.hotel || '—');

  const doneMap = (typeof DONE !== 'undefined' && DONE[sid]) ? DONE[sid] : {};
  const lab = { morning: LANG==='en'?'Morning ✓':'Πρωί ✓', afternoon: LANG==='en'?'Afternoon ✓':'Απόγευμα ✓' };

  const box = document.getElementById('system-status');
  if (box) {
    box.innerHTML = '';
    ['morning','afternoon'].forEach(per => {
      if (doneMap[per]) {
        const s = document.createElement('span');
        s.className = 'pool-pill done';
        s.textContent = lab[per];
        box.appendChild(s);
      }
    });
  }

  ['morning','afternoon'].forEach(per => {
    const dot = document.getElementById('dot-' + per);
    if (dot) dot.style.display = doneMap[per] ? 'inline-block' : 'none';
  });

  const badges = document.getElementById('done-badges');
  if (badges) {
    badges.innerHTML = '';
    const blab = { morning: LANG==='en'?'Morning':'Πρωί', afternoon: LANG==='en'?'Afternoon':'Απόγευμα' };
    ['morning','afternoon'].forEach(per => {
      if (doneMap[per]) {
        const a = document.createElement('a');
        a.href = '/edit/' + doneMap[per];
        a.className = 'submitted-badge';
        a.style.textDecoration = 'none';
        a.innerHTML = `<i class="ti ti-check"></i> ${blab[per]} <i class="ti ti-edit" style="font-size:11px;"></i>`;
        badges.appendChild(a);
      }
    });
  }
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

  // Καθαρισμός φόρμας — με διατήρηση επιλεγμένου ξενοδοχείου/δικτύου (v12.3)
  const hs = document.getElementById('hotel-select');
  const ss = document.getElementById('system-select');
  const hv = hs ? hs.value : null;
  const sv = ss ? ss.value : null;
  document.getElementById('water-form').reset();
  if (hs && hv !== null) hs.value = hv;
  if (ss && sv !== null) ss.value = sv;
  document.getElementById('period-input').value = period;
  document.getElementById('submit-msg').style.display = 'none';
  document.getElementById('submit-btn').disabled = false;
  document.getElementById('submit-btn').innerHTML = `<i class="ti ti-send"></i> ${LANG==='en'?'Submit report':'Υποβολή αναφοράς'}`;

  // Καθαρισμός status badges
  document.querySelectorAll('.sbadge').forEach(el => el.remove());
  refreshSystemUI();
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
  renderNextSteps();
}

// v12.83 — κανόνες προτεινόμενων ενεργειών ΖΝΧ/δικτύου (mirror app.py WATER_ACTION_RULES)
const W_RULES = {
  temp_dhw_out:    {mn:60, mx:null, label:'Κολεκτέρ ΖΝΧ (Αναχ.)', low:'Κολεκτέρ ΖΝΧ <60°C: ανέβασε θερμοκρασία αποθήκευσης ≥60°C (κίνδυνος legionella)· έλεγξε λέβητα/εναλλάκτη/θερμοστάτη.'},
  temp_dhw_return: {mn:50, mx:null, label:'Κολεκτέρ Ανακυκλ. (Επιστρ.)', low:'Επιστροφή ανακυκλοφορίας <50°C: ανεπαρκής ανακυκλοφορία· έλεγξε αντλία & βάνες· εξέτασε θερμική απολύμανση/flushing.'},
  temp_kitchen_hot:{mn:50, mx:null, label:'Κουζίνα Ζεστό', low:'Ζεστό Κουζίνας <50°C: flushing του σημείου· έλεγξε ανακυκλοφορία/μόνωση γραμμής.'},
  temp_remote_hot: {mn:50, mx:null, label:'Απομακρυσμένο Ζεστό', low:'Ζεστό Απομακρυσμένου <50°C: flushing· έλεγξε ανακυκλοφορία (κρίσιμο τελευταίο σημείο δικτύου).'},
  temp_tank:       {mn:null, mx:20, label:'Δεξαμενή', high:'Δεξαμενή (κρύο) >20°C: εξέτασε ψύξη/μόνωση/ανανέωση νερού· κίνδυνος ανάπτυξης μικροβίων.'},
  clo2_dhw_out:    {mn:1, mx:2, label:'ClO2 Αναχώρηση ΖΝΧ', low:'ClO2 Αναχώρηση ΖΝΧ <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Αναχώρηση ΖΝΧ >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_dhw_return: {mn:1, mx:2, label:'ClO2 Επιστροφή ΖΝΧ', low:'ClO2 Επιστροφή ΖΝΧ <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Επιστροφή ΖΝΧ >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_tank:       {mn:1, mx:2, label:'ClO2 Δεξαμενή', low:'ClO2 Δεξαμενή <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Δεξαμενή >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_kitchen:    {mn:1, mx:2, label:'ClO2 Κουζίνα', low:'ClO2 Κουζίνα <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Κουζίνα >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_remote:     {mn:1, mx:2, label:'ClO2 Απομακρυσμένο', low:'ClO2 Απομακρυσμένο <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Απομακρυσμένο >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_ro:         {mn:1, mx:2, label:'ClO2 Αντ. Όσμωση', low:'ClO2 Αντ. Όσμωση <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.', high:'ClO2 Αντ. Όσμωση >2 ppm: μείωσε δοσομέτρηση.'}
};
function _wUrgent(id,val){
  if(id==='temp_dhw_out'&&val<50) return true;
  if((id==='temp_dhw_return'||id==='temp_kitchen_hot'||id==='temp_remote_hot')&&val<45) return true;
  if((id==='clo2_dhw_out'||id==='clo2_dhw_return')&&val<0.3) return true;
  return false;
}
function renderNextSteps(){
  const card=document.getElementById('next-steps'); if(!card) return;
  const body=document.getElementById('next-steps-body');
  const tips=[]; let anyVal=false;
  Object.keys(W_RULES).forEach(id=>{
    const el=document.getElementById(id); if(!el||el.value==='') return;
    const val=parseFloat(el.value); if(isNaN(val)) return;
    anyVal=true;
    const r=W_RULES[id]; let txt=null;
    if(r.mn!=null && val<r.mn) txt=r.low;
    else if(r.mx!=null && val>r.mx) txt=r.high;
    if(txt) tips.push({lab:r.label,txt,urgent:_wUrgent(id,val)});
  });
  if(tips.length){
    body.innerHTML=tips.map(t=>'<div class="ns-item'+(t.urgent?' urgent':'')+'"><i class="ti ti-'+(t.urgent?'alert-triangle':'arrow-right')+'"></i><span><b>'+t.lab+':</b> '+t.txt+'</span></div>').join('');
    card.style.display='block';
  } else if(anyVal){
    body.innerHTML='<div class="ns-ok"><i class="ti ti-circle-check"></i> '+(LANG==='en'?'All readings within range.':'Όλες οι τιμές εντός ορίων.')+'</div>';
    card.style.display='block';
  } else { card.style.display='none'; }
}
function applyPreset(){
  let per='morning';
  try{
    if(typeof PRESET!=='undefined'&&PRESET&&PRESET.id){
      for(let hi=0;hi<HOTELS.length;hi++){
        if((HOTELS[hi].systems||[]).some(x=>String(x.id)===String(PRESET.id))){
          const hs=document.getElementById('hotel-select'); hs.value=hi; onHotelChange();
          document.getElementById('system-select').value=PRESET.id; onSystemChange();
          break;
        }
      }
      if(PRESET.period) per=PRESET.period;
    }
  }catch(e){}
  setPeriod(per);
  try{
    if(typeof PRESET!=='undefined'&&PRESET&&PRESET.values){
      Object.keys(PRESET.values).forEach(k=>{
        const el=document.querySelector('[name="'+k+'"]');
        if(!el) return;
        if(el.type==='checkbox') el.checked=!!PRESET.values[k]; else el.value=PRESET.values[k];
      });
      validate();
    }
  }catch(e){}
}
async function askAI(){
  const btn=document.getElementById('ai-btn'); const out=document.getElementById('ai-reply');
  if(!btn||!out) return;
  const lines=[];
  Object.keys(W_RULES).forEach(id=>{const el=document.getElementById(id); if(el&&el.value!=='') lines.push(id+'='+el.value);});
  const notes=document.getElementById('notes')?.value||'';
  const msg='Μετρήσεις δικτύου νερού/ΖΝΧ ('+currentPeriod+'): '+lines.join(', ')+(notes?('. Σημειώσεις: '+notes):'')+'. Δώσε σύντομες, πρακτικές ενέργειες (legionella/θερμοκρασίες/ClO2).';
  btn.disabled=true; const orig=btn.innerHTML; btn.innerHTML='<i class="ti ti-loader"></i> '+(LANG==='en'?'Thinking...':'Ανάλυση...');
  try{
    const res=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:msg}]})});
    const data=await res.json();
    out.style.display='block';
    out.textContent=data.reply||(data.error==='not_configured'?(LANG==='en'?'AI not configured.':'Το AI δεν έχει ρυθμιστεί.'):(LANG==='en'?'No response.':'Καμία απάντηση.'));
  }catch(e){ out.style.display='block'; out.textContent=(LANG==='en'?'Connection error.':'Σφάλμα σύνδεσης.'); }
  btn.disabled=false; btn.innerHTML=orig;
}

async function submitForm() {
  const btn = document.getElementById('submit-btn');
  const msgDiv = document.getElementById('submit-msg');
  const ss = document.getElementById('system-select');
  if (ss && !ss.value) {
    msgDiv.style.display = 'block';
    msgDiv.className = 'submit-msg error';
    msgDiv.textContent = LANG==='en' ? 'Select a water system.' : 'Επίλεξε δίκτυο νερού.';
    return;
  }
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
      // v12.3 — ενημέρωσε pills/badges χωρίς reload
      if (ss && data.record_id && typeof DONE !== 'undefined') {
        (DONE[ss.value] = DONE[ss.value] || {})[currentPeriod] = data.record_id;
        refreshSystemUI();
      }
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
