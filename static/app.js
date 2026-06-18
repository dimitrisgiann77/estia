// Εστία — Νερά Χρήσης (redesign v12.88)
let currentPeriod='morning';
const W_LIMITS={
  clo2_tank:[1,2],clo2_kitchen:[1,2],clo2_remote:[1,2],clo2_dhw_out:[1,2],clo2_dhw_return:[1,2],clo2_ro:[1,2],
  temp_tank:[null,20],temp_dhw_out:[60,null],temp_dhw_return:[50,null],temp_kitchen_hot:[50,null],temp_remote_hot:[50,null],
};
const W_RULES={
  temp_dhw_out:{label:'Κολεκτέρ ΖΝΧ (Αναχ.)',low:'Κολεκτέρ ΖΝΧ <60°C: ανέβασε θερμοκρασία αποθήκευσης ≥60°C (κίνδυνος legionella)· έλεγξε λέβητα/εναλλάκτη/θερμοστάτη.'},
  temp_dhw_return:{label:'Κολεκτέρ Ανακυκλ.',low:'Επιστροφή ανακυκλοφορίας <50°C: ανεπαρκής ανακυκλοφορία· έλεγξε αντλία & βάνες· εξέτασε θερμική απολύμανση.'},
  temp_kitchen_hot:{label:'Κουζίνα Ζεστό',low:'Ζεστό Κουζίνας <50°C: flushing του σημείου· έλεγξε ανακυκλοφορία/μόνωση γραμμής.'},
  temp_remote_hot:{label:'Απομακρυσμένο Ζεστό',low:'Ζεστό Απομακρυσμένου <50°C: flushing· έλεγξε ανακυκλοφορία (κρίσιμο τελευταίο σημείο).'},
  temp_tank:{label:'Δεξαμενή',high:'Δεξαμενή (κρύο) >20°C: εξέτασε ψύξη/μόνωση/ανανέωση νερού· κίνδυνος μικροβίων.'},
  clo2_dhw_out:{label:'ClO2 Αναχώρηση ΖΝΧ',low:'ClO2 Αναχώρηση ΖΝΧ <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.',high:'ClO2 Αναχώρηση ΖΝΧ >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_dhw_return:{label:'ClO2 Επιστροφή ΖΝΧ',low:'ClO2 Επιστροφή ΖΝΧ <1 ppm: αύξησε δοσομέτρηση· έλεγξε αντλία/απόθεμα.',high:'ClO2 Επιστροφή ΖΝΧ >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_tank:{label:'ClO2 Δεξαμενή',low:'ClO2 Δεξαμενή <1 ppm: αύξησε δοσομέτρηση.',high:'ClO2 Δεξαμενή >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_kitchen:{label:'ClO2 Κουζίνα',low:'ClO2 Κουζίνα <1 ppm: αύξησε δοσομέτρηση.',high:'ClO2 Κουζίνα >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_remote:{label:'ClO2 Απομακρυσμένο',low:'ClO2 Απομακρυσμένο <1 ppm: αύξησε δοσομέτρηση.',high:'ClO2 Απομακρυσμένο >2 ppm: μείωσε δοσομέτρηση.'},
  clo2_ro:{label:'ClO2 Αντ. Όσμωση',low:'ClO2 Αντ. Όσμωση <1 ppm: αύξησε δοσομέτρηση.',high:'ClO2 Αντ. Όσμωση >2 ppm: μείωσε δοσομέτρηση.'},
};
const W_BASE=['clo2_tank','clo2_kitchen','clo2_remote','temp_tank','temp_dhw_out','temp_dhw_return','temp_ro','temp_kitchen_cold','temp_kitchen_hot','temp_remote_cold','temp_remote_hot'];
const W_MORNING=['clo2_dhw_out','clo2_dhw_return','clo2_ro','ph_tank'];
function reqFields(){ return currentPeriod==='morning'? W_BASE.concat(W_MORNING): W_BASE.slice(); }

document.addEventListener('DOMContentLoaded',()=>{ if(typeof HOTELS!=='undefined') buildHotels(); applyPreset(); });

function buildHotels(){
  const hs=document.getElementById('hotel-select'); if(!hs) return; hs.innerHTML='';
  HOTELS.forEach((h,i)=>{ const o=document.createElement('option'); o.value=i; o.textContent=h.name; hs.appendChild(o); });
  onHotelChange();
}
function onHotelChange(){
  const hi=+document.getElementById('hotel-select').value; const ss=document.getElementById('system-select'); if(!ss) return; ss.innerHTML='';
  (HOTELS[hi]?.systems||[]).forEach(s=>{ const o=document.createElement('option'); o.value=s.id; o.textContent=s.location?`${s.name} — ${s.location}`:s.name; ss.appendChild(o); });
  onSystemChange();
}
function onSystemChange(){
  const ss=document.getElementById('system-select'); const opt=ss?ss.options[ss.selectedIndex]:null;
  const pl=document.getElementById('mf-place'); if(pl&&opt) pl.textContent=opt.textContent;
  const box=document.getElementById('system-status'); if(box){ box.innerHTML='';
    const sid=ss?ss.value:''; const d=(typeof DONE!=='undefined'&&DONE[sid])?DONE[sid]:{};
    ['morning','afternoon'].forEach(per=>{ if(d[per]){ const s=document.createElement('span'); s.className='mf-done';
      s.innerHTML='<i class="ti ti-check"></i> '+(per==='morning'?'Πρωί καταχωρήθηκε':'Απόγευμα καταχωρήθηκε'); box.appendChild(s); }});
  }
  if(typeof validate==='function') updateRequired();
}

function setPeriod(period){
  currentPeriod=period; document.getElementById('period-input').value=period;
  document.getElementById('tab-morning').classList.toggle('active',period==='morning');
  document.getElementById('tab-afternoon').classList.toggle('active',period==='afternoon');
  ['morning-clo2-extra','morning-ph'].forEach(id=>{ const el=document.getElementById(id); if(el) el.style.display=period==='morning'?'':'none'; });
  validate();
}

function fieldStatus(id){
  const el=document.getElementById(id), st=document.getElementById(id+'_st'); if(!el) return;
  el.classList.remove('ok','bad'); if(st){st.className='mf-hint';st.innerHTML='';}
  if(el.value==='') return; const val=parseFloat(el.value); if(isNaN(val)) return;
  const lim=W_LIMITS[id]; if(!lim){ return; }
  const [mn,mx]=lim; const ok=(mn!=null?val>=mn:true)&&(mx!=null?val<=mx:true);
  el.classList.add(ok?'ok':'bad');
  if(st){ st.className='mf-hint '+(ok?'ok':'bad');
    st.innerHTML=ok?'<i class="ti ti-check"></i> Εντός ορίων':'<i class="ti ti-alert-triangle"></i> '+(val<(mn??-Infinity)?'Χαμηλό':'Υψηλό'); }
}

function validate(){ reqFields().forEach(fieldStatus); renderNextSteps(); updateRequired(); }

function updateRequired(){
  const fields=reqFields(); let filled=0;
  fields.forEach(id=>{ const el=document.getElementById(id); if(el&&el.value!=='') filled++; });
  const n=fields.length; const cnt=document.getElementById('mf-count');
  const btn=document.getElementById('submit-btn'), lbl=document.getElementById('submit-lbl');
  const sysOk=!!document.getElementById('system-select')?.value; const all=sysOk&&filled===n;
  if(btn) btn.disabled=!all;
  if(lbl) lbl.textContent=all?'Αποθήκευση καταγραφής':'Συμπλήρωσε όλα τα πεδία';
  if(cnt) cnt.textContent=all?'Όλα τα πεδία συμπληρωμένα':(filled+' από '+n+' πεδία συμπληρωμένα');
}

function renderNextSteps(){
  const card=document.getElementById('next-steps'); if(!card) return;
  const body=document.getElementById('next-steps-body'); const tips=[]; let anyVal=false;
  reqFields().forEach(id=>{ const el=document.getElementById(id); if(!el||el.value==='') return;
    const val=parseFloat(el.value); if(isNaN(val)) return; anyVal=true;
    const lim=W_LIMITS[id], r=W_RULES[id]; if(!lim||!r) return; const [mn,mx]=lim; let txt=null;
    if(mn!=null&&val<mn) txt=r.low; else if(mx!=null&&val>mx) txt=r.high;
    if(txt){ const urgent=(id==='temp_dhw_out'&&val<50)||((id==='temp_dhw_return'||id==='temp_kitchen_hot'||id==='temp_remote_hot')&&val<45)||((id==='clo2_dhw_out'||id==='clo2_dhw_return')&&val<0.3);
      tips.push({lab:r.label,txt,urgent}); }
  });
  card.classList.remove('ok');
  if(tips.length){ document.querySelector('.mf-actions-h').innerHTML='<i class="ti ti-bulb"></i> Προτεινόμενες ενέργειες';
    body.innerHTML=tips.map(t=>'<div class="mf-act'+(t.urgent?' urgent':'')+'"><i class="ti ti-'+(t.urgent?'alert-triangle':'point-filled')+'"></i><span><b>'+t.lab+':</b> '+t.txt+'</span></div>').join(''); card.style.display='block';
  } else if(anyVal){ card.classList.add('ok'); document.querySelector('.mf-actions-h').innerHTML='<i class="ti ti-circle-check"></i> Όλες οι τιμές εντός ορίων'; body.innerHTML=''; card.style.display='block';
  } else { card.style.display='none'; }
}

function applyPreset(){
  let per='morning';
  try{ if(typeof PRESET!=='undefined'&&PRESET&&PRESET.id){
    for(let hi=0;hi<HOTELS.length;hi++){ if((HOTELS[hi].systems||[]).some(x=>String(x.id)===String(PRESET.id))){
      const hs=document.getElementById('hotel-select'); hs.value=hi; onHotelChange();
      document.getElementById('system-select').value=PRESET.id; onSystemChange(); break; } }
    if(PRESET.period) per=PRESET.period;
  } }catch(e){}
  setPeriod(per);
  if(typeof PRESET!=='undefined'&&PRESET&&PRESET.period){
    const tabs=document.querySelector('.mf-tabs'); if(tabs) tabs.style.display='none';
    const pl=document.getElementById('mf-place'); if(pl) pl.innerHTML += ' · <i class="ti ti-'+(per==='morning'?'sun':'moon')+'"></i> '+(per==='morning'?'Πρωί 08:00':'Απόγευμα 17:00');
  }
  try{ if(typeof PRESET!=='undefined'&&PRESET&&PRESET.values){
    Object.keys(PRESET.values).forEach(k=>{ const el=document.querySelector('[name="'+k+'"]'); if(!el) return;
      if(el.type==='checkbox') el.checked=!!PRESET.values[k]; else el.value=PRESET.values[k]; });
    validate();
  } }catch(e){}
}

async function submitForm(){
  const btn=document.getElementById('submit-btn'), ss=document.getElementById('system-select');
  if(!ss||!ss.value){ showMsg('error','Επίλεξε δίκτυο νερού.'); return; }
  const miss=reqFields().filter(id=>{ const el=document.getElementById(id); return !el||el.value===''; });
  if(miss.length){ showMsg('error','Συμπλήρωσε όλα τα υποχρεωτικά πεδία.'); return; }
  btn.disabled=true; document.getElementById('submit-lbl').textContent='Αποθήκευση...';
  const fd=new FormData(document.getElementById('water-form')); fd.set('period',currentPeriod);
  try{ const res=await fetch('/submit',{method:'POST',body:fd}); const data=await res.json();
    if(data.success){ showMsg('success',data.message||'Αποθηκεύτηκε!');
      if(ss.value&&data.record_id&&typeof DONE!=='undefined'){ (DONE[ss.value]=DONE[ss.value]||{})[currentPeriod]=data.record_id; onSystemChange(); }
      setTimeout(()=>{ window.location.href='/katagrafes'+(location.search.indexOf('embed=1')>=0?'?embed=1':''); },900);
    } else { showMsg('error',data.message||'Σφάλμα.'); updateRequired(); }
  }catch(e){ showMsg('error','Σφάλμα σύνδεσης.'); updateRequired(); }
}
function showMsg(kind,text){ const m=document.getElementById('submit-msg'); m.style.display='block'; m.className='mf-msg '+kind; m.textContent=text; }

async function askAI(){
  const btn=document.getElementById('ai-btn'), out=document.getElementById('ai-reply'); if(!btn||!out) return;
  const lines=[]; reqFields().forEach(id=>{ const el=document.getElementById(id); if(el&&el.value!=='') lines.push(id+'='+el.value); });
  const notes=document.getElementById('notes')?.value||'';
  const msg='Μετρήσεις δικτύου νερού/ΖΝΧ ('+currentPeriod+'): '+lines.join(', ')+(notes?('. Σημειώσεις: '+notes):'')+'. Δώσε σύντομες πρακτικές ενέργειες (legionella/θερμοκρασίες/ClO2).';
  btn.disabled=true; const o=btn.innerHTML; btn.innerHTML='<i class="ti ti-loader"></i> Ανάλυση...';
  try{ const res=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:msg}]})});
    const data=await res.json(); out.style.display='block'; out.textContent=data.reply||(data.error==='not_configured'?'Το AI δεν έχει ρυθμιστεί.':'Καμία απάντηση.');
  }catch(e){ out.style.display='block'; out.textContent='Σφάλμα σύνδεσης.'; }
  btn.disabled=false; btn.innerHTML=o;
}
