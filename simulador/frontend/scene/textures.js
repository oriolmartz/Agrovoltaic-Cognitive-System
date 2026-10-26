/* Textures procedurals (canvas): sense fitxers externs, funcionen sense xarxa. */
import * as THREE from 'three';
import { tfbm, hash2, seeded } from './noise.js';

function toTexture(canvas, { srgb = true, repeat = [1, 1] } = {}) {
  const t = new THREE.CanvasTexture(canvas);
  t.wrapS = THREE.RepeatWrapping;
  t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = 8;
  t.repeat.set(repeat[0], repeat[1]);
  return t;
}

function canvas(w, h = w) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

/** fn(u,v) -> {r,g,b,h}; genera mapa de color i mapa de normals a partir de h. */
function build(size, fn, normalStrength, opts = {}) {
  const cc = canvas(size);
  const ctx = cc.getContext('2d');
  const img = ctx.createImageData(size, size);
  const H = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const o = fn(x / size, y / size);
      const i = (y * size + x) * 4;
      img.data[i] = o.r; img.data[i + 1] = o.g; img.data[i + 2] = o.b; img.data[i + 3] = 255;
      H[y * size + x] = o.h;
    }
  }
  ctx.putImageData(img, 0, 0);
  const nc = canvas(size);
  const nctx = nc.getContext('2d');
  const nimg = nctx.createImageData(size, size);
  const at = (x, y) => H[((y + size) % size) * size + ((x + size) % size)];
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = at(x + 1, y) - at(x - 1, y);
      const dy = at(x, y + 1) - at(x, y - 1);
      let nx = -dx * normalStrength; let ny = dy * normalStrength; let nz = 1;
      const l = Math.hypot(nx, ny, nz);
      nx /= l; ny /= l; nz /= l;
      const i = (y * size + x) * 4;
      nimg.data[i] = (nx * 0.5 + 0.5) * 255; nimg.data[i + 1] = (ny * 0.5 + 0.5) * 255; nimg.data[i + 2] = (nz * 0.5 + 0.5) * 255; nimg.data[i + 3] = 255;
    }
  }
  nctx.putImageData(nimg, 0, 0);
  return { map: toTexture(cc, { srgb: true, repeat: opts.repeat }), normalMap: toTexture(nc, { srgb: false, repeat: opts.repeat }) };
}

export function grassTextures(size = 512, repeat = [1, 1]) {
  return build(size, (u, v) => {
    const lo = tfbm(u, v, 5, 3, 1);
    const mid = tfbm(u, v, 22, 3, 2);
    const hi = tfbm(u, v, 110, 2, 3);
    const dry = tfbm(u, v, 7, 2, 9);
    const t = lo * 0.5 + mid * 0.32 + hi * 0.18;
    return { r: 104 + 46 * t + 34 * dry, g: 142 + 36 * t - 6 * dry, b: 78 + 20 * t, h: mid * 0.5 + hi * 0.5 };
  }, 2.4, { repeat });
}

/** Terra llaurada: crestes cada `period` (en unitats de textura = 1 cop per tile en u). */
export function soilTextures(size = 512, repeat = [1, 1], phase = 0.7826) {
  return build(size, (u, v) => {
    const ridge = 0.5 + 0.5 * Math.cos(2 * Math.PI * (u - phase));
    const clod = tfbm(u, v, 28, 3, 4);
    const fine = tfbm(u, v, 120, 2, 5);
    const pebble = hash2(Math.floor(u * 90), Math.floor(v * 90), 3) > 0.985 ? 1 : 0;
    const shade = 0.62 + 0.30 * ridge + 0.22 * clod;
    return {
      r: 150 * shade + 26 * fine + pebble * 60,
      g: 112 * shade + 20 * fine + pebble * 55,
      b: 80 * shade + 14 * fine + pebble * 48,
      h: ridge * 1.0 + clod * 0.5 + fine * 0.2,
    };
  }, 3.2, { repeat });
}

/** Grava amb rodades. Tile al llarg de u; les rodades són bandes en v. */
export function gravelTextures(size = 512, repeat = [1, 1]) {
  return build(size, (u, v) => {
    const n = tfbm(u, v, 14, 3, 6);
    const fine = tfbm(u, v, 140, 2, 7);
    const cell = hash2(Math.floor(u * 70), Math.floor(v * 70), 5);
    const peb = cell > 0.9 ? (cell - 0.9) * 5 : 0;
    const track = Math.exp(-Math.pow((v - 0.3) / 0.08, 2)) + Math.exp(-Math.pow((v - 0.7) / 0.08, 2));
    const grass = Math.max(0, 0.5 - Math.abs(v - 0.5)) < 0.04 ? 0 : 0;
    const base = 176 + 38 * n + 22 * fine + peb * 40 - track * 26 + grass;
    return { r: base, g: base * 0.94, b: base * 0.8, h: n * 0.6 + fine * 0.5 + peb - track * 0.7 };
  }, 2.0, { repeat });
}

/** Textura de detall en gris (multiplica els colors per vèrtex del terreny llunyà). */
export function detailTexture(size = 256, repeat = [1, 1]) {
  const c = canvas(size);
  const ctx = c.getContext('2d');
  const img = ctx.createImageData(size, size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const u = x / size; const v = y / size;
      const t = 0.5 * tfbm(u, v, 6, 3, 11) + 0.3 * tfbm(u, v, 30, 3, 12) + 0.2 * tfbm(u, v, 90, 2, 13);
      const g = 255 * (0.74 + 0.5 * t);
      const i = (y * size + x) * 4;
      img.data[i] = g; img.data[i + 1] = g; img.data[i + 2] = g; img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(c, { srgb: true, repeat });
}

/** Mòdul fotovoltaic: marc d'alumini, cèl·lules de silici, busbars. */
export function panelTexture(cols = 24, rows = 10) {
  const W = 1536; const Hh = Math.round(W * 2.28 / 5.45);
  const c = canvas(W, Hh);
  const g = c.getContext('2d');
  g.fillStyle = '#d3dade'; g.fillRect(0, 0, W, Hh);
  const m = 16;
  g.fillStyle = '#07152b'; g.fillRect(m, m, W - 2 * m, Hh - 2 * m);
  const cw = (W - 2 * m) / cols; const ch = (Hh - 2 * m) / rows;
  for (let j = 0; j < rows; j += 1) {
    for (let i = 0; i < cols; i += 1) {
      const x = m + i * cw + 1.6; const y = m + j * ch + 1.6;
      const w = cw - 3.2; const h = ch - 3.2;
      const k = hash2(i, j, 21);
      const grad = g.createLinearGradient(x, y, x + w, y + h);
      grad.addColorStop(0, `rgb(${16 + k * 8},${50 + k * 16},${96 + k * 20})`);
      grad.addColorStop(1, `rgb(${10 + k * 6},${34 + k * 12},${72 + k * 16})`);
      g.fillStyle = grad; g.fillRect(x, y, w, h);
      g.strokeStyle = 'rgba(170,196,222,0.55)'; g.lineWidth = 1.1;
      for (let b = 1; b <= 3; b += 1) {
        const bx = x + (w * b) / 4;
        g.beginPath(); g.moveTo(bx, y + 1); g.lineTo(bx, y + h - 1); g.stroke();
      }
      g.strokeStyle = 'rgba(120,150,184,0.18)'; g.lineWidth = 0.7;
      for (let f = 1; f < 14; f += 1) {
        const fy = y + (h * f) / 14;
        g.beginPath(); g.moveTo(x + 2, fy); g.lineTo(x + w - 2, fy); g.stroke();
      }
    }
  }
  const t = toTexture(c, { srgb: true });
  t.wrapS = THREE.ClampToEdgeWrapping; t.wrapT = THREE.ClampToEdgeWrapping; t.anisotropy = 16;
  return t;
}

export function cloudTexture() {
  const c = canvas(256, 128);
  const g = c.getContext('2d');
  for (let i = 0; i < 16; i += 1) {
    const x = 40 + seeded(i * 3 + 1) * 176; const y = 50 + seeded(i * 5 + 2) * 36;
    const r = 22 + seeded(i * 7 + 3) * 34;
    const rg = g.createRadialGradient(x, y, 0, x, y, r);
    rg.addColorStop(0, 'rgba(255,255,255,0.85)'); rg.addColorStop(0.55, 'rgba(255,255,255,0.4)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = rg; g.fillRect(0, 0, 256, 128);
  }
  g.globalCompositeOperation = 'source-atop';
  const sh = g.createLinearGradient(0, 30, 0, 110);
  sh.addColorStop(0, 'rgba(255,255,255,0)'); sh.addColorStop(1, 'rgba(120,134,156,0.7)');
  g.fillStyle = sh; g.fillRect(0, 0, 256, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function glowTexture() {
  const c = canvas(128);
  const g = c.getContext('2d');
  const rg = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  rg.addColorStop(0, 'rgba(255,255,255,1)'); rg.addColorStop(0.12, 'rgba(255,244,214,0.75)');
  rg.addColorStop(0.4, 'rgba(255,214,150,0.22)'); rg.addColorStop(1, 'rgba(255,200,120,0)');
  g.fillStyle = rg; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Gota/boirina suau per a partícules d'aigua (additiva). */
export function dropTexture() {
  const c = canvas(64);
  const g = c.getContext('2d');
  const rg = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  rg.addColorStop(0, 'rgba(255,255,255,1)'); rg.addColorStop(0.25, 'rgba(190,232,255,0.85)');
  rg.addColorStop(0.6, 'rgba(90,190,255,0.28)'); rg.addColorStop(1, 'rgba(60,160,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Franges brillants que "corren" per les canonades quan hi ha reg (emissiveMap). */
export function flowTexture(repeatY = 1) {
  const c = canvas(8, 128);
  const g = c.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, 8, 128);
  for (let i = 0; i < 4; i += 1) {
    const y = i * 32;
    const gr = g.createLinearGradient(0, y, 0, y + 22);
    gr.addColorStop(0, 'rgba(120,210,255,0)'); gr.addColorStop(0.5, 'rgba(150,225,255,1)'); gr.addColorStop(1, 'rgba(120,210,255,0)');
    g.fillStyle = gr; g.fillRect(0, y, 8, 22);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.repeat.set(1, repeatY);
  return t;
}

/** Banda d'humitat centrada a cada fila de cultiu (es repeteix en x). */
export function wetStripeTexture() {
  const c = canvas(64);
  const g = c.getContext('2d');
  const img = g.createImageData(64, 64);
  for (let y = 0; y < 64; y += 1) {
    for (let x = 0; x < 64; x += 1) {
      const band = Math.exp(-Math.pow((x - 32) / 11, 2));
      const sheen = 0.72 + 0.28 * tfbm(x / 64, y / 64, 4, 2, 31);
      const a = band * sheen;
      const i = (y * 64 + x) * 4;
      img.data[i] = 90; img.data[i + 1] = 185; img.data[i + 2] = 255; img.data[i + 3] = a * 255;
    }
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
