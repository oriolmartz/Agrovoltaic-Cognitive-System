/* Utilitats de presentació compartides.
 *
 * Aquest mòdul només formata i etiqueta dades que ja arriben del backend.
 * No avalua candidats ni tria accions: la decisió continua dins de CLIPS.
 */

export const $ = (id) => document.getElementById(id);
export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const lerp = (a, b, t) => a + (b - a) * t;

export function mean(values) {
  const nums = values.map(Number).filter(Number.isFinite);
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m]));
}

export function fmt(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('ca-ES', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtInt(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('ca-ES', { maximumFractionDigits: 0 });
}

const pad2 = (n) => String(n).padStart(2, '0');

/** 13.5 -> "13:30" */
export function clock(h) {
  if (!Number.isFinite(Number(h))) return '--:--';
  let hh = Math.floor(Number(h));
  let mm = Math.round((Number(h) - hh) * 60);
  if (mm === 60) { hh += 1; mm = 0; }
  return `${pad2(hh)}:${pad2(mm)}`;
}

/* ---------- Icones (traç 1.8, 24x24) ---------- */
const PATHS = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a6.8 6.8 0 0 0 10.7 10.7z"/>',
  wind: '<path d="M3 8h10a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h6"/>',
  drop: '<path d="M12 3c3.2 4 6 7 6 11a6 6 0 0 1-12 0c0-4 2.8-7 6-11z"/>',
  cloud: '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 11.2 3.5 3.5 0 0 0 7 18z"/>',
  rain: '<path d="M7 14.5h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 7.7 3.5 3.5 0 0 0 7 14.5z"/><path d="M8 17.5l-1 3M12 17.5l-1 3M16 17.5l-1 3"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
  play: '<path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6.5" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none"/>',
  reset: '<path d="M4 4v6h6"/><path d="M5.5 14.5A8 8 0 1 0 7 6.8L4 10"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 3.5l9.5 16.5h-19L12 3.5z"/><path d="M12 10v4.5M12 17.5v.5"/>',
  bolt: '<path d="M13 2.5L4.5 14H11l-1 7.5L19.5 10H13l0-7.5z"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  chevron: '<path d="M9 5l7 7-7 7"/>',
  sidebar: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>',
};

export function icon(name, cls = '') {
  return `<svg class="ico ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PATHS[name] || ''}</svg>`;
}

/* ---------- Vocabulari ---------- */
const WORDS = {
  produccio: 'producció', posicio: 'posició', radiacio: 'radiació', exces: 'excés',
  estres: 'estrès', hidric: 'hídric', mecanic: 'mecànic', critic: 'crític', mitja: 'mitjà',
  maxima: 'màxima', valoracio: 'valoració', pressupost: 'pressupost', esgotat: 'esgotat',
  unica: 'única', opcio: 'opció', punts: 'punts', regar: 'regar', sense: 'sense', moviment: 'moviment', energia: 'energia', demanda: 'demanda',
};

function words(slug) {
  return String(slug ?? '').split(/[-_\s]+/).filter(Boolean).map((w) => WORDS[w] || w);
}

function sentence(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

/** Slug del backend -> text llegible ("orientar-ombra" -> "Orientar a ombra"). */
export function actionLabel(accio) {
  const raw = String(accio ?? '').split(/[-_\s]+/).filter(Boolean);
  if (!raw.length) return '—';
  const w = words(accio);
  if (raw[0] === 'orientar' && w.length > 1) return sentence(`orientar a ${w.slice(1).join(' ')}`);
  if (raw[0] === 'posicio' && w.length > 1) return sentence(`posició de ${w.slice(1).join(' ')}`);
  return sentence(w.join(' '));
}

/** Categoria visual (només presentació) segons l'arrel del nom de l'acció. */
export function actionCategory(accio) {
  const s = String(accio ?? '');
  if (/seguret/.test(s)) return 'safety';
  if (/ombra/.test(s)) return 'shade';
  if (/produc/.test(s)) return 'production';
  if (/mantenir/.test(s)) return 'hold';
  return 'other';
}

export const CATEGORIES = [
  { id: 'production', label: 'Producció' },
  { id: 'shade', label: 'Ombra' },
  { id: 'safety', label: 'Seguretat' },
  { id: 'hold', label: 'Manté posició' },
];

const LEVELS = { baix: 1, mitja: 2, alt: 3, critic: 4 };

/** "mecanic=critic;temperatura=mitja" -> [{label, level, rank}] */
export function parseRisks(str) {
  return String(str ?? '').split(';').map((x) => x.trim()).filter(Boolean).map((tok) => {
    const [kind, level = ''] = tok.split('=');
    return {
      kind,
      label: sentence(words(kind).join(' ')),
      level: words(level).join(' '),
      rank: LEVELS[level] || 2,
    };
  }).sort((a, b) => b.rank - a.rank);
}

export function maxRiskRank(str) {
  const r = parseRisks(str);
  return r.length ? r[0].rank : 0;
}

/** Restitueix accents del text d'explicació que genera CLIPS. */
export function prettyReason(str) {
  const s = String(str ?? '').trim();
  if (!s) return '';
  const out = s.replace(/[A-Za-zÀ-ÿ]+/g, (w) => WORDS[w.toLowerCase()] || w);
  return sentence(out).replace(/\((\d+)\.(\d+) punts\)/, '($1,$2 punts)');
}

export function cropKey(c) {
  const s = String(c ?? '').toLowerCase();
  if (s.includes('enciam')) return 'enciam';
  if (s.includes('vinya')) return 'vinya';
  if (s.includes('tomaquet')) return 'tomaquet';
  return 'other';
}

export const cropColor = (c) => `var(--crop-${cropKey(c)})`;
export const cropLabel = (c) => sentence(String(c ?? '').replace(/[-_]/g, ' '));
export const sectorLabel = (s) => String(s ?? '').replace(/_/g, ' ');

export const CONTROLLER_SHORT = { soar: 'SOAR', seguidor: 'Seguidor', fix: 'Fix' };
export const CONTROLLER_LONG = { soar: 'SOAR / CLIPS', seguidor: 'Seguidor comercial', fix: 'Panell fix' };
