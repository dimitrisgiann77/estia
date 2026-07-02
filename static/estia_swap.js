/* ESTIA — fragment swap (P-058, v12.382)
 * Αντικαθιστά το full-page reload μετά από καταχώρηση: fetch της ΙΔΙΑΣ σελίδας →
 * αντικατάσταση ΜΟΝΟ του server-rendered container (μία πηγή αλήθειας, καμία διπλή λογική).
 * Κρατά scroll θέση. Fallback σε location.reload() αν κάτι αποτύχει.
 * Απαιτεί: container με id, και (προαιρετικά) global initFn που ξανα-δένει listeners μετά το swap.
 */
function estiaSwap(containerId, initFnName){
  var wrap = document.getElementById(containerId);
  if(!wrap){ location.reload(); return; }
  // αποθήκευση scroll (οριζόντιο/κάθετο) των εσωτερικών scrollers + παραθύρου
  var scrollers = wrap.querySelectorAll('.gridwrap');
  var saved = [];
  for(var i=0;i<scrollers.length;i++){ saved.push([scrollers[i].scrollLeft, scrollers[i].scrollTop]); }
  var winY = window.scrollY, winX = window.scrollX;
  fetch(location.href, {credentials:'same-origin', headers:{'X-Requested-With':'estia-swap'}})
    .then(function(r){ if(!r.ok) throw new Error('http '+r.status); return r.text(); })
    .then(function(html){
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var nw = doc.getElementById(containerId);
      if(!nw){ location.reload(); return; }
      wrap.innerHTML = nw.innerHTML;
      var fn = initFnName && window[initFnName];
      if(typeof fn === 'function'){ try{ fn(); }catch(e){} }
      // επαναφορά scroll
      var s2 = wrap.querySelectorAll('.gridwrap');
      for(var j=0;j<s2.length;j++){ if(saved[j]){ s2[j].scrollLeft = saved[j][0]; s2[j].scrollTop = saved[j][1]; } }
      window.scrollTo(winX, winY);
    })
    .catch(function(){ location.reload(); });
}
/* Βολικός wrapper για το Πρόγραμμα (schedule_board) */
function refreshBoard(){ estiaSwap('boardwrap', 'initBoard'); }
