const SYNC_MAGIC='ZDROWIE-SYNC-1';
const CLOUD_SYNC_WEBHOOK='https://hook.eu1.make.com/fn8swrncw0i0e2xo29jkw37ede7jj241';

function bytesToB64(bytes){let s='';for(const b of bytes)s+=String.fromCharCode(b);return btoa(s)}
function b64ToBytes(s){const raw=atob(s);return Uint8Array.from(raw,c=>c.charCodeAt(0))}
async function deriveKey(password,salt){
 const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);
 return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:250000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
async function encryptDatabase(password){
 const salt=crypto.getRandomValues(new Uint8Array(16));
 const iv=crypto.getRandomValues(new Uint8Array(12));
 const key=await deriveKey(password,salt);
 const plain=new TextEncoder().encode(JSON.stringify({magic:SYNC_MAGIC,exportedAt:new Date().toISOString(),data:db}));
 const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,plain);
 return JSON.stringify({format:SYNC_MAGIC,salt:bytesToB64(salt),iv:bytesToB64(iv),payload:bytesToB64(new Uint8Array(encrypted))});
}
async function decryptDatabase(text,password){
 const wrapper=JSON.parse(text);
 if(wrapper.format!==SYNC_MAGIC) throw new Error('Nieprawidłowy plik synchronizacji.');
 const key=await deriveKey(password,b64ToBytes(wrapper.salt));
 const decrypted=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64ToBytes(wrapper.iv)},key,b64ToBytes(wrapper.payload));
 const parsed=JSON.parse(new TextDecoder().decode(decrypted));
 if(parsed.magic!==SYNC_MAGIC||!parsed.data) throw new Error('Nieprawidłowe dane.');
 return parsed.data;
}
function syncPage(){
 document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
 document.getElementById('syncNavBtn')?.classList.add('active');
 title('Synchronizacja','Szyfrowany backup i przygotowanie synchronizacji między komputerami.');
 document.getElementById('content').innerHTML=`
 <div class="cards">
  <div class="card"><small>Tryb</small><div class="value" style="font-size:20px">Szyfrowany</div><small>AES-256-GCM</small></div>
  <div class="card"><small>Dane lokalne</small><div class="value" style="font-size:20px">${Object.keys(db).length}</div><small>sekcji danych</small></div>
  <div class="card"><small>Profile</small><div class="value">${db.profiles?.length||0}</div></div>
  <div class="card"><small>Chmura</small><div class="value" style="font-size:20px">Make + Drive</div><small>konfiguracja</small></div>
 </div>
 <div class="panel"><h3>Połączenie z chmurą</h3><p class="sync-note">Ten test nie wysyła leków, badań ani innych danych zdrowotnych. Wysyła tylko techniczny pakiet testowy, żeby Make rozpoznał strukturę synchronizacji.</p><div class="sync-row"><button id="cloudTest">Połącz chmurę — test</button><span id="cloudStatus" class="sync-status"></span></div></div>
 <div class="panel"><h3>Eksport zaszyfrowanej kopii</h3><p class="sync-note">Ustaw hasło. Bez niego pliku nie da się odczytać.</p><div class="sync-row"><input id="syncPassword" type="password" placeholder="Hasło do kopii"/><button id="syncExport">Eksportuj zaszyfrowany plik</button></div></div>
 <div class="panel"><h3>Import na drugim komputerze</h3><p class="sync-note">Wskaż plik <strong>.zdrowie</strong> i wpisz to samo hasło.</p><div class="sync-row"><input id="syncFile" type="file" accept=".zdrowie,application/json"/><input id="syncImportPassword" type="password" placeholder="Hasło do kopii"/><button id="syncImport">Importuj dane</button></div><div id="syncStatus" class="sync-status"></div></div>
 <div class="panel"><h3>Jak używać na kilku komputerach</h3><ol class="sync-steps"><li>Na komputerze A wyeksportuj zaszyfrowany plik.</li><li>Zapisz go w swoim folderze OneDrive, Google Drive albo Dropbox.</li><li>Na komputerze B otwórz ten sam plik i zaimportuj go do aplikacji.</li><li>Po pełnym uruchomieniu chmury aplikacja będzie mogła wykonywać ten proces automatycznie.</li></ol></div>`;
 document.getElementById('cloudTest').onclick=sendCloudLearningTest;
 document.getElementById('syncExport').onclick=syncExport;
 document.getElementById('syncImport').onclick=syncImport;
}
async function sendCloudLearningTest(){
 const status=document.getElementById('cloudStatus');
 const deviceId=localStorage.getItem('zdrowie-device-id')||('dev-'+crypto.randomUUID());
 localStorage.setItem('zdrowie-device-id',deviceId);
 const payload={action:'learn',format:SYNC_MAGIC,deviceId,updatedAt:new Date().toISOString(),encrypted:'TEST-ENCRYPTED-PAYLOAD'};
 status.textContent='Wysyłanie testu…';
 try{
  await fetch(CLOUD_SYNC_WEBHOOK,{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain;charset=UTF-8'},body:JSON.stringify(payload)});
  status.textContent='Test wysłany. Możesz wrócić do rozmowy i napisać „dalej”.';
 }catch(e){status.textContent='Nie udało się wysłać testu. Sprawdź internet i spróbuj ponownie.';}
}
async function syncExport(){
 const password=document.getElementById('syncPassword').value;
 if(password.length<8){alert('Hasło musi mieć co najmniej 8 znaków.');return;}
 try{
  const encrypted=await encryptDatabase(password);
  const blob=new Blob([encrypted],{type:'application/octet-stream'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`zdrowie-sync-${new Date().toISOString().slice(0,10)}.zdrowie`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
 }catch(e){alert('Nie udało się utworzyć kopii: '+e.message);}
}
async function syncImport(){
 const file=document.getElementById('syncFile').files[0];const password=document.getElementById('syncImportPassword').value;const status=document.getElementById('syncStatus');
 if(!file){status.textContent='Wybierz plik synchronizacji.';return;} if(!password){status.textContent='Wpisz hasło.';return;}
 try{
  const imported=await decryptDatabase(await file.text(),password);
  if(!confirm('Import zastąpi dane zapisane obecnie w tej przeglądarce. Kontynuować?'))return;
  db=imported;save();renderProfiles();status.textContent='Dane zaimportowane poprawnie.';current='dashboard';render();
 }catch(e){status.textContent='Nie udało się odszyfrować pliku. Sprawdź hasło i plik.';}
}
(function addSyncNav(){
 const nav=document.getElementById('nav');if(!nav||document.getElementById('syncNavBtn'))return;
 const b=document.createElement('button');b.id='syncNavBtn';b.className='nav-btn';b.textContent='Synchronizacja';b.onclick=syncPage;nav.appendChild(b);
})();
