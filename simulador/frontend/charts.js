/* Gràfics SVG sense dependències.
 *
 * - Mida real (ResizeObserver): el text no es deforma mai.
 * - Doble eix (y / y2), àrees, barres i línies discontínues.
 * - Cursor amb tooltip i clic per anar a una hora.
 * - Cap de lectura sincronitzat amb la reproducció (setPlayhead).
 * Els colors són variables CSS: canvien sols amb el tema.
 */
import { esc, fmt } from './ui.js';

const NS = 'http://www.w3.org/2000/svg';
let uid = 0;

function niceTicks(min, max, count = 4) {
  if (!(max > min)) { max = min + 1; }
  const step0 = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const norm = step0 / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const lo = Math.floor(min / step + 1e-9) * step;
  const hi = Math.ceil(max / step - 1e-9) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(10));
  return { min: lo, max: hi, ticks };
}

function makeScale(values, spec = {}) {
  let lo = values.length ? Math.min(...values) : 0;
  let hi = values.length ? Math.max(...values) : 1;
  if (spec.min != null) lo = Math.min(spec.min, lo);
  if (spec.max != null) hi = Math.max(spec.max, hi);
  const t = niceTicks(lo, hi, spec.ticks ?? 4);
  const min = spec.min != null ? spec.min : t.min;
  const max = spec.max != null ? spec.max : t.max;
  return { min, max, ticks: t.ticks.filter((v) => v >= min - 1e-9 && v <= max + 1e-9) };
}

export class LineChart {
  /**
   * @param {HTMLElement} root
   * @param {{height?:number,y?:object,y2?:object,xFormat?:(x:number)=>string,onSeek?:(x:number)=>void,label?:string}} opts
   */
  constructor(root, opts = {}) {
    this.root = root;
    this.o = { height: 220, xFormat: (x) => `${String(Math.round(x)).padStart(2, '0')}:00`, y: {}, y2: null, ...opts };
    this.series = [];
    this.playX = null;
    this.id = `lc${++uid}`;
    root.classList.add('chart');
    root.innerHTML = '<div class="ch-legend"></div><div class="ch-plot"><svg></svg><div class="ch-tip" hidden></div></div>';
    this.legend = root.querySelector('.ch-legend');
    this.plot = root.querySelector('.ch-plot');
    this.svg = root.querySelector('svg');
    this.tip = root.querySelector('.ch-tip');
    this.svg.setAttribute('role', 'img');
    if (opts.label) this.svg.setAttribute('aria-label', opts.label);
    this.plot.style.height = `${this.o.height}px`;
    this.ro = new ResizeObserver(() => this.draw());
    this.ro.observe(this.plot);
    this.svg.addEventListener('pointermove', (e) => this._hover(e));
    this.svg.addEventListener('pointerleave', () => this._leave());
    this.svg.addEventListener('click', (e) => {
      const x = this._nearestX(e);
      if (x != null && this.o.onSeek) this.o.onSeek(x);
    });
  }

  setSeries(series) {
    this.series = series.filter((s) => s.data && s.data.length);
    this._renderLegend();
    this.draw();
  }

  setPlayhead(x) {
    this.playX = Number.isFinite(x) ? x : null;
    this._updatePlayhead();
  }

  destroy() { this.ro.disconnect(); }

  _renderLegend() {
    this.legend.innerHTML = this.series.map((s) =>
      `<span class="lg"><i class="sw${s.dashed ? ' dashed' : ''}${s.type === 'bar' ? ' bar' : ''}" style="--c:${s.color}"></i>${esc(s.name)}</span>`).join('');
  }

  draw() {
    const w = this.plot.clientWidth;
    const h = this.o.height;
    if (!w || !this.series.length) {
      if (!this.series.length) this.svg.innerHTML = '';
      return;
    }
    const hasY2 = this.series.some((s) => s.axis === 'y2');
    const m = { l: 44, r: hasY2 ? 44 : 14, t: 10, b: 24 };
    const iw = w - m.l - m.r;
    const ih = h - m.t - m.b;
    const left = this.series.filter((s) => s.axis !== 'y2');
    const right = this.series.filter((s) => s.axis === 'y2');
    const sy = makeScale(left.flatMap((s) => s.data.map((d) => d[1])).filter(Number.isFinite), this.o.y);
    const sy2 = hasY2 ? makeScale(right.flatMap((s) => s.data.map((d) => d[1])).filter(Number.isFinite), this.o.y2 || {}) : null;
    const xsAll = [...new Set(this.series.flatMap((s) => s.data.map((d) => d[0])))].sort((a, b) => a - b);
    const hasBars = this.series.some((s) => s.type === 'bar');
    const pad = hasBars ? 0.5 : 0;
    const xmin = xsAll[0] - pad;
    const xmax = xsAll[xsAll.length - 1] + pad;
    const X = (x) => m.l + ((x - xmin) / (xmax - xmin || 1)) * iw;
    const Yl = (v) => m.t + ih - ((v - sy.min) / (sy.max - sy.min || 1)) * ih;
    const Yr = (v) => m.t + ih - ((v - sy2.min) / (sy2.max - sy2.min || 1)) * ih;
    this._geo = { m, iw, ih, X, xmin, xmax, xsAll, w, h };

    const yFmt = (v, spec) => fmt(v, spec?.digits ?? 0);
    let g = '';
    sy.ticks.forEach((v) => {
      const y = Yl(v);
      const zero = v === 0 && sy.min < 0;
      g += `<line class="gl${zero ? ' zero' : ''}" x1="${m.l}" x2="${w - m.r}" y1="${y}" y2="${y}"/>`;
      g += `<text class="ax" x="${m.l - 8}" y="${y + 3.5}" text-anchor="end">${yFmt(v, this.o.y)}</text>`;
    });
    if (sy2) sy2.ticks.forEach((v) => {
      g += `<text class="ax" x="${w - m.r + 8}" y="${Yr(v) + 3.5}" text-anchor="start">${yFmt(v, this.o.y2)}</text>`;
    });
    const span = xmax - xmin;
    const target = Math.max(2, Math.floor(iw / 58));
    const stepX = [1, 2, 3, 4, 6, 12].find((s) => span / s <= target) || 12;
    xsAll.filter((x) => (x - xsAll[0]) % stepX === 0).forEach((x) => {
      g += `<text class="ax" x="${X(x)}" y="${h - 6}" text-anchor="middle">${esc(this.o.xFormat(x))}</text>`;
    });

    let defs = '';
    let body = '';
    this.series.forEach((s, i) => {
      const Y = s.axis === 'y2' ? Yr : Yl;
      const scale = s.axis === 'y2' ? sy2 : sy;
      const style = `style="--c:${s.color}"`;
      if (s.type === 'bar') {
        const bw = Math.max(3, (iw / (xmax - xmin || 1)) * 0.56);
        s.data.forEach(([x, v]) => {
          if (!Number.isFinite(v) || v <= 0) return;
          const y = Y(v);
          const base = Y(Math.max(scale.min, 0));
          body += `<rect class="bar" ${style} x="${X(x) - bw / 2}" y="${y}" width="${bw}" height="${Math.max(1, base - y)}" rx="1.5"/>`;
        });
        return;
      }
      const pts = s.data.filter((d) => Number.isFinite(d[1])).map(([x, v]) => [X(x), Y(v)]);
      if (!pts.length) return;
      const line = pts.map((p, k) => `${k ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
      if (s.area) {
        const gid = `${this.id}-g${i}`;
        const base = Y(Math.max(scale.min, 0));
        defs += `<linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${s.color};stop-opacity:.34"/><stop offset="1" style="stop-color:${s.color};stop-opacity:0"/></linearGradient>`;
        body += `<path class="area" ${style} fill="url(#${gid})" d="${line} L${pts[pts.length - 1][0].toFixed(1)} ${base} L${pts[0][0].toFixed(1)} ${base} Z"/>`;
      }
      body += `<path class="ln${s.dashed ? ' dashed' : ''}" ${style} d="${line}" ${s.width ? `stroke-width="${s.width}"` : ''}/>`;
    });

    this.svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    this.svg.setAttribute('width', w);
    this.svg.setAttribute('height', h);
    this.svg.innerHTML = `<defs>${defs}</defs>${g}${body}
      <g class="ph" hidden><line y1="${m.t}" y2="${m.t + ih}"/><path d="M-4 ${m.t - 1}h8l-4 6z"/></g>
      <g class="hv" hidden><line y1="${m.t}" y2="${m.t + ih}"/></g>
      <g class="dots"></g>
      <rect class="hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}"/>`;
    this._Y = { Yl, Yr };
    this._updatePlayhead();
  }

  _updatePlayhead() {
    const ph = this.svg.querySelector('.ph');
    if (!ph || !this._geo) return;
    const { X, xmin, xmax } = this._geo;
    if (this.playX == null || this.playX < xmin || this.playX > xmax) { ph.setAttribute('hidden', ''); return; }
    ph.removeAttribute('hidden');
    ph.setAttribute('transform', `translate(${X(this.playX).toFixed(1)} 0)`);
  }

  _nearestX(e) {
    if (!this._geo) return null;
    const r = this.svg.getBoundingClientRect();
    const px = e.clientX - r.left;
    const { X, xsAll } = this._geo;
    let best = null; let bd = Infinity;
    xsAll.forEach((x) => { const d = Math.abs(X(x) - px); if (d < bd) { bd = d; best = x; } });
    return best;
  }

  _hover(e) {
    const x = this._nearestX(e);
    if (x == null) return;
    const { X, m, iw, w } = this._geo;
    const px = X(x);
    const hv = this.svg.querySelector('.hv');
    hv.removeAttribute('hidden');
    hv.setAttribute('transform', `translate(${px.toFixed(1)} 0)`);
    let dots = ''; let rows = '';
    this.series.forEach((s) => {
      const d = s.data.find((p) => p[0] === x);
      if (!d || !Number.isFinite(d[1])) return;
      const Y = s.axis === 'y2' ? this._Y.Yr : this._Y.Yl;
      if (s.type !== 'bar') dots += `<circle class="dot" style="--c:${s.color}" cx="${px.toFixed(1)}" cy="${Y(d[1]).toFixed(1)}" r="3.5"/>`;
      rows += `<div><i class="sw${s.type === 'bar' ? ' bar' : ''}" style="--c:${s.color}"></i><span>${esc(s.name)}</span><b>${fmt(d[1], s.digits ?? this.o.y?.digits ?? 1)}${s.unit ? ` ${esc(s.unit)}` : ''}</b></div>`;
    });
    this.svg.querySelector('.dots').innerHTML = dots;
    this.tip.innerHTML = `<strong>${esc(this.o.xFormat(x))}</strong>${rows}`;
    this.tip.hidden = false;
    const tw = this.tip.offsetWidth;
    const flip = px + tw + 18 > w - 4;
    this.tip.style.left = `${flip ? px - tw - 12 : px + 12}px`;
    this.tip.style.top = `${m.t + 4}px`;
    void iw;
  }

  _leave() {
    this.svg.querySelector('.hv')?.setAttribute('hidden', '');
    const d = this.svg.querySelector('.dots');
    if (d) d.innerHTML = '';
    this.tip.hidden = true;
  }
}
