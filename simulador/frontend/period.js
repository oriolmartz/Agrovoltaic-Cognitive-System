/* Vista de periode llarg (mesos): calendari, tira de dies, evolució diària, resum per mesos i
   experiment (SOAR davant de les referències amb estadística aparellada).

   Tot el que viatja al navegador és la taula DIÀRIA; els registres horaris d'un dia es demanen
   quan es clica aquell dia (webjobs.day_payload). Per això escala amb el nombre de dies.
*/
import { LineChart } from './charts.js';
import {
  esc, fmt, fmtInt, fmtDate, fmtDateShort, fmtDuration, fmtSeconds, monthKey, monthLabel, monthShort,
  icon, CONTROLLER_LONG, MODE_LABEL,
} from './ui.js';

export const METRICS = [
  { id: 'efficiency_pct', label: 'Eficiència', unit: '%', tone: 'sun', digits: 1 },
  { id: 'energy_kwh', label: 'Producció', unit: 'kWh', tone: 'sun', digits: 0 },
  { id: 'rain_mm', label: 'Pluja', unit: 'mm', tone: 'water', digits: 1 },
  { id: 'irrigation_mm_avg', label: 'Reg', unit: 'mm', tone: 'water', digits: 1 },
  { id: 'soil_mean', label: 'Humitat del sòl', unit: '%', tone: 'shade', digits: 0 },
  { id: 'wind_max', label: 'Vent màxim', unit: 'm/s', tone: 'safe', digits: 1 },
  { id: 'temp_max', label: 'Temp. màxima', unit: '°C', tone: 'risk', digits: 1 },
  { id: 'water_stress_h', label: 'Estrès hídric', unit: 'sector·h', tone: 'risk', digits: 0 },
  { id: 'safety_violations', label: 'Violacions', unit: '', tone: 'risk', digits: 0 },
  { id: 'rules_per_cycle', label: 'Regles/cicle', unit: '', tone: 'shade', digits: 0 },
];
const metricOf = (id) => METRICS.find((m) => m.id === id) || METRICS[0];

const CTRL_STYLE = {
  soar: { color: 'var(--sun)', dashed: false },
  seguidor: { color: 'var(--tx-2)', dashed: true },
  fix: { color: 'var(--tx-3)', dashed: true },
};

const MOD_NAME = { temp_delta: ['T', 0], vent_factor: ['vent ×', 1], rad_factor: ['radiació ×', 1], pluja_factor: ['pluja ×', 1] };
const whatIf = (m = {}) => Object.entries(m).filter(([k, v]) => MOD_NAME[k] && Number(v) !== MOD_NAME[k][1]).map(([k, v]) => `${MOD_NAME[k][0]}${v}`).join(', ');

const sum = (rows, k) => rows.reduce((s, r) => s + (Number(r[k]) || 0), 0);
const avg = (rows, k) => (rows.length ? sum(rows, k) / rows.length : 0);

/* ---------- Dies destacats ---------- */
export function highlights(daily) {
  const defs = [
    ['Dia més ventós', 'wind_max', 'max', (v) => `${fmt(v, 1)} m/s`, () => true],
    ['Dia més plujós', 'rain_mm', 'max', (v) => `${fmt(v, 1)} mm`, (v) => v > 0],
    ['Dia amb més reg', 'irrigation_mm_avg', 'max', (v) => `${fmt(v, 1)} mm`, (v) => v > 0],
    ['Sòl més sec', 'soil_min', 'min', (v) => `${fmt(v, 0)} %`, () => true],
    ['Dia més calorós', 'temp_max', 'max', (v) => `${fmt(v, 1)} °C`, () => true],
    ['Pitjor estrès hídric', 'water_stress_h', 'max', (v) => `${fmtInt(v)} sector·h`, (v) => v > 0],
    ['Menys producció', 'energy_kwh', 'min', (v) => `${fmt(v, 0)} kWh`, () => true],
  ];
  return defs.map(([label, key, mode, f, ok]) => {
    let best = -1;
    daily.forEach((r, i) => {
      const v = Number(r[key]);
      if (!Number.isFinite(v)) return;
      if (best < 0 || (mode === 'max' ? v > Number(daily[best][key]) : v < Number(daily[best][key]))) best = i;
    });
    if (best < 0 || !ok(Number(daily[best][key]))) return null;
    return { label, index: best, value: f(Number(daily[best][key])), day: daily[best].day };
  }).filter(Boolean);
}

/* ---------- Resum per mesos ---------- */
export function monthlyRows(daily) {
  const m = new Map();
  daily.forEach((r) => { const k = monthKey(r.day); if (!m.has(k)) m.set(k, []); m.get(k).push(r); });
  const row = (key, rows) => ({
    key, days: rows.length,
    energy: sum(rows, 'energy_kwh'),
    eff: sum(rows, 'optimum_kwh') > 0 ? (100 * sum(rows, 'energy_kwh')) / sum(rows, 'optimum_kwh') : null,
    rain: sum(rows, 'rain_mm'), irr: sum(rows, 'irrigation_mm_avg'), m3: sum(rows, 'irrigation_m3'),
    soil: avg(rows, 'soil_mean'), stress: sum(rows, 'water_stress_h'),
    wind: Math.max(...rows.map((r) => Number(r.wind_max) || 0)), viol: sum(rows, 'safety_violations'),
  });
  return { months: [...m].map(([k, rows]) => row(k, rows)), total: row('total', daily) };
}

function monthStarts(days) {
  const out = []; let last = '';
  days.forEach((d, i) => { const k = monthKey(d); if (k !== last) { out.push({ x: i, label: monthShort(k) }); last = k; } });
  if (out.length >= 3 || days.length < 2) return out;
  // rangs curts (menys de 3 mesos): marques cada pocs dies amb la data
  const step = Math.max(1, Math.ceil(days.length / 8));
  return days.map((d, i) => ({ x: i, label: fmtDateShort(d) })).filter((t) => t.x % step === 0);
}

/* ================= Tira de dies (dins del dock) ================= */
export class DayStrip {
  constructor(host, { onPick }) {
    this.host = host;
    this.onPick = onPick;
    this.sel = 0;
    this.drag = false;
    this._t = 0;
    host.addEventListener('pointerdown', (e) => { this.drag = true; host.setPointerCapture?.(e.pointerId); this._pick(e, true); });
    host.addEventListener('pointermove', (e) => { if (this.drag) this._pick(e, false); });
    host.addEventListener('pointerup', (e) => { if (this.drag) { this.drag = false; this._pick(e, true); } });
    host.addEventListener('pointercancel', () => { this.drag = false; });
  }

  _index(e) {
    const b = this.host.querySelector('.strip-cells')?.getBoundingClientRect();
    if (!b || !this.n) return null;
    return Math.min(this.n - 1, Math.max(0, Math.floor(((e.clientX - b.left) / b.width) * this.n)));
  }

  _pick(e, final) {
    const i = this._index(e);
    if (i === null) return;
    const now = performance.now();
    if (!final && now - this._t < 140) return;     // arrossegar: no saturar el servidor
    this._t = now;
    this.onPick(i, final);
  }

  setData(daily, metricId) {
    this.daily = daily; this.n = daily.length;
    const m = metricOf(metricId);
    const vals = daily.map((r) => Number(r[m.id])).filter(Number.isFinite);
    const lo = Math.min(...vals); const hi = Math.max(...vals);
    this.host.className = `strip tone-${m.tone}`;
    this.host.innerHTML = `<div class="strip-cells" style="--n:${this.n}">${daily.map((r, i) => {
      const v = Number(r[m.id]); const t = hi > lo ? (v - lo) / (hi - lo) : 0;
      return `<i data-i="${i}" style="--t:${(Number.isFinite(t) ? t : 0).toFixed(3)}" title="${esc(fmtDate(r.day))} · ${esc(m.label)} ${fmt(v, m.digits)} ${esc(m.unit)}"></i>`;
    }).join('')}</div>
    <div class="strip-months">${monthStarts(daily.map((r) => r.day)).map((t) => `<span style="left:${(t.x / this.n) * 100}%">${esc(t.label)}</span>`).join('')}</div>`;
    this.setSelected(this.sel);
  }

  setSelected(i) {
    this.sel = i;
    this.host.querySelectorAll('i.on').forEach((el) => el.classList.remove('on'));
    this.host.querySelector(`i[data-i="${i}"]`)?.classList.add('on');
  }
}

/* ================= Pestanya "Període" ================= */
export class PeriodView {
  constructor(host, { onPickDay, onMetric, ledgerHTML, comparisonHTML }) {
    this.host = host;
    this.cb = { onPickDay, onMetric, ledgerHTML, comparisonHTML };
    this.charts = [];
    this.sel = 0;
    host.addEventListener('click', (e) => {
      const day = e.target.closest('[data-i]');
      if (day && day.matches('.cal-day, .hl-chip')) this.cb.onPickDay(Number(day.dataset.i));
      const met = e.target.closest('[data-metric]');
      if (met) this.cb.onMetric(met.dataset.metric);
    });
  }

  destroy() { this.charts.forEach((c) => c.destroy()); this.charts = []; }

  setData(result, controller, metric) {
    this.result = result; this.ctrl = controller; this.metric = metric;
    this.daily = result.daily[controller] || [];
    this.days = this.daily.map((r) => r.day);
    this.index = new Map(this.days.map((d, i) => [d, i]));
    this.render();
  }

  setMetric(metric) { this.metric = metric; this.renderMetrics(); this.renderCalendar(); }

  setSelected(i) {
    this.sel = i;
    this.host.querySelectorAll('.cal-day.sel').forEach((el) => el.classList.remove('sel'));
    this.host.querySelector(`.cal-day[data-i="${i}"]`)?.classList.add('sel');
    this.charts.forEach((c) => c.setPlayhead(i));
  }

  /* ----- estructura ----- */
  render() {
    this.destroy();
    const r = this.result; const k = r.kpis[this.ctrl]; const multi = r.controllers.length > 1;
    const sc = r.scenario;
    this.host.innerHTML = `
      <div class="per-head">
        <div>
          <h2>${esc(sc.name || 'Període')}</h2>
          <p>${esc(sc.location_name)} · ${icon('calendar')} <b>${fmtDuration(r.days.length)}</b> · ${esc(fmtDate(r.first_day))} – ${esc(fmtDate(r.last_day))}</p>
        </div>
        <ul class="per-meta">
          <li>${esc(MODE_LABEL[r.mode] || r.mode)}</li>
          <li>${r.soil_init === 'dades' ? 'Humitat inicial: mesura real' : 'Humitat inicial: configuració'}</li>
          ${whatIf(r.modifiers) ? `<li class="warn">what-if: ${esc(whatIf(r.modifiers))}</li>` : ''}
          <li>Simulat en ${esc(fmtSeconds(r.elapsed_s))}</li>
        </ul>
      </div>
      ${multi ? `<div class="per-ctl" role="group" aria-label="Controlador">${r.controllers.map((c) => `<button type="button" data-ctl="${c}" class="${c === this.ctrl ? 'active' : ''}">${esc(CONTROLLER_LONG[c] || c)}</button>`).join('')}</div>` : ''}
      ${this.cb.ledgerHTML(k, k.sector_hours)}
      <section class="per-sec"><h3 class="sub">Dies destacats <small>clic per veure’l en 3D</small></h3><div class="hl" id="perHl"></div></section>
      <section class="per-sec">
        <div class="per-sec-head"><h3 class="sub">Calendari</h3><div class="metric-chips" id="perMetrics"></div></div>
        <div class="cal" id="perCal"></div><div class="cal-legend" id="perCalLegend"></div>
      </section>
      <section class="per-sec"><h3 class="sub">Evolució diària <small>clic en un gràfic per anar a aquell dia</small></h3>
        <div class="chart-grid" id="perCharts">
          ${[['perC1', 'Producció diària'], ['perC2', 'Humitat del sòl, pluja i reg'], ['perC3', 'Vent i seguretat'], ['perC4', 'Estrès del cultiu'], ['perC5', 'Temperatura i radiació'], ['perC6', 'Aprenentatge i cost de CLIPS']]
    .map(([id, t]) => `<article class="chart-card"><h3>${t}</h3><div id="${id}"></div></article>`).join('')}
        </div></section>
      <section class="per-sec"><h3 class="sub">Resum per mesos</h3><div class="table-wrap short" id="perMonths"></div></section>
      ${multi ? '<section class="per-sec" id="perExp"></section>' : ''}`;
    this.host.querySelectorAll('[data-ctl]').forEach((b) => b.addEventListener('click', () => this.cb.onPickDay(this.sel, b.dataset.ctl)));
    this.renderHighlights();
    this.renderMetrics();
    this.renderCalendar();
    this.renderCharts();
    this.renderMonths();
    if (multi) this.renderExperiment();
    this.setSelected(this.sel);
  }

  renderHighlights() {
    this.host.querySelector('#perHl').innerHTML = highlights(this.daily).map((h) =>
      `<button type="button" class="hl-chip" data-i="${h.index}"><span>${esc(h.label)}</span><b>${esc(h.value)}</b><small>${esc(fmtDateShort(h.day))}</small></button>`).join('');
  }

  renderMetrics() {
    this.host.querySelector('#perMetrics').innerHTML = METRICS.map((m) =>
      `<button type="button" data-metric="${m.id}" class="${m.id === this.metric ? 'active' : ''}" aria-pressed="${m.id === this.metric}">${esc(m.label)}</button>`).join('');
  }

  dayTitle(i, m) {
    const r = this.daily[i];
    return `${fmtDate(r.day)} · ${m.label} ${fmt(r[m.id], m.digits)} ${m.unit} · pluja ${fmt(r.rain_mm, 1)} mm · vent màx ${fmt(r.wind_max, 1)} m/s · reg ${fmt(r.irrigation_mm_avg, 1)} mm`;
  }

  renderCalendar() {
    const m = metricOf(this.metric);
    const vals = this.daily.map((r) => Number(r[m.id])).filter(Number.isFinite);
    const lo = Math.min(...vals); const hi = Math.max(...vals);
    const months = [...new Set(this.days.map(monthKey))];
    const dow = ['Dl', 'Dt', 'Dc', 'Dj', 'Dv', 'Ds', 'Dg'];
    this.host.querySelector('#perCal').innerHTML = months.map((key) => {
      const [y, mo] = key.split('-').map(Number);
      const off = (new Date(y, mo - 1, 1).getDay() + 6) % 7;
      const dim = new Date(y, mo, 0).getDate();
      const cells = Array.from({ length: off }, () => '<i class="cal-pad"></i>');
      for (let d = 1; d <= dim; d += 1) {
        const iso = `${key}-${String(d).padStart(2, '0')}`;
        const i = this.index.get(iso);
        if (i === undefined) { cells.push(`<i class="cal-off">${d}</i>`); continue; }
        const v = Number(this.daily[i][m.id]);
        const t = hi > lo ? (v - lo) / (hi - lo) : 0;
        cells.push(`<button type="button" class="cal-day${i === this.sel ? ' sel' : ''}" data-i="${i}" style="--t:${(Number.isFinite(t) ? t : 0).toFixed(3)}" title="${esc(this.dayTitle(i, m))}"><span>${d}</span></button>`);
      }
      return `<div class="cal-month tone-${m.tone}"><h4>${esc(monthLabel(key))}</h4><div class="cal-dow">${dow.map((x) => `<b>${x}</b>`).join('')}</div><div class="cal-grid">${cells.join('')}</div></div>`;
    }).join('');
    this.host.querySelector('#perCalLegend').innerHTML = `<span>${fmt(lo, m.digits)}</span><i class="tone-${m.tone}"></i><span>${fmt(hi, m.digits)} ${esc(m.unit)}</span><em>${esc(m.label)} per dia</em>`;
  }

  /* ----- gràfics ----- */
  renderCharts() {
    const d = this.daily; const days = this.days;
    const mk = (id, opts, series) => {
      const c = new LineChart(this.host.querySelector(`#${id}`), {
        height: 210, xFormat: (x) => fmtDateShort(days[Math.round(x)]), xTicks: () => monthStarts(days),
        onSeek: (x) => this.cb.onPickDay(Math.round(x)), ...opts,
      });
      c.setSeries(series);
      this.charts.push(c);
      return c;
    };
    // 1. producció (tots els controladors)
    const energy = [];
    this.result.controllers.forEach((c) => {
      const st = CTRL_STYLE[c] || CTRL_STYLE.fix;
      energy.push({ name: CONTROLLER_LONG[c] || c, color: st.color, dashed: st.dashed, area: c === this.ctrl && this.result.controllers.length === 1,
        data: (this.result.daily[c] || []).map((r) => [this.index.get(r.day), Number(r.energy_kwh)]).filter((p) => p[0] !== undefined), unit: 'kWh', digits: 1, width: c === 'soar' ? 2.4 : 1.8 });
    });
    energy.push({ name: 'Òptim teòric', color: 'var(--tx-3)', dashed: true, data: d.map((r, i) => [i, Number(r.optimum_kwh)]), unit: 'kWh', digits: 1, width: 1.2 });
    mk('perC1', { y: { min: 0, digits: 0 }, label: 'Producció diària en kWh' }, energy);
    // 2. aigua
    mk('perC2', { y: { min: 0, max: 100, digits: 0 }, y2: { min: 0, digits: 0 }, label: 'Humitat del sòl, pluja i reg' }, [
      { name: 'Humitat mitjana (%)', color: 'var(--tx)', data: d.map((r, i) => [i, r.soil_mean]), unit: '%', digits: 0, width: 2 },
      { name: 'Humitat mínima (%)', color: 'var(--tx-3)', dashed: true, data: d.map((r, i) => [i, r.soil_min]), unit: '%', digits: 0, width: 1.4 },
      { name: 'Pluja (mm, eix dret)', color: 'var(--water)', type: 'bar', axis: 'y2', data: d.map((r, i) => [i, r.rain_mm]), unit: 'mm', digits: 1 },
      { name: 'Reg (mm/sector, eix dret)', color: 'var(--shade)', type: 'bar', axis: 'y2', data: d.map((r, i) => [i, r.irrigation_mm_avg]), unit: 'mm', digits: 1 },
    ]);
    // 3. vent
    mk('perC3', { y: { min: 0, digits: 0 }, y2: { min: 0, max: 14, digits: 0 }, label: 'Vent màxim i exposició' }, [
      { name: 'Vent màxim (m/s)', color: 'var(--safe)', area: true, data: d.map((r, i) => [i, r.wind_max]), unit: 'm/s', digits: 1 },
      { name: 'Hores exposades (eix dret)', color: 'var(--warn)', type: 'bar', axis: 'y2', data: d.map((r, i) => [i, r.wind_exposure_h]), unit: 'h', digits: 0 },
    ]);
    // 4. estrès
    mk('perC4', { y: { min: 0, digits: 0 }, label: 'Estrès del cultiu' }, [
      { name: 'Hídric', color: 'var(--water)', data: d.map((r, i) => [i, r.water_stress_h]), unit: 'sector·h', digits: 0, width: 1.8 },
      { name: 'Tèrmic', color: 'var(--risk)', data: d.map((r, i) => [i, r.heat_stress_h]), unit: 'sector·h', digits: 0, width: 1.8 },
      { name: 'Per radiació', color: 'var(--sun)', data: d.map((r, i) => [i, r.radiation_stress_h]), unit: 'sector·h', digits: 0, width: 1.8 },
    ]);
    // 5. clima
    mk('perC5', { y: { digits: 0 }, y2: { min: 0, digits: 0 }, label: 'Temperatura i radiació' }, [
      { name: 'T màxima (°C)', color: 'var(--risk)', data: d.map((r, i) => [i, r.temp_max]), unit: '°C', digits: 1, width: 2 },
      { name: 'Radiació (kWh/m², eix dret)', color: 'var(--sun)', area: true, axis: 'y2', data: d.map((r, i) => [i, r.ghi_kwh_m2]), unit: 'kWh/m²', digits: 1 },
    ]);
    // 6. aprenentatge
    mk('perC6', { y: { min: 0, digits: 0 }, y2: { min: 0, digits: 0 }, label: 'Regles per cicle i temps per cicle' }, [
      { name: 'Regles per cicle', color: 'var(--shade)', data: d.map((r, i) => [i, r.rules_per_cycle]), unit: '', digits: 0, width: 2 },
      { name: 'Temps per cicle (ms, eix dret)', color: 'var(--tx-2)', axis: 'y2', data: d.map((r, i) => [i, r.avg_ms]), unit: 'ms', digits: 1, width: 1.6 },
    ]);
  }

  /* ----- resum mensual ----- */
  renderMonths() {
    const { months, total } = monthlyRows(this.daily);
    const tr = (r, cls = '') => `<tr class="${cls}"><td>${r.key === 'total' ? 'Total' : esc(monthLabel(r.key))}</td><td class="r num">${r.days}</td>
      <td class="r num">${fmt(r.energy, 0)}</td><td class="r num">${r.eff === null ? '—' : `${fmt(r.eff, 1)} %`}</td>
      <td class="r num">${fmt(r.rain, 1)}</td><td class="r num">${fmt(r.irr, 0)}</td><td class="r num">${fmt(r.m3, 0)}</td>
      <td class="r num">${fmt(r.soil, 0)} %</td><td class="r num">${fmtInt(r.stress)}</td><td class="r num">${fmt(r.wind, 1)}</td><td class="r num">${fmtInt(r.viol)}</td></tr>`;
    this.host.querySelector('#perMonths').innerHTML = `<table class="plain"><thead><tr><th>Mes</th><th class="r">Dies</th><th class="r">Producció (kWh)</th><th class="r">Eficiència</th><th class="r">Pluja (mm)</th><th class="r">Reg (mm/sector)</th><th class="r">Aigua (m³)</th><th class="r">Humitat sòl</th><th class="r">Estrès hídric</th><th class="r">Vent màx (m/s)</th><th class="r">Violacions</th></tr></thead>
      <tbody>${months.map((r) => tr(r)).join('')}${tr(total, 'total')}</tbody></table>`;
  }

  /* ----- experiment: SOAR davant de les referències ----- */
  renderExperiment() {
    const r = this.result; const host = this.host.querySelector('#perExp');
    const runs = r.controllers.map((c) => ({ controller: c, kpis: r.kpis[c] }));
    const stats = r.stats;
    const rows = (stats?.pairs || []).map((p) => {
      const ci = p.IC95_dif; const d = p.dif_mitjana;
      const good = p.better === 'high';
      let verdict = 'Sense diferència clara'; let cls = 'tie';
      if (Array.isArray(ci) && (ci[0] > 0 || ci[1] < 0)) {
        const soarBetter = (d > 0) === good;
        verdict = soarBetter ? 'SOAR millor' : `${CONTROLLER_LONG[p.ref] || p.ref} millor`;
        cls = soarBetter ? 'win' : 'loss';
      }
      const dg = Math.abs(d) < 10 ? 2 : 1;
      const pH = p.p_holm;
      return `<tr><td>${esc(p.label)}</td><td>${esc(CONTROLLER_LONG[p.ref] || p.ref)}</td>
        <td class="r num">${d === null || d === undefined ? '—' : `${d > 0 ? '+' : ''}${fmt(d, dg)}`}</td>
        <td class="r num">${Array.isArray(ci) ? `[${fmt(ci[0], dg)}, ${fmt(ci[1], dg)}]` : '—'}</td>
        <td class="r num">${fmt(100 * (p.win_rate || 0), 0)} % / ${fmt(100 * (p.loss_rate || 0), 0)} %</td>
        <td class="r num">${pH === null || pH === undefined ? '—' : (pH < 0.001 ? '< 0,001' : fmt(pH, 3))}</td>
        <td>${esc(p.magnitud || '')}</td><td><span class="verdict ${cls}">${esc(verdict)}</span></td></tr>`;
    }).join('');
    host.innerHTML = `
      <h3 class="sub">Experiment: SOAR davant de les referències <small>${fmtInt(r.days.length)} dies de dades reals, dia a dia aparellats</small></h3>
      ${this.cb.comparisonHTML(runs).replace(/<h3 class="sub">[^<]*<\/h3>/, '')}
      <div class="chart-card wide"><h3>Producció acumulada: SOAR − referència</h3><div id="perCum"></div></div>
      ${stats?.warning ? `<p class="note">${esc(stats.warning)}</p>` : ''}
      <div class="table-wrap short"><table class="plain stats"><thead><tr><th>Mètrica</th><th>Referència</th><th class="r">Dif. mitjana/dia (SOAR − ref.)</th><th class="r">IC 95 %</th><th class="r">Dies SOAR millor / pitjor</th><th class="r">p (Holm)</th><th>Magnitud</th><th>Veredicte</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty-cell">Cal més de 2 dies per fer estadística.</td></tr>'}</tbody></table></div>`;
    const base = this.result.daily.soar || [];
    const series = [];
    r.controllers.filter((c) => c !== 'soar').forEach((c) => {
      const idx = new Map((r.daily[c] || []).map((x) => [x.day, x]));
      let acc = 0;
      series.push({ name: `SOAR − ${CONTROLLER_LONG[c] || c}`, color: c === 'seguidor' ? 'var(--shade)' : 'var(--safe)', width: 2.2,
        data: base.filter((x) => idx.has(x.day)).map((x) => { acc += x.energy_kwh - idx.get(x.day).energy_kwh; return [this.index.get(x.day), acc]; }), unit: 'kWh', digits: 0 });
    });
    const c = new LineChart(host.querySelector('#perCum'), {
      height: 220, xFormat: (x) => fmtDateShort(this.days[Math.round(x)]), xTicks: () => monthStarts(this.days),
      onSeek: (x) => this.cb.onPickDay(Math.round(x)), y: { digits: 0 }, label: 'Producció acumulada de SOAR menys la referència',
    });
    c.setSeries(series);
    this.charts.push(c);
  }
}
