/* Catàleg d'escenaris amb la durada en dies, i estimació del temps de simulació. */
import { fmtDuration, fmtDate, MODE_LABEL } from './ui.js';

export const scenarioText = (sc) => `${sc.label} — ${fmtDuration(sc.days)}`;

export function fillScenarioSelect(select, scenarios) {
  select.innerHTML = '';
  const groups = [
    ['Escenaris', scenarios.filter((s) => s.kind === 'escenari').sort((a, b) => a.days - b.days || a.label.localeCompare(b.label, 'ca'))],
    ['Totes les dades d’un lloc (creixen sols amb les dades)', scenarios.filter((s) => s.kind === 'dades')],
  ];
  groups.forEach(([title, list]) => {
    if (!list.length) return;
    const g = document.createElement('optgroup');
    g.label = title;
    list.forEach((s) => g.appendChild(new Option(scenarioText(s), s.id)));
    select.appendChild(g);
  });
}

export function scenarioSummary(sc) {
  if (!sc) return [];
  const chips = [{ icon: 'pin', text: sc.location_name }];
  chips.push({ strong: true, text: fmtDuration(sc.days) });
  if (sc.first_day) chips.push({ text: sc.days > 1 ? `${fmtDate(sc.first_day)} – ${fmtDate(sc.last_day)}` : fmtDate(sc.first_day) });
  if (sc.days > 1) chips.push({ text: MODE_LABEL[sc.mode] });
  if (sc.modifiers && Object.keys(sc.modifiers).length) {
    const names = { temp_delta: 'T', vent_factor: 'vent ×', rad_factor: 'radiació ×', pluja_factor: 'pluja ×' };
    chips.push({ warn: true, text: `what-if: ${Object.entries(sc.modifiers).map(([k, v]) => `${names[k] || k}${v}`).join(', ')}` });
  }
  return chips;
}

/* Mateix model que webjobs.estimate_seconds (mesurat amb clipspy): ~0,8 s/dia amb dies independents;
   en continu el dia i-esim costa ~0,3 + 0,043·i s perquè el controlador aprèn. */
const dayCost = (p, i) => p.seq_s_start + p.seq_s_slope * i;
const blockCost = (p, n) => { let s = 0; for (let i = 0; i < n; i += 1) s += dayCost(p, i); return s; };

export function estimateSeconds(perf, days, nControllers, mode) {
  const n = days.length;
  if (!n || !perf) return null;
  const w = Math.max(1, perf.workers);
  if (n === 1 || mode === 'independents') return perf.startup_s + (n * nControllers * perf.indep_s_per_day) / w;
  let tasks;
  if (mode === 'mensual') {
    const m = new Map();
    days.forEach((d) => m.set(d.slice(0, 7), (m.get(d.slice(0, 7)) || 0) + 1));
    tasks = Array(nControllers).fill([...m.values()].map((k) => blockCost(perf, k))).flat();
  } else {
    tasks = Array(nControllers).fill(blockCost(perf, n));
  }
  const loads = Array(Math.max(1, Math.min(w, tasks.length))).fill(0);
  [...tasks].sort((a, b) => b - a).forEach((t) => { loads[loads.indexOf(Math.min(...loads))] += t; });
  return perf.startup_s + Math.max(...loads);
}
