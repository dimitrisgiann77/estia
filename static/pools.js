// Εστία — Πισίνες (redesign v12.88)
let currentPeriod = 'morning';
const LIMITS = {
  free_chlorine:[0.4,1.5], combined_chlorine:[null,0.5], ph:[7.2,7.8], temp:[null,32.0],
  turbidity:[null,1.0], cyanuric_acid:[null,75.0], total_alkalinity:[80.0,120.0], orp:[650.0,null],
};
const BASE_FIELDS = ['free_chlorine','combined_chlorine','ph','temp','turbidity'];
const MORNING_FIELDS = ['cyanuric_acid','total_alkalinity','orp'];
function reqFields(){ return currentPeriod==='morning' ? BASE_FIELDS.concat(MORNING_FIELDS) : BASE_FIELDS.slice(); }

document.addEventListener('DOMContentLoaded', () => {
  if (typeof HOTELS !== 'undefined' && HOTELS.length) { buildHotels(); applyPreset(); }
});

function buildHotels(){
  const hs=document.getElementById('hotel-select'); hs.innerHTML='';
  HOTELS.forEach((h,i)=>{ const o=document.createElement('option'); o.value=i; o.textContent=h.name; hs.appendChild(o); });
  onHotelChange();
}
function onHotelChange(){
  const hi=+document.getElementById('hotel-select').value;
  const ps=document.getElementById('pool-select'); ps.innerHTML='';
  (HOTELS[hi]?.pools||[]).forEach(p=>{ const o=document.createElement('option'); o.value=p.id;
    o.textContent=p.location?`${p.name} — ${p.location}`:p.name; ps.appendChild(o); });
  onPoolChange();
}
function onPoolChange(){
  const sel=document.getElementById('pool-select');
  const opt=sel.options[sel.selectedIndex];
  const pl=document.getElementById('mf-place'); if(pl&&opt) pl.textContent=opt.textContent;
  const box=document.getElementById('pool-status'); if(!box) return;
  const pid=sel.value;
  const periods=(typeof DONE!=='undefined'&&DONE[pid])?DONE[pid]:[];
  box.innerHTML='';
  ['morning','afternoon'].forEach(per=>{ if(periods.includes(per)){
    const s=document.createElement('span'); s.className='mf-done';
    s.innerHTML='<i class="ti ti-check"></i> '+(per==='morning'?'Πρωί καταχωρήθηκε':'Απόγευμα καταχωρήθηκε'); box.appendChild(s);
  }});
}

function setPeriod(period){
  currentPeriod=period;
  document.getElementById('period-input').value=period;
  document.getElementById('tab-morning').classList.toggle('active',period==='morning');
  document.getElementById('tab-afternoon').classList.toggle('active',period==='afternoon');
  const extra=document.getElementById('morning-extra'); if(extra) extra.style.display=period==='morning'?'block':'none';
  validate();
}

function fieldStatus(id){
  const el=document.getElementById(id), st=document.getElementById(id+'_st');
  if(!el) return;
  el.classList.remove('ok','bad'); if(st){st.className='mf-hint'; st.innerHTML='';}
  if(el.value==='') return;
  const val=parseFloat(el.value); if(isNaN(val)) return;
  const [mn,mx]=LIMITS[id]||[null,null];
  const ok=(mn!=null?val>=mn:true)&&(mx!=null?val<=mx:true);
  el.classList.add(ok?'ok':'bad');
  if(st){ st.className='mf-hint '+(ok?'ok':'bad');
    st.innerHTML = ok ? '<i class="ti ti-check"></i> Εντός ορίων'
      : '<i class="ti ti-alert-triangle"></i> '+(val<(mn??-Infinity)?'Χαμηλό':'Υψηλό'); }
}

function validate(){
  reqFields().forEach(fieldStatus);
  renderNextSteps();
  updateRequired();
}

function updateRequired(){
  const fields=reqFields();
  let filled=0;
  fields.forEach(id=>{ const el=document.getElementById(id); if(el&&el.value!=='') filled++; });
  const n=fields.length;
  const cnt=document.getElementById('mf-count');
  const btn=document.getElementById('submit-btn'), lbl=document.getElementById('submit-lbl');
  const poolOk=!!document.getElementById('pool-select')?.value;
  const all = poolOk && filled===n;
  if(btn) btn.disabled=!all;
  if(lbl) lbl.textContent = all ? 'Αποθήκευση καταγραφής' : 'Συμπλήρωσε όλα τα πεδία';
  if(cnt) cnt.textContent = all ? 'Όλα τα πεδία συμπληρωμένα' : (filled+' από '+n+' πεδία συμπληρωμένα');
}

function renderNextSteps(){
  const card=document.getElementById('next-steps'); if(!card) return;
  const body=document.getElementById('next-steps-body'); const tips=[]; let anyVal=false;
  reqFields().forEach(id=>{
    const el=document.getElementById(id); if(!el||el.value==='') return;
    const val=parseFloat(el.value); if(isNaN(val)) return; anyVal=true;
    const [mn,mx]=LIMITS[id]||[null,null]; const rule=(typeof ACTIONS!=='undefined')?ACTIONS[id]:null; if(!rule) return;
    let txt=null; if(mn!=null&&val<mn) txt=rule.low; else if(mx!=null&&val>mx) txt=rule.high;
    if(txt){ const lab=(typeof PARAM_LABELS!=='undefined'&&PARAM_LABELS[id])?PARAM_LABELS[id]:id;
      const urgent=(id==='free_chlorine'&&val<0.2)||(id==='combined_chlorine'&&val>1.0)||(id==='turbidity'&&val>2.0);
      tips.push({lab,txt,urgent}); }
  });
  card.classList.remove('ok');
  if(tips.length){
    document.querySelector('.mf-actions-h').innerHTML='<i class="ti ti-bulb"></i> Προτεινόμενες ενέργειες';
    body.innerHTML=tips.map(t=>'<div class="mf-act'+(t.urgent?' urgent':'')+'"><i class="ti ti-'+(t.urgent?'alert-triangle':'point-filled')+'"></i><span><b>'+t.lab+':</b> '+t.txt+'</span></div>').join('');
    card.style.display='block';
  } else if(anyVal){
    card.classList.add('ok');
    document.querySelector('.mf-actions-h').innerHTML='<i class="ti ti-circle-check"></i> Όλες οι τιμές εντός ορίων';
    body.innerHTML=''; card.style.display='block';
  } else { card.style.display='none'; }
}

function applyPreset(){
  let per='morning';
  try{ if(typeof PRESET!=='undefined'&&PRESET&&PRESET.id){
    for(let hi=0;hi<HOTELS.length;hi++){ if((HOTELS[hi].pools||[]).some(p=>String(p.id)===String(PRESET.id))){
      const hs=document.getElementById('hotel-select'); hs.value=hi; onHotelChange();
      document.getElementById('pool-select').value=PRESET.id; onPoolChange(); break; } }
    if(PRESET.period) per=PRESET.period;
  } }catch(e){}
  setPeriod(per);
  try{ if(typeof PRESET!=='undefined'&&PRESET&&PRESET.values){
    Object.keys(PRESET.values).forEach(k=>{ const el=document.querySelector('[name="'+k+'"]'); if(!el) return;
      if(el.type==='checkbox') el.checked=!!PRESET.values[k]; else el.value=PRESET.values[k]; });
    validate();
  } }catch(e){}
}

async function submitForm(){
  const btn=document.getElementById('submit-btn'), msg=document.getElementById('submit-msg');
  const sel=document.getElementById('pool-select');
  if(!sel||!sel.value){ showMsg('error','Επίλεξε πισίνα.'); return; }
  const miss=reqFields().filter(id=>{ const el=document.getElementById(id); return !el||el.value===''; });
  if(miss.length){ showMsg('error','Συμπλήρωσε όλα τα υποχρεωτικά πεδία.'); return; }
  btn.disabled=true; document.getElementById('submit-lbl').textContent='Αποθήκευση...';
  const fd=new FormData(document.getElementById('pool-form')); fd.set('period',currentPeriod);
  try{
    const res=await fetch('/submit-pool',{method:'POST',body:fd}); const data=await res.json();
    if(data.success){
      showMsg('success',data.message||'Αποθηκεύτηκε!');
      const pid=sel.value; if(typeof DONE!=='undefined'){ DONE[pid]=DONE[pid]||[]; if(!DONE[pid].includes(currentPeriod)) DONE[pid].push(currentPeriod); }
      onPoolChange();
      setTimeout(()=>{ window.location.href='/katagrafes'+(location.search.indexOf('embed=1')>=0?'?embed=1':''); },900);
    } else { showMsg('error',data.message||'Σφάλμα.'); updateRequired(); }
  }catch(e){ showMsg('error','Σφάλμα σύνδεσης.'); updateRequired(); }
}
function showMsg(kind,text){ const m=document.getElementById('submit-msg'); m.style.display='block'; m.className='mf-msg '+kind; m.textContent=text; }

async function askAI(){
  const btn=document.getElementById('ai-btn'), out=document.getElementById('ai-reply'); if(!btn||!out) return;
  const pid=document.getElementById('pool-select')?.value; const lines=[];
  reqFields().forEach(id=>{ const el=document.getElementById(id); if(el&&el.value!=='') lines.push(id+'='+el.value); });
  const notes=document.getElementById('notes')?.value||'';
  const msg='Μετρήσεις πισίνας ('+currentPeriod+'): '+lines.join(', ')+(notes?('. Σημειώσεις: '+notes):'')+'. Δώσε σύντομες, πρακτικές ενέργειες.';
  btn.disabled=true; const o=btn.innerHTML; btn.innerHTML='<i class="ti ti-loader"></i> Ανάλυση...';
  try{ const res=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pool_id:pid,messages:[{role:'user',content:msg}]})});
    const data=await res.json(); out.style.display='block';
    out.textContent=data.reply||(data.error==='not_configured'?'Το AI δεν έχει ρυθμιστεί.':'Καμία απάντηση.');
  }catch(e){ out.style.display='block'; out.textContent='Σφάλμα σύνδεσης.'; }
  btn.disabled=false; btn.innerHTML=o;
}
