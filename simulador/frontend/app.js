import { DigitalTwin3D } from './twin3d.js';
import { initCatalog } from './catalog.js';
import { LineChart } from './charts.js';
import { Ribbon } from './timeline.js';
import { startJob, waitForJob, cancelJob, jobResult, jobDay } from './jobs.js';
import { fillScenarioSelect, estimateSeconds } from './scenarios.js';
import { PeriodView, DayStrip } from './period.js';
import {
  $, clamp, lerp, mean, esc, fmt, fmtInt, clock, icon,
  actionCategory, actionLabel, CATEGORIES, parseRisks, prettyReason,
  cropColor, cropLabel, sectorLabel, CONTROLLER_SHORT, CONTROLLER_LONG,
  fmtDate, fmtDuration, fmtSeconds, MODE_LABEL, MODE_HINT,
} from './ui.js';

/* La UI no implementa cap política de decisió: només presenta el que CLIPS
   ha decidit i que el backend retorna a /api/simulate. */

const state = { boot: null, controller: 'soar', runs: [], run: null, frames: [], sectors: [], selected: null, tab: 'balance', irrCycles: [],
  sc: null, days: [], scope: 'period', period: null, metric: 'efficiency_pct', loadToken: 0, job: null, abort: false };
let periodView = null;
let dayStrip = null;
const playback = { position: 0, speed: 0.7, playing: false, rafId: null, lastTs: null };
let twin = null;
let ribbon = null;
let charts = [];
const cards = new Map();
const hud = {};
let trace = { rows: [], cycleIdx: -1 };
let defenseFilter = "all";
let defenseSelected = -1;

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

/* Versió compacta (tarjetes de sector): el risc més greu + «+N»; el detall surt al passar el cursor. */
function riskChipsCompact(str, impas, max = 1) {
  const list = parseRisks(str).map((r) => ({ cls: `lvl-${r.rank}`, text: r.label, full: `${r.label}${r.level ? ` · ${r.level}` : ''}` }));
  if (impas) list.push({ cls: 'impasse', text: 'Impasse', full: `Impasse · ${impas}` });
  const shown = list.slice(0, max); const rest = list.slice(max);
  let h = shown.map((c) => `<span class="risk ${c.cls}" title="${esc(c.full)}">${esc(c.text)}</span>`).join('');
  if (rest.length) h += `<span class="risk more" title="${esc(rest.map((c) => c.full).join(' · '))}">+${rest.length}</span>`;
  return h;
}

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
          <div><dt>Angle</dt><dd><b data-r="angle">—</b><small title="Angle òptim">/ <span data-r="optimal">—</span></small></dd></div>
          <div><dt>Sòl</dt><dd><b data-r="water">—</b><span class="meter"><i data-r="waterBar"></i></span></dd></div>
          <div><dt>Potència</dt><dd><b data-r="power">—</b></dd></div>
          <div><dt>T cultiu</dt><dd><b data-r="tcrop">—</b></dd></div>
        </dl>
      </div>
      <p class="why" data-r="why"></p>
      <div class="sc-foot">
        <div class="irr" data-r="irr">${icon('drop')}<span data-r="irrText"></span></div>
        <div class="risks compact" data-r="risks"></div>
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
    setText(c.action, actionLabel(s.accio));
    if (c.action._cat !== cat) { c.action.className = `chip act cat-${cat}`; c.action._cat = cat; }
    c.pan.setAttribute('transform', `rotate(${(s.angle_real || 0).toFixed(1)} 60 34)`);
    c.opt.setAttribute('transform', `rotate(${(s.angle_optim || 0).toFixed(1)} 60 34)`);
    setText(c.angle, `${fmt(s.angle_real, 0)}°`);
    setText(c.optimal, `${fmt(s.angle_optim, 0)}°`);
    c.angle.title = `Angle òptim ${fmt(s.angle_optim, 0)}°`;
    setText(c.water, `${fmt(s.aigua_pct, 0)} %`);
    c.waterBar.style.width = `${clamp(s.aigua_pct || 0, 0, 100)}%`;
    setText(c.power, `${fmt(s.P_kw, 1)} kW`);
    setText(c.tcrop, `${fmt(s.t_cultiu, 1)} °C`);
    setText(c.why, prettyReason(s.motiu) || 'Sense decisió registrada.');
    c.why.title = c.why.textContent;
    setHTML(c.risks, riskChipsCompact(s.riscos, s.impas));
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
    c.irr.title = irrTxt;
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
  if (next >= max) {
    renderPosition(max); stopPlayback();
    const p = state.period;
    if (p && $('autoNext').checked && p.index < p.result.days.length - 1) showDay(p.index + 1, { play: true });
    return;
  }
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

function ledgerHTML(k, sc) {
  const eff = clamp(k.efficiency_pct ?? 0, 0, 100);
  return `
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
        <dl>${row('Reg net aplicat', fmt(k.irrigation_mm_avg ?? k.irrigation_mm, 1), 'mm/sector', true)}
          ${row('Reg executats', fmtInt(k.irrigation_events), 'sector·h')}
          ${row('Aigua bombejada', fmt(k.irrigation_m3, 1), 'm³')}
          ${row('Pluja', fmt(k.rain_mm, 1), 'mm')}
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
}

function renderBalance(run) {
  const k = run.kpis;
  $('balance').innerHTML = ledgerHTML(k, k.sector_hours ?? run.records.length);
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
  $('comparison').innerHTML = runs.length < 2 ? '' : comparisonHTML(runs);
}

function comparisonHTML(runs) {
  const order = ['soar', 'seguidor', 'fix'];
  const sorted = [...runs].sort((a, b) => order.indexOf(a.controller) - order.indexOf(b.controller));
  const soar = sorted.find((r) => r.controller === 'soar');
  return `<h3 class="sub">SOAR davant de les referències</h3><div class="cmp">${COMPARE_METRICS.map((m) => {
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

/* ================= Laboratori de decisions: evidència real de CLIPS ================= */
function renderDemoDetail(r) {
  const target = $('demoDetails');
  if (!target) return;
  const d = r?.demo;
  if (!d) {
    target.innerHTML = `<div class="demo-empty"><span aria-hidden="true">◈</span><h4>Traça detallada no disponible</h4><p>Activa <b>Mode defensa · traça CLIPS</b>, selecciona el controlador SOAR i executa una simulació d'un sol dia.</p></div>`;
    return;
  }
  const safe = (x) => esc(x === null || x === undefined ? '—' : String(x));
  const items = (x) => Array.isArray(x) ? x : x === null || x === undefined ? [] : [x];
  const has = (x) => x !== null && x !== undefined && x !== '';
  const human = (x) => String(x ?? '').replaceAll('_',' ').replaceAll('-',' ');
  const readable = (x) => typeof x === 'object' ? JSON.stringify(x, null, 2) : String(x ?? '—');
  const kv = (name, val) => `<div class="demo-kv"><dt>${safe(human(name))}</dt><dd>${safe(readable(val))}</dd></div>`;
  const json = (v) => `<pre class="demo-raw">${safe(JSON.stringify(v ?? null, null, 2))}</pre>`;
  const tags = (arr, kind='base') => items(arr).map(v => `<span class="demo-tag demo-tag-${kind}">${safe(v)}</span>`).join('');
  const choice = items(d.seleccio)[0];
  const selected = Array.isArray(choice) ? choice[0] : choice?.op || choice?.nom || (typeof choice === 'string' ? choice : r.accio);
  const choiceText = actionLabel(selected || r.accio);
  const isSafety = actionCategory(r.accio) === 'safety';
  const riskEntries = items(d.riscos).map(v => Array.isArray(v) ? `${v[0]} · ${v[1]}` : readable(v));
  const imp = items(d.impasses);
  const prefs = items(d.preferencies);
  const candidates = items(d.candidats);
  const regCandidates = items(d.reg_candidats);
  const regPrefs = items(d.reg_preferencies);
  const regOrders = items(d.reg_ordres);
  const rules = items(d.regles_disparades);
  const invalid = items(d.invariants_ko).filter(Boolean);
  const observation = d.observacions && typeof d.observacions === 'object' && !Array.isArray(d.observacions) ? d.observacions : {};
  const obsEntries = Object.entries(observation);
  const candidateRows = candidates.map((c) => {
    const name = c?.nom || '—';
    const state = c?.estat || '—';
    const isChosen = String(name) === String(selected || r.accio);
    const matching = prefs.filter(p => p.op === name);
    const rejected = matching.some(p => String(p.tipus).toLowerCase() === 'rebuig') || /rebutj|descart|no-aplic/i.test(state);
    return `<div class="demo-candidate ${isChosen ? 'is-selected' : ''} ${rejected ? 'is-rejected' : ''}">
      <div class="demo-candidate-main"><span class="demo-candidate-symbol" aria-hidden="true">${isChosen ? '✓' : rejected ? '×' : '↗'}</span>
        <div><b>${safe(actionLabel(name))}</b><small>${safe(name)}</small></div></div>
      <div class="demo-candidate-extra"><span class="demo-state ${isChosen ? 'chosen' : rejected ? 'rejected' : ''}">${isChosen ? 'Seleccionat' : rejected ? 'Rebuig registrat' : safe(state)}</span><span class="demo-angle">${safe(c?.['angle-objectiu'])}°</span></div>
      ${matching.length ? `<div class="demo-pref-list">${matching.map(p=>`<span><b>${safe(p.tipus)}</b> · ${safe(p.font)}${p.valor !== undefined ? ` <strong>${safe(p.valor)}</strong>` : ''}${p.op2 && p.op2 !== 'cap' ? ` vs ${safe(p.op2)}` : ''}</span>`).join('')}</div>` : '<div class="demo-pref-list muted">Sense preferències registrades per a aquest operador</div>'}
    </div>`;
  }).join('');
  const dataCard = (id, numeral, title, subtitle, html, icon) => `<section id="${id}" class="demo-panel"><div class="demo-panel-head"><span class="demo-numeral">${numeral}</span><div><h4>${title}</h4><p>${subtitle}</p></div><span class="demo-panel-icon" aria-hidden="true">${icon}</span></div><div class="demo-panel-body">${html}</div></section>`;
  const obsHtml = obsEntries.length ? `<dl class="demo-metrics">${obsEntries.map(([a,b])=>`<div><dt>${safe(human(a))}</dt><dd>${safe(readable(b))}</dd></div>`).join('')}</dl>` : json(d.observacions);
  const riskHtml = `<div class="demo-risk-grid"><div class="demo-context-card"><span>Predicció del model</span>${json(d.prediccio)}</div><div class="demo-context-card"><span>Riscos elaborats</span><div class="demo-risk-tags">${riskEntries.length ? tags(riskEntries,'risk') : '<span class="demo-soft">Cap risc registrat</span>'}</div></div></div>`;
  const prefsHtml = prefs.length ? `<div class="demo-pref-table"><div class="demo-pref-head"><span>Operador</span><span>Tipus</span><span>Valor</span><span>Font de la preferència</span></div>${prefs.map(p=>`<div class="demo-pref-row"><span>${safe(actionLabel(p.op))}${p.op2 && p.op2 !== 'cap' ? `<small>vs ${safe(actionLabel(p.op2))}</small>` : ''}</span><span><em>${safe(p.tipus)}</em></span><strong>${safe(p.valor)}</strong><span class="demo-source">${safe(p.font)}</span></div>`).join('')}</div>` : '<p class="demo-soft">No consten preferències explícites en aquest registre.</p>';
  const regHtml = `<div class="demo-reg-stats"><div><small>Alternatives de reg</small><strong>${regCandidates.length}</strong></div><div><small>Preferències</small><strong>${regPrefs.length}</strong></div><div><small>Ordres emeses</small><strong>${regOrders.length}</strong></div></div><div class="demo-reg-columns"><div><h5>Operadors candidats</h5>${regCandidates.length ? regCandidates.map(c=>`<div class="demo-mini-row"><b>${safe(c.nom)}</b><span>${safe(c.estat)} · dosi ${safe(c.dosi)}</span></div>`).join('') : '<p class="demo-soft">Sense dades</p>'}</div><div><h5>Preferències de reg</h5>${regPrefs.length ? regPrefs.map(p=>`<div class="demo-mini-row"><b>${safe(p.op)}</b><span>${safe(p.tipus)} · ${safe(p.valor)} · ${safe(p.font)}</span></div>`).join('') : '<p class="demo-soft">Sense dades</p>'}</div></div><details class="demo-native-details"><summary>Ordres i explicació originals del reg</summary>${json({ordres:d.reg_ordres,explicacio:d.reg_explicacio})}</details>`;
  target.innerHTML = `
    <div class="demo-summary">
      <div class="demo-summary-top"><div><span class="demo-eyebrow">DECISIÓ SELECCIONADA · CICLE ${safe(r.cicle)}</span><h4>${safe(sectorLabel(r.sector))} <span>·</span> ${safe(clock(r.hora))}</h4></div><span class="demo-clips-badge">● CLIPS real</span></div>
      <div class="demo-summary-main"><div class="demo-decision-icon ${isSafety ? 'safety' : ''}" aria-hidden="true">${isSafety ? '◇' : '↗'}</div><div><small>Operador escollit</small><strong>${safe(choiceText)}</strong><p>${safe(prettyReason(r.motiu) || d.explicacio || 'Sense explicació textual disponible')}</p></div><div class="demo-angle-display"><span>ANGLE</span><b>${safe(r.angle_ordre ?? r.angle_real)}°</b></div></div>
      <div class="demo-summary-bottom"><span><b>${candidates.length}</b> candidats de panell</span><span><b>${prefs.length}</b> preferències</span><span><b>${imp.length}</b> impasses</span><span><b>${rules.length}</b> activacions de regles · 3 sectors</span></div>
    </div>
    <nav class="demo-phase-nav" aria-label="Fases del raonament"><a href="#demo-perception">01 Percepció</a><a href="#demo-risk">02 Elaboració</a><a href="#demo-operators">03 Proposta</a><a href="#demo-evaluation">04 Avaluació</a><a href="#demo-result">05 Selecció</a><a href="#demo-irrigation">06 Reg</a><a href="#demo-monitor">07 Control</a></nav>
    <div class="demo-section-label"><span>CADENA DE RAONAMENT</span><span>Fets i decisions del cicle seleccionat</span></div>
    <div class="demo-panels">
      ${dataCard('demo-perception','01','Percepció','Lectures originals del sector',obsHtml,'◉')}
      ${dataCard('demo-risk','02','Elaboració','Predicció i valoració de riscos',riskHtml,'◈')}
      ${dataCard('demo-operators','03','Proposta','Alternatives creades per les regles CLIPS',candidateRows || '<p class="demo-soft">No s’han capturat candidats en aquest cicle.</p>','◇')}
      ${dataCard('demo-evaluation','04','Avaluació','Preferències explícites i fonts de decisió',prefsHtml,'≋')}
      ${dataCard('demo-result','05','Deliberació i selecció',imp.length ? 'Hi ha impasses registrats' : 'Cicle sense impasse registrat',`<div class="demo-result-grid"><div><span>IMPASSES</span>${imp.length ? tags(imp,'risk') : '<strong class="demo-ok">Cap impasse</strong>'}</div><div><span>SELECCIÓ DEL MOTOR</span>${json(d.seleccio)}</div><div><span>ORDRE EMESA</span>${json(d.ordre)}</div></div><details class="demo-native-details"><summary>Explicació original CLIPS</summary>${json(d.explicacio)}</details>`,'◎')}
      ${dataCard('demo-irrigation','06','Actuador de reg','Candidats, preferències i ordre de reg',regHtml,'≈')}
      ${dataCard('demo-monitor','07','Monitoratge i seguretat','Estat final i invariants del cicle',`<div class="demo-monitor-grid"><div><small>Invariants vulnerats</small><strong class="${invalid.length ? 'demo-bad' : 'demo-ok'}">${invalid.length ? safe(invalid.length) : '0 · Sense violacions'}</strong></div><div><small>Fase final</small><strong>${safe(d.fase_final)}</strong></div><div><small>Regles disparades al cicle</small><strong>${safe(d.regles_total ?? rules.length)}</strong></div></div>${invalid.length ? json(invalid) : ''}`,'✓')}
    </div>
    <details class="demo-rules"><summary><span><b>Traça tècnica completa</b><small>Regles disparades durant el cicle global · inclou els tres sectors, no només el seleccionat</small></span><span class="demo-rule-count">${rules.length} activacions <span class="demo-chevron">⌄</span></span></summary><div class="demo-rules-body"><div class="demo-rules-notice">L’ordre d’aquesta llista reflecteix la traça del motor. No s’atribueix automàticament cada regla al sector seleccionat.</div>${rules.length ? `<ol class="demo-rule-lines">${rules.map((name,i)=>`<li><span>${String(i+1).padStart(3,'0')}</span><code>${safe(name)}</code></li>`).join('')}</ol>` : '<p class="demo-soft">No hi ha noms de regles disponibles.</p>'}</div></details>
    <div class="demo-disclaimer"><span aria-hidden="true">ⓘ</span><p>Les dades provenen de les estructures del motor CLIPS capturades per la integració Python. Els elements visuals agrupen aquesta evidència; no calculen ni alteren les decisions. Les regles disparades corresponen al cicle complet.</p></div>`;
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
  defenseSelected = -1;
  trace.rows.forEach((tr) => {
    tr.tabIndex = 0;
    tr.setAttribute('aria-label', `Inspeccionar decisió del sector ${sectorLabel(recs[Number(tr.dataset.i)].sector)} a les ${clock(recs[Number(tr.dataset.i)].hora)}`);
    const inspect = () => {
      stopPlayback();
      trace.rows.forEach(row => { row.classList.remove('demo-inspected'); row.removeAttribute('aria-current'); });
      tr.classList.add('demo-inspected'); tr.setAttribute('aria-current', 'true');
      defenseSelected = Number(tr.dataset.i);
      renderPosition(Number(tr.dataset.c)); renderDemoDetail(recs[Number(tr.dataset.i)]);
      updateDefenseGuide();
      $('demoInspector').scrollIntoView({behavior:'smooth',block:'start'});
    };
    tr.addEventListener('click', inspect);
    tr.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inspect(); } });
  });
  $('demoDetails').innerHTML = '<div class="demo-empty"><span aria-hidden="true">◈</span><h4>Selecciona una decisió</h4><p>Prem una fila de traçabilitat per explorar la seva cadena de raonament.</p></div>';
  applyTraceFilter();
  updateDefenseGuide();
  if ($('demoMode').checked && state.controller === 'soar' && trace.rows.length) {
    const best = trace.rows.find(tr => state.run.records[Number(tr.dataset.i)]?.impas)
      || trace.rows.find(tr => actionCategory(state.run.records[Number(tr.dataset.i)]?.accio) === 'safety')
      || trace.rows[0];
    best.click();
  }
}

function applyTraceFilter() {
  const sec = $('sectorFilter').value;
  const only = $('onlyIncidents').checked;
  let shown = 0;
  trace.rows.forEach((tr) => {
    const rec = state.run?.records?.[Number(tr.dataset.i)];
    const kindOk = defenseFilter === 'all'
      || (defenseFilter === 'safety' && actionCategory(rec?.accio) === 'safety')
      || (defenseFilter === 'impasse' && Boolean(rec?.impas))
      || (defenseFilter === 'irrigation' && Number(rec?.reg_mm) > 0.05);
    const ok = kindOk && (sec === 'all' || tr.dataset.s === sec) && (!only || tr.dataset.inc === '1');
    tr.hidden = !ok;
    if (ok) shown += 1;
  });
  $('traceCount').textContent = `${shown} de ${trace.rows.length} registres`;
  $('defenseFilterCount').textContent = shown ? `${shown} casos` : 'Cap cas; prova un altre filtre';
  updateDefenseGuide();
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
/* ================= Escenari, abast i durada ================= */
const MOD_IDS = { temp_delta: 'modTemp', vent_factor: 'modWind', rad_factor: 'modRad', pluja_factor: 'modRain' };
const MOD_DEFAULT = { temp_delta: 0, vent_factor: 1, rad_factor: 1, pluja_factor: 1 };

function setModifiers(m = {}) { Object.entries(MOD_IDS).forEach(([k, id]) => { $(id).value = m[k] ?? MOD_DEFAULT[k]; }); }
function readModifiers() {
  const out = {};
  Object.entries(MOD_IDS).forEach(([k, id]) => { const v = Number($(id).value); out[k] = Number.isFinite(v) ? v : MOD_DEFAULT[k]; });
  return out;
}

function currentDays() {
  if (state.scope === 'day' || state.days.length < 2) return $('day').value ? [$('day').value] : [];
  let a = $('rangeFrom').value; let b = $('rangeTo').value;
  if (a > b) [a, b] = [b, a];
  return state.days.filter((d) => d >= a && d <= b);
}

function effectiveMode(days) {
  if (days.length < 2) return 'independents';
  return $('mode').value || state.sc?.mode || 'independents';
}

function updateMeta() {
  const sc = state.sc;
  if (!sc) return;
  const days = currentDays();
  const mode = effectiveMode(days);
  const nCtl = $('compare').checked ? 3 : 1;
  const mods = readModifiers();
  const names = { temp_delta: 'T', vent_factor: 'vent ×', rad_factor: 'radiació ×', pluja_factor: 'pluja ×' };
  const changed = Object.entries(mods).filter(([k, v]) => v !== MOD_DEFAULT[k]);
  const dur = fmtDuration(days.length) + (days.length !== sc.days ? ` de ${fmtInt(sc.days)}` : '');
  const chips = [`<li>${icon('pin')}${esc(sc.location_name)}</li>`, `<li class="strong">${icon('calendar')}${esc(dur)}</li>`];
  if (days.length) chips.push(`<li>${days.length > 1 ? `${esc(fmtDate(days[0]))} – ${esc(fmtDate(days[days.length - 1]))}` : esc(fmtDate(days[0]))}</li>`);
  if (days.length > 1) chips.push(`<li title="${esc(MODE_HINT[mode])}">${esc(MODE_LABEL[mode])}</li>`);
  if (changed.length) chips.push(`<li class="warn">what-if: ${esc(changed.map(([k, v]) => `${names[k]}${v}`).join(', '))}</li>`);
  $('scenarioMeta').innerHTML = chips.join('');
  const perf = state.boot?.perf;
  const est = estimateSeconds(perf, days, nCtl, mode);
  $('scenarioEstimate').innerHTML = days.length > 1 && est !== null
    ? `Temps estimat <b>≈ ${esc(fmtSeconds(est))}</b> <small>${nCtl > 1 ? '3 controladors · ' : ''}${perf.workers} ${perf.workers === 1 ? 'procés' : 'processos'}</small>`
    : 'Resultat immediat';
  $('modeHint').textContent = MODE_HINT[$('mode').value || sc.mode] || '';
  if (sc.description) $('scenario').title = sc.description;
}

function setScope(scope) {
  state.scope = scope;
  const multi = state.days.length > 1;
  $('scope').hidden = !multi;
  $('scope').querySelectorAll('button').forEach((b) => b.classList.toggle('active', b.dataset.scope === scope));
  $('rangeField').hidden = !(multi && scope === 'period');
  $('dayField').hidden = multi && scope === 'period';
  updateMeta();
}

async function loadScenario() {
  const id = $('scenario').value;
  const sc = state.boot.scenarios.find((x) => x.id === id);
  state.sc = sc || null;
  const d = await api(`/api/days?scenario=${encodeURIComponent(id)}`);
  state.days = d.days;
  const opts = (sel, withDow) => { sel.innerHTML = ''; d.days.forEach((x) => sel.add(new Option(withDow ? x : fmtDate(x), x))); };
  opts($('day'), true); opts($('rangeFrom'), false); opts($('rangeTo'), false);
  if (d.days.length) {
    $('day').value = d.days[Math.floor(d.days.length / 2)];
    $('rangeFrom').value = d.days[0];
    $('rangeTo').value = d.days[d.days.length - 1];
  }
  $('mode').value = '';
  $('soilInit').value = '';
  setModifiers(sc?.modifiers);
  setScope(d.days.length > 1 ? 'period' : 'day');
}

function buildPayload() {
  return {
    scenario: $('scenario').value, controller: state.controller, compare: $('compare').checked,
    seed: Number($('seed').value || 0), mode: $('mode').value || null, soil_init: $('soilInit').value || null,
    demo: $('demoMode').checked,
    modifiers: readModifiers(),
  };
}

/* ================= Execució ================= */
function setBusy(on, period = false) {
  state.busy = on;
  $('progress').hidden = !on;
  $('progress').classList.toggle('det', on && period);
  $('emptyRun').disabled = on;
  const b = $('runButton');
  b.disabled = on && !period;
  b.textContent = on ? (period ? 'Atura' : 'Executant…') : 'Executar simulació';
  b.classList.toggle('busy', on);
  b.classList.toggle('cancel', on && period);
}

function sectorsFrom(records) {
  const seen = new Map();
  records.forEach((r) => { if (!seen.has(r.sector)) seen.set(r.sector, { id: r.sector, crop: r.cultiu }); });
  return [...seen.values()].sort((a, b) => a.id.localeCompare(b.id));
}

function applyRun(run, runs, { play = true, keepSelection = false } = {}) {
  const prevSel = keepSelection ? state.selected : null;
  state.runs = runs; state.run = run;
  state.frames = groupFrames(run.records);
  state.sectors = sectorsFrom(run.records);
  state.irrCycles = state.frames.map((f) => [...f.records.values()].some((r) => Number(r.reg_mm) > 0.05));
  state.selected = null;
  twin?.setSelected(null);

  $('sceneEmpty').hidden = true;
  $('play3d').disabled = false; $('reset3d').disabled = false;
  buildCards();
  ribbon.setData({ frames: state.frames, sectors: state.sectors });
  renderBalance(run);
  renderComparison(runs);
  buildCharts(run);
  buildTrace(run);
  renderPosition(0);
  updateDefenseGuide();
  if (prevSel && cards.has(prevSel)) {          // en canviar de dia es manté el sector seguit
    state.selected = prevSel;
    cards.get(prevSel).el.classList.add('selected');
    cards.get(prevSel).el.setAttribute('aria-pressed', 'true');
    twin?.setSelected(prevSel);
  }
  if (play) startPlayback();
}

async function runDay() {
  const payload = { ...buildPayload(), day: currentDays()[0] };
  if (!payload.soil_init) delete payload.soil_init;      // un dia: valor de configuració, com sempre
  const data = await api('/api/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  renderOntology(data.ontology);
  teardownPeriod();
  history.replaceState(null, '', location.pathname);
  const primary = data.runs.find((r) => r.controller === payload.controller) || data.runs[0];
  applyRun(primary, data.runs, {play: !payload.demo});
  if (payload.demo && payload.controller === "soar") { stopPlayback(); setTab("trace"); $("panel-trace").scrollIntoView({behavior:"smooth",block:"start"}); }
}

async function run() {
  hideError(); stopPlayback();
  const days = currentDays();
  if (!days.length) { showError('Tria un dia o un rang de dates amb dades.'); return; }
  if (days.length > 1) { await runPeriod(days); return; }
  setBusy(true);
  try { await runDay(); } catch (err) { showError(err.message || String(err)); } finally { setBusy(false); }
}

/* ================= Laboratori de casos CLIPS CP05 / CP06 ================= */
let impasseLoadSerial = 0;
function renderImpasseLab(result) {
  const host = $('impasseLabResult');
  const code = (v) => esc(String(v ?? '—'));
  const verdict = result.ok ? 'Cas superat' : 'Hi ha discrepàncies';
  const cards = result.cicles.map((c) => {
    const imp = c.impasse ? `<span class="impasse-state found">IMPASSE: ${code(c.impasse)}</span>` : '<span class="impasse-state resolved">Sense impasse en aquest cicle</span>';
    const obs = Object.entries(c.observacions).map(([k,v])=>`<div><dt>${code(k.replaceAll('-',' '))}</dt><dd>${code(v)}</dd></div>`).join('');
    const risks = (c.riscos || []).map(r=>`<span class="impasse-pill">${code(r[0])}: ${code(r[1])}</span>`).join('') || '<span class="impasse-muted">Sense riscos</span>';
    const selected = c.seleccio?.[0]?.[0] || c.ordres?.[0]?.[0] || '—';
    const candidates = (c.candidats || []).map(x=>`<div class="impasse-choice ${x.operador === selected ? 'chosen' : ''}"><b>${code(x.operador)}</b><small>${code(x.estat)}</small>${x.operador === selected ? '<em>SELECCIONAT</em>' : ''}${(c.rebutjats||[]).includes(x.operador) ? '<em>REBUTJAT</em>' : ''}</div>`).join('') || '<p class="impasse-muted">No es registren candidats</p>';
    const sources = (c.fonts_preferencia || []).map(x=>`<span class="impasse-pill">${code(x.join(' · '))}</span>`).join('') || '<span class="impasse-muted">Sense fonts registrades</span>';
    const chunks = c.chunks_nous.length ? c.chunks_nous.map(x=>x.join(' · ')).join(', ') : 'Cap chunk nou';
    const verdictText = c.correcte ? '✓ Verificat' : `⚠ ${(c.discrepancies||[]).map(code).join(' · ') || 'Resultat no verificat'}`;
    return `<article class="impasse-cycle"><header><span class="impasse-cycle-number">CICLE ${c.numero}</span>${imp}<span class="impasse-cycle-ok ${c.correcte?'':'bad'}">${verdictText}</span></header>
    <div class="impasse-cycle-head"><div><small>Operador seleccionat</small><h4>${code(selected)}</h4><p>${code(c.explicacio || c.seleccio?.[0]?.[1] || 'Sense explicació')}</p></div><div><small>Chunking</small><strong>${c.chunk_utilitzat ? 'Chunk reutilitzat' : chunks !== 'Cap chunk nou' ? 'Chunk creat' : 'Sense reutilització'}</strong><p>${code(chunks)}</p></div></div>
    <div class="impasse-subgrid"><section><h5>01 · Observacions</h5><dl>${obs}</dl><h5>Riscos elaborats</h5><div class="impasse-pill-group">${risks}</div></section><section><h5>02 · Operadors candidats</h5><div class="impasse-choices">${candidates}</div></section><section><h5>03 · Fonts de preferència</h5><div class="impasse-pill-group">${sources}</div><h5>04 · Decisió i aplicació</h5><p>${code(JSON.stringify(c.ordres))}</p></section></div>
    <details class="impasse-technical"><summary>Traça CLIPS original · ${c.regles_disparades} activacions · fase ${code(c.fase_final)}</summary><pre>${code(c.traca_clips || 'Sense sortida del motor')}</pre></details></article>`;
  }).join('');
  host.innerHTML = `<div class="impasse-result-head"><div><span class="demo-overline">${code(result.id)} · EXECUCIÓ AÏLLADA</span><h4>${code(result.titol)}</h4><p>${code(result.objectiu)}</p></div><span class="impasse-result-status ${result.ok ? 'ok':'bad'}">${verdict}</span></div><div class="impasse-cycle-grid">${cards}</div><p class="impasse-source">Font de les entrades i de les expectatives: <code>${code(result.font)}</code>. Les dades mostrades són de l'execució actual del motor, no d'una traça pregravada.</p>`;
}
async function runImpasseCase(caseId) {
  const host = $('impasseLabResult');
  const serial = ++impasseLoadSerial;
  document.querySelectorAll('[data-impasse-case]').forEach(b=>{b.disabled=true;b.classList.toggle('selected',b.dataset.impasseCase===caseId)});
  host.innerHTML = `<div class="impasse-working"><span class="impasse-spinner"></span>Executant ${esc(caseId)} amb el motor CLIPS…</div>`;
  try {
    const result = await api(`/api/defensa/impasses/${encodeURIComponent(caseId)}`);
    if (serial === impasseLoadSerial) renderImpasseLab(result);
  } catch(err) {
    if (serial === impasseLoadSerial) host.innerHTML = `<p class="impasse-error">No s'ha pogut executar ${esc(caseId)}: ${esc(err.message || String(err))}</p>`;
  } finally {
    if (serial === impasseLoadSerial) document.querySelectorAll('[data-impasse-case]').forEach(b=>b.disabled=false);
  }
}

/* ================ Mode Defensa: guia de presentació ================ */
function updateDefenseGuide() {
  const enabled = $('demoMode').checked;
  const valid = Boolean(state.run && state.controller === 'soar' && state.run.records?.some(r => r.demo));
  $('defenseModeStatus').textContent = enabled ? (valid ? '● Traça CLIPS disponible' : '◉ Preparat per capturar') : '○ Mode inactiu';
  $('defenseModeStatus').classList.toggle('is-ready', valid);
  $('demoLaunch').classList.toggle('is-active', enabled);
  $('defenseRun').textContent = enabled ? 'Tornar a executar amb traça' : 'Activar i executar';
  if (defenseSelected >= 0 && state.run?.records?.[defenseSelected]) {
    const r = state.run.records[defenseSelected];
    $('defenseGuideText').textContent = `${sectorLabel(r.sector)} · ${clock(r.hora)} · ${actionLabel(r.accio)}. Segueix les set fases i obre les regles disparades al final.`;
  } else {
    $('defenseGuideText').textContent = enabled ? 'Executa un dia amb SOAR; després selecciona una fila per veure els fets, candidats, preferències i regles.' : 'Activa el Mode Defensa, executa un dia amb SOAR i inspecciona una decisió real.';
  }
  $('defensePrev').disabled = !trace.rows.some(tr => !tr.hidden && Number(tr.dataset.i) < defenseSelected);
  $('defenseNext').disabled = !trace.rows.some(tr => !tr.hidden && Number(tr.dataset.i) > defenseSelected);
  $('defenseCopy').disabled = defenseSelected < 0;
}
function navigateDefense(delta) {
  const visible = trace.rows.filter(tr => !tr.hidden);
  if (!visible.length) return;
  const pos = visible.findIndex(tr => Number(tr.dataset.i) === defenseSelected);
  const next = visible[Math.min(visible.length-1,Math.max(0,pos+delta))];
  next?.click();
}
function activateDefense() {
  if (state.busy) return;
  $('demoMode').checked = true;
  state.controller = 'soar';
  document.querySelectorAll('#controller button').forEach(btn => {
    const active = btn.dataset.id === 'soar';
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-checked', String(active));
  });
  if (state.scope !== 'day') setScope('day');
  $('advanced').open = false;
  updateDefenseGuide();
  run();
}
function copyDefenseSummary() {
  const r = state.run?.records?.[defenseSelected];
  if (!r) return;
  const d = r.demo || {};
  const body = [
    'DEMOSTRACIÓ SOAR–CLIPS',
    `Sector: ${sectorLabel(r.sector)} · Hora: ${clock(r.hora)}`,
    `Acció: ${actionLabel(r.accio)}`,
    `Motiu: ${prettyReason(r.motiu)}`,
    `Candidats: ${JSON.stringify(d.candidats || [])}`,
    `Preferències: ${JSON.stringify(d.preferencies || [])}`,
    `Impasses: ${JSON.stringify(d.impasses || [])}`,
    `Selecció: ${JSON.stringify(d.seleccio || [])}`,
    `Regles de tot el cicle: ${JSON.stringify(d.regles_disparades || [])}`
  ].join('\n');
  navigator.clipboard?.writeText(body).then(() => {
    $('defenseCopy').textContent = '✓ Copiat';
  }).catch(() => {
    const blob = new Blob([body],{type:'text/plain'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download='traca-clips.txt';a.click();URL.revokeObjectURL(url);
  });
}

/* ================= Períodes llargs ================= */
function updateJobCard(st) {
  $('jobCard').hidden = false;
  const pct = Math.round((st.fraction || 0) * 100);
  $('jobTitle').textContent = `Simulant ${fmtDuration(st.total_days)}`;
  $('jobSub').textContent = `Dia ${st.done_days} de ${st.total_days} · ${pct} % · ${fmtSeconds(st.elapsed_s)} · queden ≈ ${fmtSeconds(st.eta_s)}`;
  $('jobBar').style.width = `${pct}%`;
  $('progress').style.setProperty('--p', `${pct}%`);
  $('jobCtl').innerHTML = st.controllers.length > 1
    ? st.controllers.map((c) => `<li><span>${esc(CONTROLLER_SHORT[c] || c)}</span><span class="job-bar mini"><i style="width:${Math.round(((st.done_by_controller[c] || 0) / st.total_days) * 100)}%"></i></span></li>`).join('')
    : '';
  $('jobNote').textContent = `${MODE_LABEL[st.mode] || st.mode} · ${st.tasks} ${st.tasks === 1 ? 'tasca' : 'tasques'} en ${st.workers} ${st.workers === 1 ? 'procés' : 'processos'}`;
}

async function cancelPeriod() {
  state.abort = true;
  if (state.job) await cancelJob(state.job);
}

async function runPeriod(days) {
  setBusy(true, true);
  state.abort = false;
  $('sceneEmpty').hidden = true;
  try {
    const payload = { ...buildPayload(), start: days[0], end: days[days.length - 1] };
    const st0 = await startJob(payload);
    state.job = st0.id;
    updateJobCard(st0);
    const st = await waitForJob(st0.id, updateJobCard, () => state.abort);
    if (st.state === 'cancelled' || state.abort) return;
    if (st.state === 'error') throw new Error(st.error || 'La simulació ha fallat');
    const result = await jobResult(st0.id);
    setupPeriod(result, payload.controller);
    history.replaceState(null, '', `?job=${result.id}`);
    await showDay(0, { play: true });
    setTab('period');
  } catch (err) {
    showError(err.message || String(err));
  } finally {
    state.job = null;
    $('jobCard').hidden = true;
    setBusy(false);
    if (!state.frames.length) $('sceneEmpty').hidden = false;
  }
}

/* Reobre un període ja simulat (?job=<id>): permet recarregar la pàgina o compartir l'enllaç mentre el servidor està en marxa. */
async function openJobFromUrl() {
  const id = new URLSearchParams(location.search).get('job');
  if (!id) return;
  try {
    const result = await jobResult(id);
    const sid = result.scenario?.id;
    if (sid && [...$('scenario').options].some((o) => o.value === sid)) { $('scenario').value = sid; await loadScenario(); }
    setupPeriod(result, result.controllers[0]);
    await showDay(0, { play: false });
    setTab('period');
  } catch (err) {
    history.replaceState(null, '', location.pathname);      // el treball ja no existeix al servidor
  }
}

function setupPeriod(result, preferred) {
  const ctrl = result.controllers.includes(preferred) ? preferred : result.controllers[0];
  state.period = { id: result.id, result, controller: ctrl, index: 0, cache: new Map() };
  state.runs = [];
  periodView ??= new PeriodView($('periodView'), {
    onPickDay: (i, ctl) => pickDay(i, ctl), onMetric: (m) => setMetric(m), ledgerHTML, comparisonHTML,
  });
  dayStrip ??= new DayStrip($('periodStrip'), { onPick: (i, final) => showDay(i, { play: final }) });
  periodView.setData(result, ctrl, state.metric);
  dayStrip.setData(result.daily[ctrl], state.metric);
  ['periodStrip', 'dayNav', 'autoNextWrap', 'tab-period'].forEach((id) => { $(id).hidden = false; });
}

function teardownPeriod() {
  if (!state.period) return;
  state.period = null;
  periodView?.destroy();
  $('periodView').innerHTML = '';
  ['periodStrip', 'dayNav', 'autoNextWrap', 'tab-period'].forEach((id) => { $(id).hidden = true; });
  if (state.tab === 'period') setTab('balance');
}

function setMetric(m) {
  state.metric = m;
  periodView?.setMetric(m);
  if (state.period) dayStrip.setData(state.period.result.daily[state.period.controller], m);
  if (state.period) dayStrip.setSelected(state.period.index);
}

function pickDay(i, ctl) {
  const p = state.period;
  if (!p) return;
  if (ctl && ctl !== p.controller) {
    p.controller = ctl;
    periodView.setData(p.result, ctl, state.metric);
    dayStrip.setData(p.result.daily[ctl], state.metric);
  }
  showDay(i, { play: true });
}

function updateDayNav() {
  const p = state.period;
  const n = p.result.days.length;
  $('dayDate').textContent = `${fmtDate(p.result.days[p.index])} · ${p.index + 1}/${n}`;
  $('dayPrev').disabled = p.index <= 0;
  $('dayNext').disabled = p.index >= n - 1;
}

async function prefetchDay(j) {
  const p = state.period;
  if (!p || j < 0 || j >= p.result.days.length) return;
  const key = `${p.controller}|${p.result.days[j]}`;
  if (p.cache.has(key)) return;
  try { p.cache.set(key, await jobDay(p.id, p.result.days[j], p.controller)); } catch (e) { /* es tornarà a demanar */ }
}

async function showDay(i, { play = true } = {}) {
  const p = state.period;
  if (!p) return;
  const n = p.result.days.length;
  i = clamp(i, 0, n - 1);
  const day = p.result.days[i];
  const key = `${p.controller}|${day}`;
  const token = ++state.loadToken;
  let r = p.cache.get(key);
  if (!r) {
    try { r = await jobDay(p.id, day, p.controller); } catch (err) { showError(err.message); return; }
    p.cache.set(key, r);
    if (p.cache.size > 60) p.cache.delete(p.cache.keys().next().value);
  }
  if (token !== state.loadToken) return;     // s'ha demanat un altre dia mentre es carregava
  stopPlayback();
  p.index = i;
  applyRun(r, [r], { play, keepSelection: true });
  updateDayNav();
  periodView.setSelected(i);
  dayStrip.setSelected(i);
  prefetchDay(i + 1); prefetchDay(i - 1);
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
  if (name === 'period') requestAnimationFrame(() => periodView?.charts.forEach((c) => c.draw()));
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
  $('scenario').addEventListener('change', () => loadScenario().catch((e) => showError(e.message)));
  $('runButton').addEventListener('click', () => (state.busy && state.job ? cancelPeriod() : run()));
  $('demoLaunch').addEventListener('click', activateDefense);
  $('defenseRun').addEventListener('click', activateDefense);
  $('demoMode').addEventListener('change', updateDefenseGuide);
  $('defensePrev').addEventListener('click', () => navigateDefense(-1));
  $('defenseNext').addEventListener('click', () => navigateDefense(1));
  $('defenseCopy').addEventListener('click', copyDefenseSummary);
  document.querySelectorAll('[data-demo-filter]').forEach(btn => btn.addEventListener('click', () => {
    defenseFilter = btn.dataset.demoFilter;
    document.querySelectorAll('[data-demo-filter]').forEach(b=>b.classList.toggle('active',b===btn));
    applyTraceFilter(); updateDefenseGuide();
  }));
  $('emptyRun').addEventListener('click', run);
  $('jobCancel').addEventListener('click', cancelPeriod);

  /* abast, rang, mode i what-if: tot actualitza la durada i el temps estimat */
  $('scope').querySelectorAll('button').forEach((b) => b.addEventListener('click', () => setScope(b.dataset.scope)));
  ['rangeFrom', 'rangeTo', 'day', 'mode', 'compare', 'modTemp', 'modWind', 'modRad', 'modRain'].forEach((id) => $(id).addEventListener('input', updateMeta));
  $('modReset').addEventListener('click', () => { setModifiers(state.sc?.modifiers); updateMeta(); });
  $('dayPrev').innerHTML = icon('left');
  $('dayNext').innerHTML = icon('chevron');
  $('dayPrev').addEventListener('click', () => state.period && showDay(state.period.index - 1));
  $('dayNext').addEventListener('click', () => state.period && showDay(state.period.index + 1));
  $('dayDate').addEventListener('click', () => { stopPlayback(); renderPosition(0); });
  document.addEventListener('click', (e) => { const adv = $('advanced'); if (adv.open && !adv.contains(e.target)) adv.open = false; });
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
      const vis = tabs.filter((x) => !x.hidden);
      const n = vis[(vis.indexOf(t) + d + vis.length) % vis.length];
      n.focus(); setTab(n.dataset.tab);
    });
  });

  $('sectorFilter').addEventListener('change', applyTraceFilter);
  $('onlyIncidents').addEventListener('change', applyTraceFilter);

  window.addEventListener('keydown', (e) => {
    if (state.period && (e.key === '[' || e.key === ']') && !/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)) {
      showDay(state.period.index + (e.key === ']' ? 1 : -1));
      return;
    }
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
  $('catalogLaunch').addEventListener('click', () => { setTab('catalog'); $('panel-catalog').scrollIntoView({behavior:'smooth',block:'start'}); });
  initCatalog();
  try {
    twin = new DigitalTwin3D($('scene3d'), $('sceneTooltip'));
    twin.onPick = (id) => selectSector(id && id !== state.selected ? id : null);
  } catch (err) {
    $('sceneLoading').textContent = 'WebGL no està disponible en aquest navegador.';
    showError(`No s'ha pogut inicialitzar el 3D: ${err.message || err}`);
  }
  try {
    state.boot = await api('/api/bootstrap');
    fillScenarioSelect($('scenario'), state.boot.scenarios);
    if (state.boot.scenarios.some((s) => s.id === 'dia_normal.json')) $('scenario').value = 'dia_normal.json';
    buildControllers(state.boot.controllers);
    renderOntology(state.boot.ontology);
    await loadScenario();
    await openJobFromUrl();
  } catch (err) {
    $('statusText').textContent = 'Sense connexió amb el backend';
    $('systemStatus').classList.add('bad');
    showError(`No s'ha pogut carregar la configuració: ${err.message || err}`);
  }
}

init();
