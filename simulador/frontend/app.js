import { DigitalTwin3D } from './twin3d.js';
import { LineChart } from './charts.js';
import { Ribbon } from './timeline.js';
import {
  $, clamp, lerp, mean, esc, fmt, fmtInt, clock, icon,
  actionCategory, actionLabel, CATEGORIES, parseRisks, prettyReason,
  cropColor, cropLabel, sectorLabel, CONTROLLER_SHORT, CONTROLLER_LONG,
} from './ui.js';

/* La UI no implementa cap política de decisió: només presenta el que CLIPS
   ha decidit i que el backend retorna a /api/simulate. */

const state = { boot: null, controller: 'soar', runs: [], run: null, frames: [], sectors: [], selected: null, tab: 'balance', irrCycles: [] };
const playback = { position: 0, speed: 0.7, playing: false, rafId: null, lastTs: null };
let twin = null;
let ribbon = null;
let charts = [];
const cards = new Map();
const hud = {};
let trace = { rows: [], cycleIdx: -1 };

/* ================= Dades ================= */
async function api(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}

function groupFrames(records) {
  const byCycle = new Map();
  records.forEach((r) => {
    const key = Number(r.cicle);
    if (!byCycle.has(key)) byCycle.set(key, { cicle: key, hora: Number(r.hora), records: new Map() });
    byCycle.get(key).records.set(r.sector, r);
  });
  return [...byCycle.values()].sort((a, b) => a.cicle - b.cicle).map((f) => {
    const all = [...f.records.values()];
    return {
      ...f,
      globals: {
        hora: f.hora,
        temp: mean(all.map((r) => r.t_cultiu)),
        ghi: mean(all.map((r) => r.ghi)),
        wind: mean(all.map((r) => r.vent_real ?? r.vent_obs)),
        rain: mean(all.map((r) => r.pluja_mm)),
        water: mean(all.map((r) => r.aigua_pct)),
        cloud: mean(all.map((r) => r.nubolositat)),
        elevation: mean(all.map((r) => r.elevacio_solar)),
        azimuth: mean(all.map((r) => r.azimut_solar)),
      },
    };
  });
}

function interpolateFrames(frames, pos) {
  if (!frames.length) return null;
  const bounded = clamp(pos, 0, Math.max(0, frames.length - 1));
  const i0 = Math.floor(bounded);
  const i1 = Math.min(i0 + 1, frames.length - 1);
  const t = bounded - i0;
  const a = frames[i0]; const b = frames[i1];
  const sectors = new Map();
  const names = new Set([...a.records.keys(), ...b.records.keys()]);
  names.forEach((name) => {
    const ra = a.records.get(name) || b.records.get(name);
    const rb = b.records.get(name) || a.records.get(name);
    const pick = (k) => (t < 0.5 ? (ra[k] || rb[k]) : (rb[k] || ra[k]));
    sectors.set(name, {
      sector: name,
      cultiu: pick('cultiu'),
      accio: pick('accio'),
      /* El reg d'un cicle passa durant tota aquella hora: es manté (no s'interpola). */
      reg_accio: ra.reg_accio,
      reg_motiu: ra.reg_motiu,
      reg_mode: ra.reg_mode,
      reg_dosi_pct: ra.reg_dosi_pct || 0,
      motiu: pick('motiu'),
      riscos: pick('riscos'),
      impas: pick('impas'),
      angle_real: lerp(ra.angle_real, rb.angle_real, t),
      angle_optim: lerp(ra.angle_optim, rb.angle_optim, t),
      aigua_pct: lerp(ra.aigua_pct, rb.aigua_pct, t),
      t_cultiu: lerp(ra.t_cultiu, rb.t_cultiu, t),
      P_kw: lerp(ra.P_kw, rb.P_kw, t),
      rad_cultiu: lerp(ra.rad_cultiu, rb.rad_cultiu, t),
      reg_mm: ra.reg_mm,
      pluja_mm: lerp(ra.pluja_mm, rb.pluja_mm, t),
      vent_real: lerp(ra.vent_real ?? ra.vent_obs, rb.vent_real ?? rb.vent_obs, t),
      ghi: lerp(ra.ghi, rb.ghi, t),
      elevacio_solar: lerp(ra.elevacio_solar, rb.elevacio_solar, t),
      azimut_solar: lerp(ra.azimut_solar, rb.azimut_solar, t),
      nubolositat: lerp(ra.nubolositat, rb.nubolositat, t),
    });
  });
  return {
    position: bounded,
    cicle: t < 0.5 ? a.cicle : b.cicle,
    hora: lerp(a.hora, b.hora, t),
    globals: {
      temp: lerp(a.globals.temp, b.globals.temp, t),
      ghi: lerp(a.globals.ghi, b.globals.ghi, t),
      wind: lerp(a.globals.wind, b.globals.wind, t),
      rain: lerp(a.globals.rain, b.globals.rain, t),
      water: lerp(a.globals.water, b.globals.water, t),
      cloud: lerp(a.globals.cloud, b.globals.cloud, t),
      elevation: lerp(a.globals.elevation, b.globals.elevation, t),
      azimuth: lerp(a.globals.azimuth, b.globals.azimuth, t),
    },
    sectors,
  };
}

function conditionsNarrative(frame) {
  const g = frame.globals;
  const wet = [...frame.sectors.values()].filter((s) => Number(s.reg_mm) > 0.05);
  if (wet.length) {
    const soar = wet.some((s) => s.reg_accio);
    return soar
      ? `Reg en marxa: CLIPS decideix la dosi segons l’aigua del sòl, la pluja prevista i el cost de la bomba.`
      : 'Reg en marxa amb la regla fixa de la finca (sense decisió del controlador).';
  }
  if ((g.rain || 0) > 0.2) return 'Plou: el sòl s’humiteja i baixa la radiació disponible. El reg el decideix CLIPS segons l’estat del sòl.';
  if ((g.wind || 0) >= 12) return 'Vent fort: el risc mecànic és alt i el controlador prioritza la seguretat dels panells.';
  if ((g.cloud || 0) > 0.65) return 'Cel molt cobert: baixa la irradiància i, amb ella, la producció fotovoltaica.';
  if ((g.ghi || 0) > 700) return 'Radiació elevada: cal equilibrar producció, ombra i estrès del cultiu.';
  return 'Condicions estables: clima, energia, sòl i panells evolucionen sense incidències.';
}

/* ================= Utilitats DOM ================= */
function setText(el, txt) { if (el && el._t !== txt) { el.textContent = txt; el._t = txt; } }
function setHTML(el, html) { if (el && el._h !== html) { el.innerHTML = html; el._h = html; } }
function showError(msg) { $('errorText').textContent = msg; $('errorBox').hidden = false; }
function hideError() { $('errorBox').hidden = true; }

function riskChips(str, impas) {
  const chips = parseRisks(str).map((r) => `<span class="risk lvl-${r.rank}">${esc(r.label)}${r.level ? ` · ${esc(r.level)}` : ''}</span>`);
  if (impas) chips.push(`<span class="risk impasse">Impasse · ${esc(impas)}</span>`);
  return chips.join('');
}

/* ================= HUD de l'escena ================= */
const CLIMATE = [
  ['ghi', 'sun', 'Radiació', 'W/m²'],
  ['wind', 'wind', 'Vent', 'm/s'],
  ['rain', 'rain', 'Pluja', 'mm'],
  ['cloud', 'cloud', 'Núvols', '%'],
  ['water', 'drop', 'Aigua sòl', '%'],
];

function buildHud() {
  $('climateStrip').innerHTML = CLIMATE.map(([k, ic, label, unit]) =>
    `<div class="cs" data-k="${k}">${icon(ic)}<div><span>${label}</span><b><em data-v>—</em><small>${unit}</small></b></div></div>`).join('');
  hud.vals = Object.fromEntries(CLIMATE.map(([k]) => [k, $('climateStrip').querySelector(`[data-k="${k}"] [data-v]`)]));
  hud.clock = $('hudClock'); hud.sun = $('hudSun'); hud.narr = $('hudNarrative'); hud.dot = $('sunDot');
}

function updateHud(frame) {
  const g = frame.globals;
  setText(hud.clock, clock(frame.hora));
  const h0 = state.frames[0].hora - 1;
  const h1 = state.frames[state.frames.length - 1].hora + 1;
  const f = clamp((frame.hora - h0) / (h1 - h0), 0, 1);
  const th = Math.PI * (1 - f);
  hud.dot.setAttribute('cx', (84 + 66 * Math.cos(th)).toFixed(1));
  hud.dot.setAttribute('cy', (70 - 66 * Math.sin(th)).toFixed(1));
  hud.dot.classList.toggle('night', (g.elevation || 0) < 0);
  setText(hud.sun, `Elevació ${fmt(g.elevation, 0)}° · azimut ${fmt(g.azimuth, 0)}°`);
  setText(hud.narr, conditionsNarrative(frame));
  setText(hud.vals.ghi, fmtInt(g.ghi));
  setText(hud.vals.wind, fmt(g.wind, 1));
  setText(hud.vals.rain, fmt(g.rain, 1));
  setText(hud.vals.cloud, fmt(clamp((g.cloud || 0) * 100, 0, 100), 0));
  setText(hud.vals.water, fmt(g.water, 0));
}

/* ================= Panell de sectors ================= */
function buildCards() {
  const host = $('sectorCards');
  cards.clear();
  host.innerHTML = state.sectors.map((s) => `
    <article class="sector-card" data-sector="${esc(s.id)}" tabindex="0" role="button" aria-pressed="false" aria-label="Segueix ${esc(sectorLabel(s.id))}">
      <header>
        <div class="sc-id"><i class="crop-dot" style="--c:${cropColor(s.crop)}"></i>
          <div><h3>${esc(sectorLabel(s.id))}</h3><p>${esc(cropLabel(s.crop))}</p></div></div>
        <span class="chip act" data-r="action">—</span>
      </header>
      <div class="sc-body">
        <svg class="side" viewBox="0 0 120 66" aria-hidden="true">
          <line class="ground" x1="6" y1="60" x2="114" y2="60"/>
          <path class="post" d="M60 60 V36"/>
          <rect class="opt" x="18" y="31.5" width="84" height="5" rx="1.5" data-r="opt"/>
          <rect class="pan" x="18" y="31.5" width="84" height="5" rx="1.5" data-r="pan"/>
        </svg>
        <dl class="sc-stats">
          <div><dt>Angle</dt><dd><b data-r="angle">—</b><small>òptim <span data-r="optimal">—</span></small></dd></div>
          <div><dt>Sòl</dt><dd><b data-r="water">—</b><span class="meter"><i data-r="waterBar"></i></span></dd></div>
          <div><dt>Potència</dt><dd><b data-r="power">—</b></dd></div>
          <div><dt>T cultiu</dt><dd><b data-r="tcrop">—</b></dd></div>
        </dl>
      </div>
      <div class="sc-why">
        <p class="why" data-r="why"></p>
        <div class="irr" data-r="irr">${icon('drop')}<span data-r="irrText"></span></div>
        <div class="risks" data-r="risks"></div>
      </div>
    </article>`).join('');
  host.querySelectorAll('.sector-card').forEach((el) => {
    const id = el.dataset.sector;
    const r = (k) => el.querySelector(`[data-r="${k}"]`);
    cards.set(id, { el, action: r('action'), pan: r('pan'), opt: r('opt'), angle: r('angle'), optimal: r('optimal'), water: r('water'), waterBar: r('waterBar'), power: r('power'), tcrop: r('tcrop'), why: r('why'), risks: r('risks'), irr: r('irr'), irrText: r('irrText') });
    el.addEventListener('click', () => selectSector(state.selected === id ? null : id));
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); } });
  });
}

function updateCards(frame) {
  frame.sectors.forEach((s, id) => {
    const c = cards.get(id);
    if (!c) return;
    const cat = actionCategory(s.accio);
    const irr = Number(s.reg_mm) > 0.05;
    setText(c.action, actionLabel(s.accio) + (irr ? ` · reg ${fmt(s.reg_mm, 1)} mm` : ''));
    if (c.action._cat !== cat) { c.action.className = `chip act cat-${cat}`; c.action._cat = cat; }
    c.pan.setAttribute('transform', `rotate(${(s.angle_real || 0).toFixed(1)} 60 34)`);
    c.opt.setAttribute('transform', `rotate(${(s.angle_optim || 0).toFixed(1)} 60 34)`);
    setText(c.angle, `${fmt(s.angle_real, 0)}°`);
    setText(c.optimal, `${fmt(s.angle_optim, 0)}°`);
    setText(c.water, `${fmt(s.aigua_pct, 0)} %`);
    c.waterBar.style.width = `${clamp(s.aigua_pct || 0, 0, 100)}%`;
    setText(c.power, `${fmt(s.P_kw, 1)} kW`);
    setText(c.tcrop, `${fmt(s.t_cultiu, 1)} °C`);
    setText(c.why, prettyReason(s.motiu) || 'Sense decisió registrada.');
    setHTML(c.risks, riskChips(s.riscos, s.impas));
    const mode = s.reg_mode || 'cap';
    const watering = Number(s.reg_mm) > 0.05;
    let irrTxt = '';
    if (s.reg_accio) {
      irrTxt = `${actionLabel(s.reg_accio)}${watering ? ` · dosi ${fmt(s.reg_dosi_pct, 0)} % · ${fmt(s.reg_mm, 1)} mm` : ''}`;
    } else if (mode !== 'cap') {
      irrTxt = watering ? `Reg de la finca · ${fmt(s.reg_mm, 1)} mm` : 'Reg de la finca (regla fixa)';
    } else {
      irrTxt = 'Sense reg';
    }
    setText(c.irrText, irrTxt);
    c.irr.classList.toggle('on', watering);
    c.irr.classList.toggle('idle', !watering);
  });
}

function selectSector(id) {
  state.selected = id;
  cards.forEach((c, k) => { c.el.classList.toggle('selected', k === id); c.el.setAttribute('aria-pressed', String(k === id)); });
  twin?.setSelected(id);
  if (id) twin?.focusSector(id); else { twin?.setCameraPreset('overview'); setActiveCamera('overview'); }
  if (id) setActiveCamera(null);
  $('railHint').textContent = id ? 'Clic de nou per tornar' : 'Clic per seguir';
}

function setActiveCamera(name) {
  document.querySelectorAll('.camera-btn').forEach((b) => b.classList.toggle('active', b.dataset.camera === name));
}

/* ================= Aplica un fotograma ================= */
function applyFrame(frame) {
  twin?.setState(frame);
  updateHud(frame);
  updateCards(frame);
  ribbon.setPosition(frame.position);
  charts.forEach((c) => c.setPlayhead(frame.hora));
  setText($('cycleClock'), clock(frame.hora));
  setText($('cycleInfo'), `Cicle ${Math.round(frame.position) + 1} de ${state.frames.length}`);
  const wet = [...frame.sectors.values()].filter((s) => Number(s.reg_mm) > 0.05);
  const badge = $('irrBadge');
  badge.hidden = !wet.length;
  if (wet.length) setHTML(badge, `${icon('drop')}Reg actiu · ${wet.map((s) => sectorLabel(s.sector).replace('Sector ', 'S')).join(', ')}`);
  updateTraceHighlight(Math.round(frame.position));
}

function renderPosition(pos) {
  const f = interpolateFrames(state.frames, pos);
  if (!f) return;
  playback.position = clamp(pos, 0, Math.max(0, state.frames.length - 1));
  applyFrame(f);
}

function seekToHour(h) {
  const fr = state.frames;
  if (!fr.length) return;
  let i = 0;
  while (i < fr.length - 1 && fr[i + 1].hora <= h) i += 1;
  const next = fr[Math.min(i + 1, fr.length - 1)];
  const span = next.hora - fr[i].hora || 1;
  stopPlayback();
  renderPosition(i + clamp((h - fr[i].hora) / span, 0, 1));
}

/* ================= Reproducció ================= */
function setPlayIcon() {
  $('play3d').innerHTML = icon(playback.playing ? 'pause' : 'play');
  $('play3d').setAttribute('aria-label', playback.playing ? 'Pausa' : 'Reproduir');
}

function stopPlayback() {
  playback.playing = false; playback.lastTs = null;
  if (playback.rafId) cancelAnimationFrame(playback.rafId);
  playback.rafId = null;
  setPlayIcon();
}

function tick(ts) {
  if (!playback.playing) return;
  if (!playback.lastTs) playback.lastTs = ts;
  const dt = (ts - playback.lastTs) / 1000;
  playback.lastTs = ts;
  const max = Math.max(0, state.frames.length - 1);
  const slow = $('slowIrr').checked && state.irrCycles[Math.min(max, Math.floor(playback.position))] ? 0.3 : 1;
  const next = playback.position + dt * playback.speed * slow;
  if (next >= max) { renderPosition(max); stopPlayback(); return; }
  renderPosition(next);
  playback.rafId = requestAnimationFrame(tick);
}

function startPlayback() {
  if (state.frames.length < 2) return;
  if (playback.position >= state.frames.length - 1) renderPosition(0);
  playback.playing = true; playback.lastTs = null;
  setPlayIcon();
  playback.rafId = requestAnimationFrame(tick);
}

function togglePlayback() { if (playback.playing) stopPlayback(); else startPlayback(); }

/* ================= Balanç, resum, comparativa ================= */
function row(label, value, unit = '', main = false) {
  return `<div class="lrow${main ? ' main' : ''}"><dt>${label}</dt><dd><b>${value}</b>${unit ? `<small>${unit}</small>` : ''}</dd></div>`;
}

const REG_MODE = {
  soar: 'Decidit per CLIPS', finca: 'Regla fixa de la finca', fao: 'Calendari FAO-56', cap: 'Sense reg',
};

function renderBalance(run) {
  const k = run.kpis;
  const sc = run.records.length;
  const eff = clamp(k.efficiency_pct ?? 0, 0, 100);
  $('balance').innerHTML = `
    <div class="ledger">
      <section class="lg-group tone-sun">
        <h3>${icon('bolt')}Energia</h3>
        <dl>${row('Producció fotovoltaica', fmt(k.energy_kwh, 1), 'kWh', true)}
          ${row('Energia neta', fmt(k.net_energy_kwh, 1), 'kWh')}
          ${row('Consum de la bomba', fmt(k.pump_kwh, 2), 'kWh')}</dl>
        <div class="meterline"><span>Eficiència respecte l’òptim</span><b>${fmt(k.efficiency_pct, 1)} %</b></div>
        <span class="meter big"><i style="width:${eff}%"></i></span>
      </section>
      <section class="lg-group tone-water">
        <h3>${icon('drop')}Aigua <small class="mode">${REG_MODE[k.irrigation_mode] || ''}</small></h3>
        <dl>${row('Reg net aplicat', fmt(k.irrigation_mm, 1), 'mm', true)}
          ${row('Reg executats', fmtInt(k.irrigation_events), 'sector·h')}
          ${row('Aigua bombejada', fmt(k.irrigation_m3, 1), 'm³')}
          ${row('Pluja del dia', fmt(k.rain_mm, 1), 'mm')}
          ${row('Percolació', fmt(k.percolation_mm, 1), 'mm')}
          ${row('Estrès hídric', `${fmtInt(k.water_stress_cycles)} de ${fmtInt(sc)}`, 'sector·h')}</dl>
      </section>
      <section class="lg-group tone-safe">
        <h3>${icon('wind')}Seguretat i cultiu</h3>
        <dl>${row('Violacions de seguretat', fmtInt(k.safety_violations), '', true)}
          ${row('Hores exposades al vent', fmtInt(k.wind_exposure_h), 'h')}
          ${row('Estrès tèrmic', fmtInt(k.heat_stress_h), 'sector·h')}
          ${row('Estrès per radiació', fmtInt(k.radiation_stress_h), 'sector·h')}
          ${row('Invariants incomplerts', fmtInt(k.invariants_ko))}</dl>
      </section>
      <section class="lg-group tone-mind">
        <h3>${icon('layers')}Raonament</h3>
        <dl>${row('Impasses', fmtInt(k.impasses), '', true)}
          ${row('Decisions via chunk', fmtInt(k.chunk_decisions))}
          ${row('Decisions via reforç', fmtInt(k.rl_decisions))}
          ${row('Temps per cicle', fmt(k.avg_ms, 1), 'ms')}
          ${row('Regles per cicle', fmt(k.rules_per_cycle, 0))}</dl>
      </section>
    </div>`;

  $('sectorSummary').innerHTML = `
    <h3 class="sub">Estat al final del dia</h3>
    <div class="table-wrap short"><table class="plain">
      <thead><tr><th>Sector</th><th>Cultiu</th><th>Última acció</th><th class="r">Angle</th><th class="r">Òptim</th><th class="r">Sòl</th><th class="r">T cultiu</th><th class="r">Potència</th><th class="r">Reg del dia</th></tr></thead>
      <tbody>${run.sectors.map((s) => `<tr>
        <td><i class="crop-dot" style="--c:${cropColor(s.crop)}"></i>${esc(sectorLabel(s.sector))}</td><td>${esc(cropLabel(s.crop))}</td>
        <td><span class="chip act cat-${actionCategory(s.action)}">${esc(actionLabel(s.action))}</span></td>
        <td class="r num">${fmt(s.angle, 0)}°</td><td class="r num">${fmt(s.optimal_angle, 0)}°</td>
        <td class="r num">${fmt(s.water_pct, 0)} %</td><td class="r num">${fmt(s.crop_temp, 1)} °C</td><td class="r num">${fmt(s.power_kw, 1)} kW</td><td class="r num">${s.irrigation_mm > 0 ? `${fmt(s.irrigation_mm, 1)} mm` : '—'}</td></tr>`).join('')}</tbody>
    </table></div>`;
}

const COMPARE_METRICS = [
  { key: 'energy_kwh', label: 'Producció fotovoltaica', unit: 'kWh', digits: 1, better: 'high' },
  { key: 'net_energy_kwh', label: 'Energia neta', unit: 'kWh', digits: 1, better: 'high' },
  { key: 'irrigation_m3', label: 'Aigua de reg bombejada', unit: 'm³', digits: 1, better: 'low' },
  { key: 'water_stress_cycles', label: 'Estrès hídric', unit: 'sector·h', digits: 0, better: 'low' },
  { key: 'heat_stress_h', label: 'Estrès tèrmic', unit: 'sector·h', digits: 0, better: 'low' },
  { key: 'safety_violations', label: 'Violacions de seguretat', unit: '', digits: 0, better: 'low' },
  { key: 'wind_exposure_h', label: 'Exposició al vent', unit: 'h', digits: 0, better: 'low' },
];

function renderComparison(runs) {
  const host = $('comparison');
  if (runs.length < 2) { host.innerHTML = ''; return; }
  const order = ['soar', 'seguidor', 'fix'];
  const sorted = [...runs].sort((a, b) => order.indexOf(a.controller) - order.indexOf(b.controller));
  const soar = sorted.find((r) => r.controller === 'soar');
  host.innerHTML = `<h3 class="sub">SOAR davant de les referències</h3><div class="cmp">${COMPARE_METRICS.map((m) => {
    const vals = sorted.map((r) => Number(r.kpis[m.key]) || 0);
    const max = Math.max(...vals, 1e-9);
    const best = m.better === 'high' ? Math.max(...vals) : Math.min(...vals);
    return `<div class="cmp-row"><h4>${m.label}</h4>${sorted.map((r, i) => {
      const v = vals[i];
      const isBest = v === best && new Set(vals).size > 1;
      const delta = soar && r !== soar && Number(soar.kpis[m.key]) ? ((Number(soar.kpis[m.key]) - v) / Math.abs(v || 1)) * 100 : null;
      return `<div class="cmp-line ${r.controller === 'soar' ? 'is-soar' : ''}"><span class="who">${CONTROLLER_LONG[r.controller] || r.controller}${delta != null && Number.isFinite(delta) && Math.abs(delta) >= 0.05 ? `<small>SOAR ${delta > 0 ? '+' : '−'}${fmt(Math.abs(delta), 1)} %</small>` : ''}</span>
        <span class="bar"><i style="width:${Math.max(1.5, (v / max) * 100)}%"></i></span>
        <b class="num">${fmt(v, m.digits)}${m.unit ? ` <small>${m.unit}</small>` : ''}</b>
        <span class="mark">${isBest ? icon('check') : ''}</span></div>`;
    }).join('')}</div>`;
  }).join('')}</div>`;
}

/* ================= Gràfics ================= */
function aggregateByHour(records, key, { sector = null, mode = 'avg' } = {}) {
  const m = new Map();
  records.filter((r) => !sector || r.sector === sector).forEach((r) => {
    const h = Number(r.hora); const v = Number(r[key]);
    if (!Number.isFinite(v)) return;
    if (!m.has(h)) m.set(h, []);
    m.get(h).push(v);
  });
  return [...m].sort((a, b) => a[0] - b[0]).map(([h, vs]) => [h, mode === 'sum' ? vs.reduce((a, b) => a + b, 0) : vs.reduce((a, b) => a + b, 0) / vs.length]);
}

function buildCharts(run) {
  charts.forEach((c) => c.destroy());
  const r = run.records;
  const seek = (h) => seekToHour(h);
  const mk = (id, opts) => new LineChart($(id), { onSeek: seek, ...opts });
  const secSeries = (key, extra = {}) => state.sectors.map((s, i) => ({
    name: `${sectorLabel(s.id)} · ${cropLabel(s.crop)}`, color: cropColor(s.crop), data: aggregateByHour(r, key, { sector: s.id }),
    dashed: false, width: 3.6 - i * 0.9, ...(i && state.sectors.some((o, j) => j < i && o.crop === s.crop) ? { dashed: true } : {}), ...extra,
  }));
  const energy = mk('chEnergy', { y: { min: 0, digits: 0 }, label: 'Producció fotovoltaica en kW' });
  energy.setSeries([
    { name: 'Producció', color: 'var(--sun)', data: aggregateByHour(r, 'P_kw', { mode: 'sum' }), area: true, unit: 'kW', digits: 1 },
    { name: 'Òptim teòric', color: 'var(--tx-2)', data: aggregateByHour(r, 'P_opt_kw', { mode: 'sum' }), dashed: true, unit: 'kW', digits: 1 },
  ]);
  const power = mk('chPower', { y: { min: 0, digits: 0 }, label: 'Potència per sector en kW' });
  power.setSeries(secSeries('P_kw', { unit: 'kW', digits: 1 }));
  const angle = mk('chAngle', { y: { min: -60, max: 60, digits: 0 }, label: 'Angle dels panells en graus' });
  angle.setSeries([...secSeries('angle_real', { unit: '°', digits: 0 }),
    { name: 'Òptim', color: 'var(--tx-2)', data: aggregateByHour(r, 'angle_optim'), dashed: true, unit: '°', digits: 0, width: 1.6 }]);
  const irrPeak = Math.max(0, ...aggregateByHour(r, 'reg_mm', { mode: 'sum' }).map((d) => d[1]));
  const water = mk('chWater', { y: { min: 0, max: 100, digits: 0 }, y2: { min: 0, max: Math.max(24, Math.ceil(irrPeak * 2.4)), digits: 0 }, label: 'Humitat del sòl i reg' });
  water.setSeries([...secSeries('aigua_pct', { unit: '%', digits: 0 }),
    { name: 'Reg (mm, eix dret)', color: 'var(--water)', type: 'bar', axis: 'y2', data: aggregateByHour(r, 'reg_mm', { mode: 'sum' }), unit: 'mm', digits: 1 }]);
  const climate = mk('chClimate', { y: { min: 0, digits: 0 }, y2: { digits: 0 }, label: 'Radiació i temperatura del cultiu' });
  climate.setSeries([
    { name: 'Radiació (W/m²)', color: 'var(--sun)', data: aggregateByHour(r, 'ghi'), area: true, unit: 'W/m²', digits: 0 },
    { name: 'T cultiu (°C, eix dret)', color: 'var(--risk)', axis: 'y2', data: aggregateByHour(r, 't_cultiu'), unit: '°C', digits: 1 },
  ]);
  const wind = mk('chWind', { y: { min: 0, digits: 0 }, y2: { min: 0, max: 2, digits: 1 }, label: 'Vent i pluja' });
  wind.setSeries([
    { name: 'Vent (m/s)', color: 'var(--safe)', data: aggregateByHour(r, 'vent_real'), area: true, unit: 'm/s', digits: 1 },
    { name: 'Pluja (mm, eix dret)', color: 'var(--water)', type: 'bar', axis: 'y2', data: aggregateByHour(r, 'pluja_mm'), unit: 'mm', digits: 1 },
  ]);
  charts = [energy, power, angle, water, climate, wind];
}

/* ================= Traçabilitat ================= */
function buildTrace(run) {
  const idxOf = new Map(state.frames.map((f, i) => [f.cicle, i]));
  const sel = $('sectorFilter');
  sel.innerHTML = '<option value="all">Tots els sectors</option>' + state.sectors.map((s) => `<option value="${esc(s.id)}">${esc(sectorLabel(s.id))}</option>`).join('');
  const body = $('decisionRows');
  const recs = run.records;
  body.innerHTML = recs.map((r, i) => {
    const incident = Boolean(r.riscos || r.impas || Number(r.reg_mm) > 0.05);
    const diff = Math.abs(Number(r.angle_ordre) - Number(r.angle_real)) > 0.5;
    return `<tr data-i="${i}" data-c="${idxOf.get(Number(r.cicle))}" data-s="${esc(r.sector)}" data-inc="${incident ? 1 : 0}">
      <td class="num">${clock(r.hora)}</td>
      <td><i class="crop-dot" style="--c:${cropColor(r.cultiu)}"></i>${esc(sectorLabel(r.sector))}</td>
      <td><span class="chip act cat-${actionCategory(r.accio)}">${esc(actionLabel(r.accio))}</span></td>
      <td class="r num">${fmt(r.angle_real, 0)}°${diff ? `<small class="dim"> ordre ${fmt(r.angle_ordre, 0)}°</small>` : ''}</td>
      <td class="r num">${Number(r.reg_mm) > 0.05 ? `${fmt(r.reg_mm, 1)} mm${r.reg_accio ? `<small class="dim"> ${esc(actionLabel(r.reg_accio).toLowerCase())} ${fmt(r.reg_dosi_pct, 0)} %</small>` : ''}` : '—'}</td>
      <td class="riskcell"><div class="risks">${riskChips(r.riscos, '') || '<span class="dim">—</span>'}</div></td>
      <td>${r.impas ? `<span class="risk impasse">${esc(r.impas)}</span>` : '<span class="dim">—</span>'}</td>
      <td class="why">${esc(prettyReason(r.motiu))}${r.reg_accio && r.reg_accio !== 'no-regar' && r.reg_motiu ? `<br><span class="reg-why">Reg: ${esc(prettyReason(r.reg_motiu))}</span>` : ''}</td></tr>`;
  }).join('');
  trace = { rows: [...body.querySelectorAll('tr')], cycleIdx: -1 };
  trace.rows.forEach((tr) => tr.addEventListener('click', () => { stopPlayback(); renderPosition(Number(tr.dataset.c)); }));
  applyTraceFilter();
}

function applyTraceFilter() {
  const sec = $('sectorFilter').value;
  const only = $('onlyIncidents').checked;
  let shown = 0;
  trace.rows.forEach((tr) => {
    const ok = (sec === 'all' || tr.dataset.s === sec) && (!only || tr.dataset.inc === '1');
    tr.hidden = !ok;
    if (ok) shown += 1;
  });
  $('traceCount').textContent = `${shown} de ${trace.rows.length} registres`;
}

function updateTraceHighlight(idx) {
  if (idx === trace.cycleIdx) return;
  trace.cycleIdx = idx;
  let first = null;
  trace.rows.forEach((tr) => {
    const on = Number(tr.dataset.c) === idx;
    tr.classList.toggle('now', on);
    if (on && !first && !tr.hidden) first = tr;
  });
  if (first && state.tab === 'trace' && playback.playing) {
    const wrap = $('traceWrap');
    wrap.scrollTop = Math.max(0, first.offsetTop - 44);
  }
}

/* ================= Ontologia ================= */
function renderOntology(o) {
  $('statusText').textContent = o.valid ? 'Ontologies validades' : 'Error d’ontologia';
  $('systemStatus').classList.toggle('ok', Boolean(o.valid));
  $('systemStatus').classList.toggle('bad', !o.valid);
  $('archDomain').textContent = o.domain;
  $('archModel').textContent = o.model;
  $('archReg').textContent = o.reg ? o.reg.file : 'no carregada';
  $('factsCount').textContent = `${o.facts.total} fets`;
  const f = o.facts; const v = o.validation; const g = o.reg;
  const chips = [
    `${f.sector} sectors`, `${f.cultiu} cultius`, `${f.panell} panells`, `${f.estat_sensor} estats de sensor`,
    `${v.classes_operacionals} classes`, `${v.propietats_objecte} propietats d’objecte`, `${v.propietats_dades} de dades`,
    `${v.relacions_validades} relacions validades`, `${v.literals_validats} literals validats`,
  ];
  $('ontologyStats').innerHTML = chips.map((x) => `<span class="chip">${x}</span>`).join('');
  if (g) {
    const c = g.config;
    $('regStats').innerHTML = [
      `${g.valves} vàlvules`, `${g.objectives} objectiu d’estalvi d’aigua`, `${g.sources} fonts de preferència`,
      `${f.reg} fets de reg`, `${g.validation.relacions_reg_validades} relacions validades`,
    ].map((x) => `<span class="chip">${x}</span>`).join('');
    $('regConfig').innerHTML = [
      ['Anticipació', fmt(c.anticipacio, 2), ''],
      ['La pluja anul·la el reg a partir de', fmt(c.pluja_anulla, 0), 'mm'],
      ['Pluja mínima que es té en compte', fmt(c.pluja_minima, 0), 'mm'],
      ['Hora fresca del matí', `${c.hora_fresca_mati}:00`, ''],
      ['Hora fresca de la tarda', `${c.hora_fresca_tarda}:00`, ''],
    ].map(([l, val, u]) => `<div><dt>${l}</dt><dd><b>${val}</b>${u ? `<small>${u}</small>` : ''}</dd></div>`).join('');
  }
}

/* ================= Simulació ================= */
async function loadDays() {
  const d = await api(`/api/days?scenario=${encodeURIComponent($('scenario').value)}`);
  const el = $('day');
  el.innerHTML = '';
  d.days.forEach((day) => el.add(new Option(day, day)));
  if (d.days.length) el.value = d.days[Math.floor(d.days.length / 2)];
}

function setBusy(on) {
  $('progress').hidden = !on;
  ['runButton', 'emptyRun'].forEach((id) => { $(id).disabled = on; });
  $('runButton').textContent = on ? 'Executant…' : 'Executar simulació';
  $('runButton').classList.toggle('busy', on);
}

function sectorsFrom(records) {
  const seen = new Map();
  records.forEach((r) => { if (!seen.has(r.sector)) seen.set(r.sector, { id: r.sector, crop: r.cultiu }); });
  return [...seen.values()].sort((a, b) => a.id.localeCompare(b.id));
}

async function runSimulation() {
  hideError(); setBusy(true); stopPlayback();
  try {
    const payload = { scenario: $('scenario').value, controller: state.controller, day: $('day').value, seed: Number($('seed').value || 0), compare: $('compare').checked };
    const data = await api('/api/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    renderOntology(data.ontology);
    const primary = data.runs.find((r) => r.controller === payload.controller) || data.runs[0];
    state.runs = data.runs; state.run = primary;
    state.frames = groupFrames(primary.records);
    state.sectors = sectorsFrom(primary.records);
    state.irrCycles = state.frames.map((f) => [...f.records.values()].some((r) => Number(r.reg_mm) > 0.05));
    state.selected = null;
    twin?.setSelected(null);

    $('sceneEmpty').hidden = true;
    $('play3d').disabled = false; $('reset3d').disabled = false;
    buildCards();
    ribbon.setData({ frames: state.frames, sectors: state.sectors });
    renderBalance(primary);
    renderComparison(data.runs);
    buildCharts(primary);
    buildTrace(primary);
    renderPosition(0);
    startPlayback();
  } catch (err) {
    showError(err.message || String(err));
  } finally {
    setBusy(false);
  }
}

/* ================= Interfície ================= */
function buildControllers(list) {
  const host = $('controller');
  host.innerHTML = list.map((c) => `<button type="button" role="radio" data-id="${c.id}" aria-checked="${c.id === state.controller}" title="${esc(c.label)}">${esc(CONTROLLER_SHORT[c.id] || c.label)}</button>`).join('');
  host.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    state.controller = b.dataset.id;
    host.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  }));
}

function buildRibbonLegend() {
  $('ribbonLegend').innerHTML = CATEGORIES.map((c) => `<li><i class="sw cat-${c.id}"></i>${c.label}</li>`).join('')
    + `<li><i class="sw water"></i>Reg</li><li><i class="sw riskdot"></i>Risc</li>`;
}

function setTab(name) {
  state.tab = name;
  document.querySelectorAll('[role="tab"]').forEach((t) => {
    const on = t.dataset.tab === name;
    t.setAttribute('aria-selected', String(on));
    t.tabIndex = on ? 0 : -1;
    $(`panel-${t.dataset.tab}`).hidden = !on;
  });
  if (name === 'charts') requestAnimationFrame(() => charts.forEach((c) => c.draw()));
}

function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem('acs-theme', t); } catch (e) { /* mode privat */ }
  $('themeToggle').innerHTML = icon(t === 'dark' ? 'sun' : 'moon');
  $('themeToggle').setAttribute('aria-label', t === 'dark' ? 'Canvia al tema clar' : 'Canvia al tema fosc');
}

function setRail(open) {
  $('stage').classList.toggle('rail-off', !open);
  $('railOpen').hidden = open;
  try { localStorage.setItem('acs-rail', open ? '1' : '0'); } catch (e) { /* mode privat */ }
  window.dispatchEvent(new Event('resize'));
}

function bindUi() {
  $('railToggle').innerHTML = icon('chevron');
  $('railToggle').addEventListener('click', () => setRail(false));
  $('railOpen').addEventListener('click', () => setRail(true));
  let railOpen = true;
  try { railOpen = localStorage.getItem('acs-rail') !== '0'; } catch (e) { /* mode privat */ }
  setRail(railOpen);
  $('scenario').addEventListener('change', () => loadDays().catch((e) => showError(e.message)));
  $('runButton').addEventListener('click', runSimulation);
  $('emptyRun').addEventListener('click', runSimulation);
  $('play3d').addEventListener('click', togglePlayback);
  $('reset3d').addEventListener('click', () => { stopPlayback(); renderPosition(0); });
  $('errorClose').addEventListener('click', hideError);
  $('errorClose').innerHTML = icon('close');
  $('themeToggle').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
  setTheme(document.documentElement.dataset.theme || 'dark');
  setPlayIcon();
  $('reset3d').innerHTML = icon('reset');

  document.querySelectorAll('.speed-btn').forEach((btn) => btn.addEventListener('click', () => {
    document.querySelectorAll('.speed-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    playback.speed = Number(btn.dataset.speed || 0.7);
  }));
  document.querySelectorAll('.camera-btn').forEach((btn) => btn.addEventListener('click', () => {
    setActiveCamera(btn.dataset.camera);
    twin?.setCameraPreset(btn.dataset.camera);
  }));

  const tabs = [...document.querySelectorAll('[role="tab"]')];
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => setTab(t.dataset.tab));
    t.addEventListener('keydown', (e) => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      const n = tabs[(i + d + tabs.length) % tabs.length];
      n.focus(); setTab(n.dataset.tab);
    });
  });

  $('sectorFilter').addEventListener('change', applyTraceFilter);
  $('onlyIncidents').addEventListener('change', applyTraceFilter);

  window.addEventListener('keydown', (e) => {
    if (/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(e.target.tagName) || e.target.closest?.('.ribbon') || e.metaKey || e.ctrlKey) return;
    if (!state.frames.length) return;
    if (e.code === 'Space') { e.preventDefault(); togglePlayback(); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      stopPlayback();
      renderPosition(clamp(Math.round(playback.position) + (e.key === 'ArrowRight' ? 1 : -1), 0, state.frames.length - 1));
    }
  });
}

async function init() {
  buildHud();
  buildRibbonLegend();
  ribbon = new Ribbon($('ribbon'), { onSeek: (p) => { stopPlayback(); renderPosition(p); } });
  bindUi();
  try {
    twin = new DigitalTwin3D($('scene3d'), $('sceneTooltip'));
    twin.onPick = (id) => selectSector(id && id !== state.selected ? id : null);
  } catch (err) {
    $('sceneLoading').textContent = 'WebGL no està disponible en aquest navegador.';
    showError(`No s'ha pogut inicialitzar el 3D: ${err.message || err}`);
  }
  try {
    state.boot = await api('/api/bootstrap');
    state.boot.scenarios.forEach((s) => $('scenario').add(new Option(s.label, s.id)));
    buildControllers(state.boot.controllers);
    renderOntology(state.boot.ontology);
    await loadDays();
  } catch (err) {
    $('statusText').textContent = 'Sense connexió amb el backend';
    $('systemStatus').classList.add('bad');
    showError(`No s'ha pogut carregar la configuració: ${err.message || err}`);
  }
}

init();
