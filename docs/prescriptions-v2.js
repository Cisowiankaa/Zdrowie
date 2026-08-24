function rxStatusValue(r){
  if(r.fulfillmentStatus)return r.fulfillmentStatus;
  const bought=Number(r.fulfilledQty||0),total=Number(r.qty||0);
  if(total>0&&bought>=total)return 'Zrealizowana';
  if(bought>0)return 'Częściowo zrealizowana';
  return 'Do realizacji';
}
function rxRemaining(r){return Math.max(0,Number(r.qty||0)-Number(r.fulfilledQty||0));}
function rxStatusClass(s){return s==='Zrealizowana'?'rx-done':s==='Częściowo zrealizowana'?'rx-partial':'rx-open';}
function prescriptions(){
  title('Recepty',`Realizacja recept i wykupione opakowania — ${activeName()}`);
  const all=byProfile('prescriptions');
  const filter=window.__rxFilter||'all';
  const rows=all.filter(r=>filter==='all'||(filter==='open'?rxStatusValue(r)!=='Zrealizowana':rxStatusValue(r)==='Zrealizowana'));
  const open=all.filter(r=>rxStatusValue(r)==='Do realizacji').length;
  const partial=all.filter(r=>rxStatusValue(r)==='Częściowo zrealizowana').length;
  const done=all.filter(r=>rxStatusValue(r)==='Zrealizowana').length;
  document.getElementById('content').innerHTML=`
  <div class="cards rx-summary">
    <div class="card"><small>Wszystkie recepty</small><div class="value">${all.length}</div></div>
    <div class="card"><small>Do realizacji</small><div class="value ${open?'danger':''}">${open}</div></div>
    <div class="card"><small>Częściowo</small><div class="value">${partial}</div></div>
    <div class="card"><small>Zrealizowane</small><div class="value">${done}</div></div>
  </div>
  <div class="panel">
    <div class="toolbar rx-toolbar">
      <button id="rxAdd">+ Dodaj receptę</button>
      <button class="secondary rx-filter ${filter==='all'?'active-filter':''}" data-filter="all">Wszystkie</button>
      <button class="secondary rx-filter ${filter==='open'?'active-filter':''}" data-filter="open">Do realizacji</button>
      <button class="secondary rx-filter ${filter==='done'?'active-filter':''}" data-filter="done">Zrealizowane</button>
    </div>
    ${rows.length?`<div class="table-wrap"><table><tr><th>Lek</th><th>Kod</th><th>Ważna do</th><th>Przepisano</th><th>Wykupiono</th><th>Pozostało</th><th>Status</th><th>Akcje</th></tr>${rows.map(r=>{const s=rxStatusValue(r);return `<tr><td><strong>${esc(r.name||'')}</strong></td><td>${esc(r.code||'')}</td><td>${esc(r.valid||'')}</td><td>${esc(r.qty||'')}</td><td>${esc(r.fulfilledQty||'0')}</td><td>${rxRemaining(r)}</td><td><span class="badge ${rxStatusClass(s)}">${s}</span></td><td class="rx-actions">${s!=='Zrealizowana'?`<button class="rx-fulfill" data-id="${r.id}">Realizuj</button>`:''}<button class="secondary rx-med" data-id="${r.id}">Do leków</button><button class="secondary rx-del" data-id="${r.id}">Usuń</button></td></tr>`}).join('')}</table></div>`:'<div class="empty">Brak recept dla wybranego filtra.</div>'}
  </div>`;
  document.getElementById('rxAdd').onclick=()=>prescriptionForm();
  document.querySelectorAll('.rx-filter').forEach(b=>b.onclick=()=>{window.__rxFilter=b.dataset.filter;prescriptions();});
  document.querySelectorAll('.rx-fulfill').forEach(b=>b.onclick=()=>fulfillPrescription(b.dataset.id));
  document.querySelectorAll('.rx-med').forEach(b=>b.onclick=()=>sendPrescriptionToMedication(b.dataset.id));
  document.querySelectorAll('.rx-del').forEach(b=>b.onclick=()=>{db.prescriptions=db.prescriptions.filter(x=>x.id!==b.dataset.id);save();prescriptions();});
}
function prescriptionForm(){
  const m=document.createElement('div');m.className='modal';m.innerHTML=`<div class="modal-card"><h2>Dodaj receptę</h2><div class="form-grid">
    <label>Lek<br><input data-f="name"></label>
    <label>Kod recepty<br><input data-f="code"></label>
    <label>Ważna do<br><input data-f="valid" type="date"></label>
    <label>Liczba opakowań<br><input data-f="qty" type="number" min="0" step="1"></label>
  </div><div class="modal-actions"><button class="secondary" id="rxCancel">Anuluj</button><button id="rxSave">Zapisz</button></div></div>`;document.body.appendChild(m);
  m.querySelector('#rxCancel').onclick=()=>m.remove();
  m.querySelector('#rxSave').onclick=()=>{const r={id:'r'+Date.now(),profileId:pid(),fulfilledQty:0,fulfillmentStatus:'Do realizacji'};m.querySelectorAll('[data-f]').forEach(i=>r[i.dataset.f]=i.value);db.prescriptions.push(r);save();m.remove();prescriptions();};
}
function fulfillPrescription(id){
  const r=db.prescriptions.find(x=>x.id===id);if(!r)return;
  const remaining=rxRemaining(r);if(remaining<=0){r.fulfillmentStatus='Zrealizowana';save();prescriptions();return;}
  const raw=prompt(`Ile opakowań wykupiono teraz? Pozostało: ${remaining}`,String(remaining));if(raw===null)return;
  const added=Math.max(0,Math.min(remaining,Number(raw)||0));if(!added)return;
  r.fulfilledQty=Number(r.fulfilledQty||0)+added;
  r.lastFulfilledAt=new Date().toISOString().slice(0,10);
  r.fulfillmentStatus=rxRemaining(r)===0?'Zrealizowana':'Częściowo zrealizowana';
  updateMedicationFromPrescription(r,added);
  save();prescriptions();
}
function updateMedicationFromPrescription(r,added){
  const name=(r.name||'').trim();if(!name)return;
  let med=db.medications.find(m=>m.profileId===pid()&&(m.name||'').trim().toLowerCase()===name.toLowerCase());
  if(!med){med={id:'m'+Date.now(),profileId:pid(),name,packages:0,stock:'',threshold:5,purchaseStatus:'Wykupiony'};db.medications.push(med);}
  med.packages=Number(med.packages||0)+Number(added||0);
  med.purchaseStatus='Wykupiony';
  med.lastPurchase=new Date().toISOString().slice(0,10);
}
function sendPrescriptionToMedication(id){
  const r=db.prescriptions.find(x=>x.id===id);if(!r)return;
  if(typeof medicationForm==='function')medicationForm({name:r.name||'',packages:rxRemaining(r)||r.qty||'',purchaseStatus:rxStatusValue(r)==='Zrealizowana'?'Wykupiony':'Do wykupienia'});
  else{current='medications';render();}
}
const __baseBuildAlertsRx=buildAlerts;
buildAlerts=function(){
  const base=__baseBuildAlertsRx().filter(a=>a.type!=='Recepta');
  byProfile('prescriptions').forEach(r=>{
    const status=rxStatusValue(r);if(status==='Zrealizowana')return;
    const d=daysUntil(r.valid);
    if(d>=0&&d<=7)base.push({prio:d<=2?'Wysoki':'Średni',type:'Recepta',text:`${r.name||'Recepta'} — ${status.toLowerCase()}, pozostało ${rxRemaining(r)}, ważna do ${r.valid}`});
  });
  return base;
};
