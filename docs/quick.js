const QUICK_FIELDS={
 medications:{label:'Leki',keys:['name','dose'],fields:[{k:'name',label:'Nazwa leku'},{k:'dose',label:'Dawka'},{k:'times',label:'Ile razy dziennie',type:'number'},{k:'stock',label:'Stan zapasu',type:'number'},{k:'threshold',label:'Próg alarmowy',type:'number'}]},
 appointments:{label:'Wizyty',keys:['title','doctor','location','date'],fields:[{k:'date',label:'Termin',type:'datetime-local'},{k:'title',label:'Nazwa wizyty'},{k:'doctor',label:'Lekarz'},{k:'location',label:'Miejsce'}]},
 measurements:{label:'Pomiary',keys:['date','bp','pulse','glucose','weight','spo2'],fields:[{k:'date',label:'Data i godzina',type:'datetime-local'},{k:'bp',label:'Ciśnienie np. 120/80'},{k:'pulse',label:'Puls',type:'number'},{k:'glucose',label:'Glukoza'},{k:'weight',label:'Masa kg'},{k:'spo2',label:'SpO₂ %'}]},
 doctors:{label:'Lekarze',keys:['name','specialty','facility','phone','email']},
 tests:{label:'Badania',keys:['title','result','range','date']},
 prescriptions:{label:'Recepty',keys:['name','code','valid']},
 documents:{label:'Dokumentacja',keys:['title','category','note','date']}
};

function installQuickTools(){
 const actions=document.querySelector('.header-actions'); if(!actions||document.getElementById('globalSearchBtn'))return;
 const search=document.createElement('button'); search.id='globalSearchBtn'; search.className='secondary'; search.textContent='Szukaj'; search.onclick=openGlobalSearch;
 const add=document.createElement('button'); add.id='quickAddBtn'; add.textContent='+ Szybko dodaj'; add.onclick=openQuickAdd;
 actions.insertBefore(search,actions.firstChild); actions.insertBefore(add,document.getElementById('profileSelect'));
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openGlobalSearch();}});
}
function modalShell(titleText,body){const m=document.createElement('div');m.className='modal quick-modal';m.innerHTML=`<div class="modal-card quick-card"><div class="quick-head"><h2>${titleText}</h2><button class="secondary" data-close>Zamknij</button></div>${body}</div>`;document.body.appendChild(m);m.querySelector('[data-close]').onclick=()=>m.remove();m.addEventListener('click',e=>{if(e.target===m)m.remove();});return m;}
function openGlobalSearch(){
 const m=modalShell('Wyszukiwanie',`<input id="globalSearchInput" class="quick-search" placeholder="Wpisz lek, lekarza, badanie, wizytę…" autocomplete="off"><div class="quick-hint">Ctrl+K otwiera wyszukiwarkę z dowolnego miejsca.</div><div id="globalSearchResults" class="search-results"><div class="empty">Zacznij pisać, aby przeszukać aktywny profil.</div></div>`);
 const input=m.querySelector('#globalSearchInput');const out=m.querySelector('#globalSearchResults');input.focus();input.oninput=()=>renderSearchResults(input.value,out,m);
}
function searchRecords(q){q=q.trim().toLowerCase();if(!q)return[];const hits=[];for(const [key,cfg] of Object.entries(QUICK_FIELDS)){const rows=(db[key]||[]).filter(x=>x.profileId===pid());for(const row of rows){const text=(cfg.keys||Object.keys(row)).map(k=>row[k]||'').join(' ').toLowerCase();if(text.includes(q)){const primary=row.name||row.title||row.doctor||row.category||cfg.label;const secondary=(cfg.keys||[]).map(k=>row[k]).filter(Boolean).slice(0,3).join(' • ');hits.push({key,label:cfg.label,primary,secondary});}}}return hits.slice(0,40);}
function renderSearchResults(q,out,m){const hits=searchRecords(q);if(!q.trim()){out.innerHTML='<div class="empty">Zacznij pisać, aby przeszukać aktywny profil.</div>';return;}if(!hits.length){out.innerHTML='<div class="empty">Brak wyników.</div>';return;}out.innerHTML=hits.map((h,i)=>`<button class="search-hit" data-i="${i}"><span class="badge">${esc(h.label)}</span><strong>${esc(h.primary)}</strong><small>${esc(h.secondary)}</small></button>`).join('');out.querySelectorAll('.search-hit').forEach(b=>b.onclick=()=>{const h=hits[Number(b.dataset.i)];current=h.key;render();m.remove();});}
function openQuickAdd(){
 const m=modalShell('Szybko dodaj',`<div class="quick-actions"><button data-add="medications">Lek</button><button data-add="appointments">Wizytę</button><button data-add="measurements">Pomiar</button></div><div class="quick-hint">Rekord zostanie zapisany w aktywnym profilu: <strong>${esc(activeName())}</strong>.</div>`);
 m.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>{const key=b.dataset.add;const cfg=QUICK_FIELDS[key];m.remove();formModal(key,cfg.label,cfg.fields);});
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(installQuickTools,0));else setTimeout(installQuickTools,0);
