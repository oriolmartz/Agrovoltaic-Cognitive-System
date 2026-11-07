/* Catàleg experimental: metadades i resultats del backend; cap política de CLIPS aquí. */
const $ = id => document.getElementById(id);
const safe = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds={validacio:'Validació',verificacio:'Verificació',impasse:'Impasse'};
let experiments=[],selected=null,filter='all',search='',currentRun=null,poller=null;
async function request(path,opts={}){
 const res=await fetch(path,opts);let data=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(data.detail||`HTTP ${res.status}`);return data;
}
function sourceHTML(source){
 const items=source.items?.length?source.items.map(s=>`<li><strong>${safe(s.provider)}</strong><p>${safe(s.role)}</p><code>${safe(s.file)}</code>${s.url?` <a href="${safe(s.url)}" target="_blank" rel="noopener noreferrer">Font original ↗</a>`:''}</li>`).join('') : '<li>Consulteu les dues fitxes de dades meteorològiques, segons l’emplaçament.</li>';
 return `<div class="catalog-source"><strong>${safe(source.title)}</strong><p>${safe(source.label)}</p><ul>${items}</ul></div>`;
}
function grid(){
 let rows=experiments.filter(e=>(filter==='all'||e.kind===filter) && (`${e.id} ${e.title} ${e.verify} ${e.details}`).toLowerCase().includes(search));
 $('catalogStatus').textContent=`${rows.length} experiments · dades diferenciades de sortides simulades · protocol original del repositori`;
 $('catalogGrid').innerHTML=rows.map(e=>`<button type="button" class="catalog-card ${selected===e.id?'selected':''}" data-catalog-id="${safe(e.id)}"><span class="catalog-topline"><b>${safe(e.id)}</b><i class="catalog-kind ${safe(e.kind)}">${safe(kinds[e.kind])}</i></span><strong>${safe(e.title)}</strong><span class="catalog-card-verify">${safe(e.verify)}</span><span class="catalog-card-data">${e.source==='cp'?'◇ Dades de prova sintètiques':'◉ Meteorologia històrica · resultats simulats'}</span><span class="catalog-open">Obrir protocol →</span></button>`).join('');
 $('catalogGrid').querySelectorAll('[data-catalog-id]').forEach(b=>b.addEventListener('click',()=>openDetail(b.dataset.catalogId)));
}
function detailStatus(message='',error=false){const box=$('catalogRunState');if(box){box.textContent=message;box.classList.toggle('error',error)}}
function openDetail(id){
 const e=experiments.find(x=>x.id===id);if(!e)return;selected=id;grid();
 let cp=e.kind==='impasse',long=e.risk==='llarg';
 $('catalogDetail').hidden=false;
 $('catalogDetail').innerHTML=`<div class="catalog-detail-head"><div><span class="demo-overline">${safe(e.id)} · ${safe(kinds[e.kind])} · ${safe(e.tag)}</span><h3>${safe(e.title)}</h3><p>${safe(e.details)}</p></div><button type="button" id="catalogClose" class="catalog-dismiss">✕ Tancar</button></div>
 <div class="catalog-detail-cols"><div><h4>Què verifica?</h4><p>${safe(e.verify)}</p><h4>Protocol executat</h4><code class="catalog-command">${cp?`verificacio/casos_prova.py · ${safe(e.id)}`:safe(['python',...e.command].join(' '))}</code><p class="catalog-caution">${cp?'Prova determinista: les entrades NO provenen de sensors ni meteorologia històrica.':long?'Protocol costós: execució parcial o per trams. Una part no equival a una campanya completa.':'Executa el script original, que desa fitxers a simulador/resultats/. Les mètriques calculades són sortides del model, no mesures de producció real.'}</p></div>
 <div><h4>Procedència de les dades</h4>${sourceHTML(e.source_detail)}</div></div>
 <div class="catalog-run-controls"><button id="catalogRun" type="button" class="catalog-run-btn">▶ ${cp?'Executar cas CLIPS':'Executar protocol original'}</button><button id="catalogStop" type="button" hidden class="catalog-stop-btn">Aturar procés</button><span id="catalogRunState" aria-live="polite">Cap execució iniciada</span></div>
 <div id="catalogResults" class="catalog-results" hidden></div>`;
 $('catalogClose').onclick=()=>{$('catalogDetail').hidden=true;selected=null;grid()};
 $('catalogRun').onclick=()=>execute(e);
 $('catalogStop').onclick=stopCurrent;
 $('catalogDetail').scrollIntoView({behavior:'smooth',block:'nearest'});
}
async function execute(e){
 const btn=$('catalogRun');if(!btn)return;
 if(e.risk==='llarg'&&!confirm(`${e.id} pot durar hores. El catàleg executarà la part definida al protocol. Continuar?`))return;
 btn.disabled=true; detailStatus('Executant el motor original…');
 try {
   if(e.kind==='impasse'){
     const r=await request(`/api/defensa/impasses/${e.id}`);
     detailStatus(r.ok?'Cas executat; comprovacions superades':'Cas executat, amb discrepàncies',!r.ok);
     $('catalogResults').hidden=false;
     $('catalogResults').innerHTML=`<h4>Resultat real · ${safe(r.id)}</h4><p>${r.ok?'✓ Tots els cicles han superat les expectatives':'⚠ Hi ha discrepàncies amb el resultat esperat'}</p>` + r.cicles.map(c=>`<article class="catalog-cp-cycle"><strong>Cicle ${c.numero} · ${safe(c.sector)}</strong><p><b>Impasse:</b> ${safe(c.impasse||'Cap')} · <b>Fase final:</b> ${safe(c.fase_final)}</p><p><b>Selecció:</b> <code>${safe(JSON.stringify(c.seleccio))}</code></p><p><b>Chunks nous:</b> <code>${safe(JSON.stringify(c.chunks_nous))}</code></p><p><b>Fonts de preferència:</b> <code>${safe(JSON.stringify(c.fonts_preferencia))}</code></p><details><summary>Traça CLIPS original · ${safe(c.regles_disparades)} activacions</summary><pre>${safe(c.traca_clips)}</pre></details></article>`).join('');
   }else{
     const r=await request(`/api/catalog/${e.id}/run`,{method:'POST'});
     currentRun=r.run_id; $('catalogStop').hidden=false;displayRun(r);
     if(poller)clearInterval(poller);
     poller=setInterval(async()=>{try{const s=await request(`/api/catalog/runs/${currentRun}`);if(selected===s.experiment)displayRun(s);if(s.state!=='running'){clearInterval(poller);poller=null;currentRun=null}}catch(err){clearInterval(poller);poller=null;detailStatus(err.message,true)}},1800);
   }
 }catch(err){detailStatus(`Error: ${err.message}`,true)}finally{if(e.kind==='impasse'||!currentRun){btn.disabled=false}}
}
async function loadArtifacts(runId){
 try{
  const result=await request(`/api/catalog/runs/${runId}/artifacts`);
  const host=$('catalogResults');if(!host)return;
  const older=host.querySelector('.catalog-artifacts');if(older)older.remove();
  const block=document.createElement('div');block.className='catalog-artifacts';
  block.innerHTML='<h4>Fitxers produïts per aquesta execució</h4>'+(result.files.length?`<ul>${result.files.map(f=>`<li><a href="/api/catalog/runs/${encodeURIComponent(runId)}/download?path=${encodeURIComponent(f.path)}">${safe(f.path)}</a><small> ${(f.bytes/1024).toFixed(1)} KB</small></li>`).join('')}</ul>`:'<p>No s’han detectat fitxers nous; consulta el log i el directori de resultats.</p>');
  host.appendChild(block);
 }catch(err){console.warn('No es poden enumerar artefactes:',err)}
}
function displayRun(r){
 detailStatus(r.state==='running'?`Executant ${r.experiment} · ${r.seconds}s`:r.state==='done'?`${r.experiment} completat correctament`:`${r.experiment} finalitzat amb error (codi ${r.returncode})`,r.state==='failed');
 const box=$('catalogResults');if(!box)return;box.hidden=false;
 box.innerHTML=`<h4>Execució ${safe(r.run_id)}</h4><p><b>Ordre:</b> <code>${safe(r.command)}</code></p><p><b>Log:</b> <code>${safe(r.log_path)}</code> · Els CSV i traces es desen a <code>simulador/resultats/</code>.</p><pre class="catalog-log">${safe(r.log_tail || 'Procés en curs; encara no hi ha sortida…')}</pre>`;
 if(r.state!=='running'){$('catalogStop').hidden=true;$('catalogRun').disabled=false;loadArtifacts(r.run_id)}
}
async function stopCurrent(){if(!currentRun)return;try{let r=await request(`/api/catalog/runs/${currentRun}/stop`,{method:'POST'});displayRun(r)}catch(err){detailStatus(err.message,true)}}
export async function initCatalog(){
 $('catalogSearch').addEventListener('input',e=>{search=e.target.value.trim().toLowerCase();grid()});
 $('catalogFilters').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.catFilter;document.querySelectorAll('#catalogFilters button').forEach(x=>x.classList.toggle('active',x===b));grid()}));
 try{const payload=await request('/api/catalog');experiments=payload.experiments;grid()}
 catch(err){$('catalogStatus').textContent=`No s'ha pogut carregar el catàleg: ${err.message}`}
}
