/* Cinta de decisions.
 *
 * Una fila per sector i una columna per cicle. Cada cel·la mostra l'acció que va
 * seleccionar el controlador (color per categoria), l'angle resultant, si hi va
 * haver reg, risc o impasse. A sobre, la radiació i el vent alineats en el temps
 * expliquen *per què* canvia l'acció. També fa de línia de temps: clic, arrossegar
 * o fletxes del teclat mouen la reproducció.
 */
import { actionCategory, actionLabel, clock, cropColor, cropLabel, esc, fmt, maxRiskRank, mean, parseRisks, prettyReason, sectorLabel } from './ui.js';

const rec = (f, sector) => f.records.get(sector);

export class Ribbon {
  constructor(root, { onSeek } = {}) {
    this.root = root;
    this.onSeek = onSeek || (() => {});
    this.frames = [];
    this.n = 0;
    this.pos = 0;
    this.drag = false;
    root.setAttribute('tabindex', '0');
    root.setAttribute('role', 'slider');
    root.setAttribute('aria-label', 'Cicle de la simulació');
    root.addEventListener('pointerdown', (e) => this._down(e));
    root.addEventListener('pointermove', (e) => this._move(e));
    root.addEventListener('pointerup', () => { this.drag = false; });
    root.addEventListener('pointercancel', () => { this.drag = false; });
    root.addEventListener('pointerleave', () => this._hideTip());
    root.addEventListener('keydown', (e) => this._key(e));
    this.clear();
  }

  clear() {
    this.frames = []; this.n = 0;
    this.root.classList.add('is-empty');
    this.root.removeAttribute('aria-valuemax');
    this.root.innerHTML = `
      <div class="rb-empty">
        <p><strong>Encara no hi ha decisions per mostrar.</strong>
        Executa una simulació i aquí veuràs, hora a hora, què decideix cada sector i per què.</p>
      </div>`;
  }

  setData({ frames, sectors }) {
    this.frames = frames;
    this.n = frames.length;
    this.sectors = sectors;
    const n = this.n;
    const raining = frames.some((f) => [...f.records.values()].some((r) => Number(r.pluja_mm) > 0.05));
    const ctx = [
      { id: 'ghi', label: 'Radiació', unit: 'W/m²', tone: 'sun', digits: 0, get: (f) => mean([...f.records.values()].map((r) => r.ghi)) },
      { id: 'wind', label: 'Vent', unit: 'm/s', tone: 'safe', digits: 1, get: (f) => mean([...f.records.values()].map((r) => r.vent_real ?? r.vent_obs)) },
    ];
    if (raining) ctx.push({ id: 'rain', label: 'Pluja', unit: 'mm', tone: 'water', digits: 1, bars: true, get: (f) => mean([...f.records.values()].map((r) => r.pluja_mm)) });
    this.ctx = ctx;

    const spark = (row) => {
      const vals = frames.map((f) => Number(row.get(f)) || 0);
      const max = Math.max(...vals, row.bars ? 0.5 : 1);
      row.max = max;
      if (row.bars) {
        return `<svg viewBox="0 0 ${n} 30" preserveAspectRatio="none" aria-hidden="true">${vals.map((v, i) => (v > 0.01 ? `<rect x="${i + 0.18}" width="0.64" y="${29 - (v / max) * 27}" height="${(v / max) * 27 + 1}" rx="0.1"/>` : '')).join('')}</svg>`;
      }
      const pts = vals.map((v, i) => `${(i + 0.5).toFixed(2)},${(29 - (v / max) * 26).toFixed(2)}`);
      const line = `M${pts.join(' L')}`;
      return `<svg viewBox="0 0 ${n} 30" preserveAspectRatio="none" aria-hidden="true"><path class="a" d="${line} L${n - 0.5},30 L0.5,30 Z"/><path class="l" d="${line}"/></svg>`;
    };

    const cell = (f, i, s) => {
      const r = rec(f, s.id);
      if (!r) return '<span class="rb-cell none"></span>';
      const cat = actionCategory(r.accio);
      const water = Number(r.reg_mm) > 0.05;
      const risk = maxRiskRank(r.riscos);
      return `<span class="rb-cell cat-${cat}" data-i="${i}"><b>${Math.round(Number(r.angle_real))}°</b>${water ? '<i class="rb-water"></i>' : ''}${risk ? `<i class="rb-risk lvl-${risk}"></i>` : ''}${r.impas ? '<i class="rb-impasse"></i>' : ''}</span>`;
    };

    this.root.classList.remove('is-empty');
    this.root.setAttribute('aria-valuemin', '0');
    this.root.setAttribute('aria-valuemax', String(Math.max(0, n - 1)));
    this.root.innerHTML = `
      <div class="rb-grid" style="--n:${n}">
        <div class="rb-corner"></div>
        <div class="rb-ruler">${frames.map((f) => `<span>${Math.round(f.hora)} h</span>`).join('')}</div>
        ${ctx.map((row) => `
          <div class="rb-label ctx tone-${row.tone}"><span>${row.label}</span></div>
          <div class="rb-ctx tone-${row.tone}${row.bars ? ' bars' : ''}" data-row="ctx:${row.id}">${spark(row)}</div>`).join('')}
        ${sectors.map((s) => `
          <div class="rb-label"><i class="crop-dot" style="--c:${cropColor(s.crop)}"></i><span>${esc(sectorLabel(s.id))}<small>${esc(cropLabel(s.crop))}</small></span></div>
          <div class="rb-cells" data-row="sector:${esc(s.id)}">${frames.map((f, i) => cell(f, i, s)).join('')}</div>`).join('')}
        <div class="rb-overlay"><div class="rb-playhead" data-t="--:--"></div></div>
      </div>
      <div class="rb-tip" hidden></div>`;
    this.playhead = this.root.querySelector('.rb-playhead');
    this.tip = this.root.querySelector('.rb-tip');
    this.setPosition(this.pos);
  }

  setPosition(pos) {
    if (!this.n) return;
    this.pos = pos;
    this.root.style.setProperty('--p', String((pos + 0.5) / this.n));
    const i0 = Math.floor(pos);
    const i1 = Math.min(this.n - 1, i0 + 1);
    const hora = this.frames[i0].hora + (this.frames[i1].hora - this.frames[i0].hora) * (pos - i0);
    const t = clock(hora);
    if (this.playhead && this.playhead.dataset.t !== t) this.playhead.dataset.t = t;
    this.root.setAttribute('aria-valuenow', String(Math.round(pos)));
    this.root.setAttribute('aria-valuetext', t);
    const idx = Math.round(pos);
    if (idx !== this._idx) {
      this._idx = idx;
      this.root.querySelectorAll('.rb-cell.now').forEach((el) => el.classList.remove('now'));
      this.root.querySelectorAll(`.rb-cell[data-i="${idx}"]`).forEach((el) => el.classList.add('now'));
    }
  }

  /* ----- interacció ----- */
  _ruler() { return this.root.querySelector('.rb-ruler'); }

  _fromX(x, snap) {
    const r = this._ruler();
    if (!r) return null;
    const b = r.getBoundingClientRect();
    const f = (x - b.left) / b.width;
    const p = Math.min(this.n - 1, Math.max(0, f * this.n - 0.5));
    return snap ? Math.round(p) : p;
  }

  _down(e) {
    if (!this.n) return;
    const r = this._ruler().getBoundingClientRect();
    if (e.clientX < r.left - 2) return;
    this.drag = true;
    this.root.setPointerCapture?.(e.pointerId);
    const onCell = e.target.closest?.('.rb-cell');
    this.onSeek(this._fromX(e.clientX, Boolean(onCell)));
    this.root.focus({ preventScroll: true });
  }

  _move(e) {
    if (!this.n) return;
    if (this.drag) { this.onSeek(this._fromX(e.clientX, false)); this._hideTip(); return; }
    this._showTip(e);
  }

  _key(e) {
    if (!this.n) return;
    const cur = Math.round(this.pos);
    const map = { ArrowRight: cur + 1, ArrowUp: cur + 1, ArrowLeft: cur - 1, ArrowDown: cur - 1, Home: 0, End: this.n - 1, PageUp: cur + 3, PageDown: cur - 3 };
    if (!(e.key in map)) return;
    e.preventDefault(); e.stopPropagation();
    this.onSeek(Math.min(this.n - 1, Math.max(0, map[e.key])));
  }

  _hideTip() { if (this.tip) this.tip.hidden = true; }

  _showTip(e) {
    if (!this.tip) return;
    const rowEl = e.target.closest?.('[data-row]');
    const p = this._fromX(e.clientX, true);
    if (!rowEl || p == null || e.clientX < this._ruler().getBoundingClientRect().left) { this._hideTip(); return; }
    const f = this.frames[p];
    const [kind, id] = rowEl.dataset.row.split(':');
    let html = '';
    if (kind === 'ctx') {
      const row = this.ctx.find((c) => c.id === id);
      html = `<strong>${clock(f.hora)} · ${row.label}</strong><div>${fmt(row.get(f), row.digits)} ${row.unit}</div>`;
    } else {
      const r = rec(f, id);
      if (!r) { this._hideTip(); return; }
      const cat = actionCategory(r.accio);
      const risks = parseRisks(r.riscos);
      html = `<strong>${clock(f.hora)} · ${esc(sectorLabel(id))} · ${esc(cropLabel(r.cultiu))}</strong>
        <div class="t-act"><i class="sw cat-${cat}"></i>${esc(actionLabel(r.accio))}</div>
        <div>Angle ${fmt(r.angle_real, 0)}° <span class="dim">(òptim ${fmt(r.angle_optim, 0)}°)</span></div>
        ${r.reg_accio ? `<div class="${Number(r.reg_mm) > 0.05 ? 't-water' : 'dim'}">${esc(actionLabel(r.reg_accio))}${Number(r.reg_mm) > 0.05 ? ` · dosi ${fmt(r.reg_dosi_pct, 0)} % · ${fmt(r.reg_mm, 1)} mm` : ''}</div>` : (Number(r.reg_mm) > 0.05 ? `<div class="t-water">Reg de la finca · ${fmt(r.reg_mm, 1)} mm</div>` : '')}
        ${risks.length ? `<div class="t-risk">${risks.map((k) => `${esc(k.label)} ${esc(k.level)}`).join(' · ')}</div>` : ''}
        ${r.impas ? `<div class="t-risk">Impasse: ${esc(r.impas)}</div>` : ''}
        <em>${esc(prettyReason(r.motiu))}</em>`;
    }
    this.tip.innerHTML = html;
    this.tip.hidden = false;
    const host = this.root.getBoundingClientRect();
    const tw = this.tip.offsetWidth;
    const th = this.tip.offsetHeight;
    let x = e.clientX - host.left + 14;
    if (x + tw > host.width - 6) x = e.clientX - host.left - tw - 14;
    let y = e.clientY - host.top - th - 12;
    if (y < 0) y = e.clientY - host.top + 18;
    this.tip.style.transform = `translate(${Math.max(4, x)}px, ${y}px)`;
  }
}
