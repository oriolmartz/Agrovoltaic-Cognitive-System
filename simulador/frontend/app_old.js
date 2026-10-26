const $ = (id) => document.getElementById(id);
let bootstrapData = null;
let currentRun = null;

async function api(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}

function fmt(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("ca-ES", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }

async function init() {
  try {
    bootstrapData = await api('/api/bootstrap');
    const s = $('scenario');
    bootstrapData.scenarios.forEach(x => s.add(new Option(x.label, x.id)));
    const c = $('controller');
    bootstrapData.controllers.forEach(x => c.add(new Option(x.label, x.id)));
    renderOntology(bootstrapData.ontology);
    $('systemStatus').classList.add('ok');
    $('systemStatus').innerHTML = '<span class="dot"></span> Ontologies validades';
    await loadDays();
  } catch (e) { showError(e.message); }
}

async function loadDays() {
  try {
    const d = await api(`/api/days?scenario=${encodeURIComponent($('scenario').value)}`);
    const el = $('day'); el.innerHTML = '';
    d.days.forEach(day => el.add(new Option(day, day)));
    if (d.days.length) el.value = d.days[Math.floor(d.days.length / 2)];
  } catch (e) { showError(e.message); }
}

function renderOntology(o) {
  $('ontologyBadge').textContent = o.valid ? 'VALIDAT' : 'ERROR';
  $('factsCount').textContent = `${o.facts.total} fets`;
  $('ontologyStats').innerHTML = [
    `${o.validation.classes_operacionals} classes`,
    `${o.validation.propietats_objecte} propietats objecte`,
    `${o.validation.propietats_dades} propietats dades`,
    `${o.validation.relacions_validades} relacions validades`,
    `${o.validation.literals_validats} literals validats`,
  ].map(x => `<span>${x}</span>`).join('');
}

function renderKpis(k) {
  const items = [
    ['Energia', fmt(k.energy_kwh, 1), 'kWh', `${fmt(k.efficiency_pct,1)}% del màxim`],
    ['Seguretat', String(k.safety_violations), 'violacions', `${k.wind_exposure_h} exposicions`],
    ['Impasses', String(k.impasses), '', `${k.chunk_decisions} decisions via chunk`],
    ['Temps decisió', fmt(k.avg_ms,2), 'ms', `${fmt(k.rules_per_cycle,1)} regles/cicle`],
    ['Invariants', String(k.invariants_ko), 'KO', k.invariants_ko === 0 ? 'tots satisfets' : 'revisar execució'],
  ];
  $('kpiGrid').innerHTML = items.map(([l,v,u,s]) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}<span class="unit">${u}</span></div><div class="sub">${s}</div></div>`).join('');
}

function renderSectors(sectors) {
  $('sectorGrid').innerHTML = sectors.map(s => {
    const risk = s.risks || s.impasse;
    return `<article class="sector-card">
      <div class="sector-top"><div><div class="sector-name">${esc(s.sector)}</div><div class="crop">${esc(s.crop)}</div></div><span class="action-chip">${esc(s.action)}</span></div>
      <div class="metrics-mini">
        <div class="metric-mini"><span>ANGLE</span><b>${fmt(s.angle,1)}°</b></div>
        <div class="metric-mini"><span>ÒPTIM</span><b>${fmt(s.optimal_angle,1)}°</b></div>
        <div class="metric-mini"><span>AIGUA</span><b>${fmt(s.water_pct,1)}%</b></div>
        <div class="metric-mini"><span>POTÈNCIA</span><b>${fmt(s.power_kw,2)} kW</b></div>
        <div class="metric-mini"><span>T. CULTIU</span><b>${fmt(s.crop_temp,1)} °C</b></div>
        <div class="metric-mini"><span>RADIACIÓ</span><b>${fmt(s.radiation,0)} W/m²</b></div>
      </div>
      <div class="risk-line ${risk ? 'alert':''}">${risk ? `⚠ ${esc(risk)}` : 'Sense riscos actius · sense impasse'}</div>
    </article>`;
  }).join('');
}

function aggregateByHour(records, key, sector = null) {
  const m = new Map();
  records.filter(r => !sector || r.sector === sector).forEach(r => {
    const h = Number(r.hora), v = Number(r[key] ?? 0);
    if (!m.has(h)) m.set(h, []); m.get(h).push(v);
  });
  return [...m].sort((a,b)=>a[0]-b[0]).map(([h,vs]) => [h, vs.reduce((a,b)=>a+b,0) / vs.length]);
}

function svgChart(container, series, opts = {}) {
  const W=620,H=220,p={l:42,r:18,t:20,b:30};
  const all=series.flatMap(s=>s.data.map(x=>x[1])).filter(Number.isFinite);
  const xs=series.flatMap(s=>s.data.map(x=>x[0]));
  if(!all.length){container.innerHTML='<div class="empty-state">Sense dades</div>';return;}
  let ymin=opts.ymin ?? Math.min(...all), ymax=opts.ymax ?? Math.max(...all);
  if(ymin===ymax){ymin-=1;ymax+=1;} const xmin=Math.min(...xs),xmax=Math.max(...xs);
  const X=x=>p.l+(x-xmin)/(xmax-xmin||1)*(W-p.l-p.r); const Y=y=>H-p.b-(y-ymin)/(ymax-ymin)*(H-p.t-p.b);
  let grid=''; for(let i=0;i<5;i++){const v=ymin+(ymax-ymin)*i/4,yy=Y(v);grid+=`<line class="grid-line" x1="${p.l}" y1="${yy}" x2="${W-p.r}" y2="${yy}"/><text class="axis-label" x="4" y="${yy+3}">${fmt(v,opts.digits??1)}</text>`;}
  const xlabels=[xmin,Math.round((xmin+xmax)/2),xmax].map(x=>`<text class="axis-label" x="${X(x)}" y="${H-8}" text-anchor="middle">${x}:00</text>`).join('');
  const lines=series.map(s=>{const pts=s.data.map(([x,y])=>`${X(x)},${Y(y)}`).join(' ');return `<polyline class="${s.cls}" points="${pts}"/>`;}).join('');
  const legend=series.map(s=>`<span><i class="legend-dot" style="background:${s.color}"></i>${s.name}</span>`).join('');
  container.innerHTML=`<div class="chart-legend">${legend}</div><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${xlabels}${lines}</svg>`;
}

function renderCharts(run) {
  $('chartsSection').hidden=false;
  const r=run.records;
  svgChart($('energyChart'),[
    {name:'Producció',data:aggregateByHour(r,'P_kw'),cls:'line-energy',color:'#267a55'},
    {name:'Òptim',data:aggregateByHour(r,'P_opt_kw'),cls:'line-opt',color:'#9eada5'}
  ],{ymin:0,digits:1});
  const sectors=[...new Set(r.map(x=>x.sector))];
  const colors=['#267a55','#386e91','#b47722'];
  const series=sectors.map((s,i)=>({name:s,data:aggregateByHour(r,'angle_real',s),cls:`line-sector-${i+1}`,color:colors[i]}));
  series.push({name:'Òptim',data:aggregateByHour(r,'angle_optim'),cls:'line-opt',color:'#9eada5'});
  svgChart($('angleChart'),series,{digits:0});
}

function renderDecisions(records) {
  $('decisionSection').hidden=false;
  const sectors=[...new Set(records.map(r=>r.sector))];
  const f=$('sectorFilter'); f.innerHTML='<option value="all">Tots els sectors</option>'+sectors.map(s=>`<option>${esc(s)}</option>`).join('');
  const draw=()=>{
    const selected=f.value;
    $('decisionRows').innerHTML=records.filter(r=>selected==='all'||r.sector===selected).map(r=>`<tr>
      <td>${r.hora}:00</td><td>${esc(r.sector)}</td><td><b>${esc(r.accio)}</b></td><td>${fmt(r.angle_real,1)}°</td>
      <td class="muted">${esc(r.riscos)||'—'}</td><td class="muted">${esc(r.impas)||'—'}</td><td>${esc(r.motiu)||'—'}</td></tr>`).join('');
  }; f.onchange=draw; draw();
}

function renderComparison(runs) {
  const sec=$('comparisonSection');
  sec.hidden=runs.length<2; if(runs.length<2)return;
  const labels={soar:'SOAR / CLIPS',seguidor:'Seguidor',fix:'Panell fix'};
  $('comparisonGrid').innerHTML=runs.map(r=>`<div class="compare-card ${r.controller==='soar'?'active':''}">
    <div class="compare-title">${labels[r.controller]||r.controller}</div>
    <div class="compare-values">
      <div><span>ENERGIA</span><b>${fmt(r.kpis.energy_kwh,1)} kWh</b></div>
      <div><span>RENDIMENT</span><b>${fmt(r.kpis.efficiency_pct,1)}%</b></div>
      <div><span>VIOLACIONS</span><b>${r.kpis.safety_violations}</b></div>
      <div><span>EXPOSICIÓ</span><b>${r.kpis.wind_exposure_h} h</b></div>
    </div></div>`).join('');
}

async function runSimulation() {
  $('runButton').disabled=true; $('runButton').textContent='Executant…'; hideError();
  try {
    const payload={scenario:$('scenario').value,controller:$('controller').value,day:$('day').value,seed:Number($('seed').value||0),compare:$('compare').checked};
    const data=await api('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const primary=data.runs.find(r=>r.controller===payload.controller) || data.runs[0]; currentRun=primary;
    renderOntology(data.ontology); renderKpis(primary.kpis); renderSectors(primary.sectors); renderCharts(primary); renderDecisions(primary.records); renderComparison(data.runs);
    $('runContext').textContent=`${primary.scenario_name} · ${primary.day} · ${primary.location} · ${primary.controller.toUpperCase()}`;
  } catch(e){ showError(e.message); }
  finally {$('runButton').disabled=false;$('runButton').textContent='Executar simulació';}
}
function showError(msg){const e=$('errorBox');e.textContent=msg;e.style.display='block';}
function hideError(){$('errorBox').style.display='none';}
$('scenario').addEventListener('change',loadDays);
$('runButton').addEventListener('click',runSimulation);
init();
