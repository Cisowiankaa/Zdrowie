function medStatusValue(m){return m.purchaseStatus||((Number(m.stock||0)>0)?'Wykupiony':'Do wykupienia');}
function medDailyUse(m){const v=Number(m.times||0);return v>0?v:0;}
function medEndDate(m){const stock=Number(m.stock||0),daily=medDailyUse(m);if(stock<=0||daily<=0)return '';const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+Math.floor(stock/daily));return d.toISOString().slice(0,10);}
function medications(){
 title('Leki',`Leki, zapasy i wykupienie — ${activeName()}`);
 const all=byProfile('medications');
 const filter=window.__medFilter||'all';
 const rows=all.filter(m=>filter==='all'||(filter==='owned'?medStatusValue(m)==='Wykupiony':medStatusValue(m)==='Do wykupienia'));
 const toBuy=all.filter(m=>medStatusValue(m)==='Do wykupienia'||Number(m.stock||0)<=Number(m.threshold||5)).length;
 const owned=all.filter(m=>medStatusValue(m)==='Wykupiony').length;
 document.getElementById('content').innerHTML=`
 <div class="cards meds-summary">
  <div class="card"><small>Wszystkie leki</small><div class="value">${all.length}</div></div>
  <div class="card"><small>Wykupione</small><div class="value">${owned}</div></div>
  <div class="card"><small>Do wykupienia / niski zapas</small><div class="value ${toBuy?'danger':''}">${toBuy}</div></div>
  <div class="card"><small>Aktywny filtr</small><div class="value" style="font-size:18px">${filter==='all'?'Wszystkie':filter==='owned'?'Mam':'Do kupienia'}</div></div>
 </div>
 <div class="panel">
  <div class="toolbar meds-toolbar">
   <button id="medAdd">+ Dodaj lek</button>
   <button class="secondary med-filter ${filter==='all'?'active-filter':''}" data-filter="all">Wszystkie</button>
   <button class="secondary med-filter ${filter==='owned'?'active-filter':''}" data-filter="owned">Mam</button>
   <button class="secondary med-filter ${filter==='buy'?'active-filter':''}" data-filter="buy">Do wykupienia</button>
   <button class="secondary" id="fromRx">+ Z recepty</button>
  </div>
  ${rows.length?`<div class="table-wrap"><table><tr><th>Lek</th><th>Dawka</th><th>x/dzień</th><th>Stan</th><th>Opak.</th><th>Status</th><th>Ostatni zakup</th><th>Szac. koniec</th><th></th></tr>${rows.map(m=>`<tr><td><strong>${esc(m.name||'')}</strong></td><td>${esc(m.dose||'')}</td><td>${esc(m.times||'')}</td><td>${esc(m.stock||'0')}</td><td>${esc(m.packages||'')}</td><td><button class="status-toggle ${medStatusValue(m)==='Do wykupienia'?'need-buy':''}" data-id="${m.id}">${medStatusValue(m)}</button></td><td>${esc(m.lastPurchase||'')}</td><td>${esc(medEndDate(m)||'—')}</td><td><button class="secondary med-del" data-id="${m.id}">Usuń</button></td></tr>`).join('')}</table></div>`:'<div class="empty">Brak leków dla wybranego filtra.</div>'}
 </div>`;
 document.getElementById('medAdd').onclick=()=>medicationForm();
 document.querySelectorAll('.med-filter').forEach(b=>b.onclick=()=>{window.__medFilter=b.dataset.filter;medications();});
 document.querySelectorAll('.status-toggle').forEach(b=>b.onclick=()=>{const m=db.medications.find(x=>x.id===b.dataset.id);if(!m)return;m.purchaseStatus=medStatusValue(m)==='Wykupiony'?'Do wykupienia':'Wykupiony';if(m.purchaseStatus==='Wykupiony'&&!m.lastPurchase)m.lastPurchase=new Date().toISOString().slice(0,10);save();medications();});
 document.querySelectorAll('.med-del').forEach(b=>b.onclick=()=>{db.medications=db.medications.filter(x=>x.id!==b.dataset.id);save();medications();});
 document.getElementById('fromRx').onclick=prescriptionToMedication;
}
function medicationForm(seed={}){
 const m=document.createElement('div');m.className='modal';m.innerHTML=`<div class="modal-card"><h2>Dodaj lek</h2><div class="form-grid">
 <label>Nazwa leku<br><input data-f="name" value="${esc(seed.name||'')}"></label>
 <label>Dawka<br><input data-f="dose" value="${esc(seed.dose||'')}"></label>
 <label>Ile razy dziennie<br><input data-f="times" type="number" min="0" step="0.5" value="${esc(seed.times||'')}"></label>
 <label>Stan zapasu (szt.)<br><input data-f="stock" type="number" min="0" value="${esc(seed.stock||'')}"></label>
 <label>Liczba opakowań<br><input data-f="packages" type="number" min="0" value="${esc(seed.packages||'')}"></label>
 <label>Próg alarmowy<br><input data-f="threshold" type="number" min="0" value="${esc(seed.threshold||'5')}"></label>
 <label>Ostatni zakup<br><input data-f="lastPurchase" type="date" value="${esc(seed.lastPurchase||'')}"></label>
 <label>Status<br><select data-f="purchaseStatus"><option ${seed.purchaseStatus==='Wykupiony'?'selected':''}>Wykupiony</option><option ${seed.purchaseStatus==='Do wykupienia'?'selected':''}>Do wykupienia</option></select></label>
 </div><div class="modal-actions"><button class="secondary" id="medCancel">Anuluj</button><button id="medSave">Zapisz</button></div></div>`;document.body.appendChild(m);
 m.querySelector('#medCancel').onclick=()=>m.remove();m.querySelector('#medSave').onclick=()=>{const r={id:'m'+Date.now(),profileId:pid()};m.querySelectorAll('[data-f]').forEach(i=>r[i.dataset.f]=i.value);db.medications.push(r);save();m.remove();medications();};
}
function prescriptionToMedication(){
 const rx=byProfile('prescriptions');if(!rx.length){alert('Brak recept dla aktywnego profilu.');return;}
 const labels=rx.map((r,i)=>`${i+1}. ${r.name||'Recepta'}${r.valid?' — ważna do '+r.valid:''}`).join('\n');
 const n=Number(prompt(`Wybierz numer recepty:\n${labels}`));if(!n||!rx[n-1])return;const r=rx[n-1];medicationForm({name:r.name||'',packages:r.qty||'',purchaseStatus:'Do wykupienia'});
}
