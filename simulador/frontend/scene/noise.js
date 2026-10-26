/* Soroll determinista (valor + fbm). Les versions "t*" són periòdiques: serveixen per
   generar textures que es repeteixen sense costures. */

export function hash2(x, y, s = 0) {
  const h = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453123;
  return h - Math.floor(h);
}

export function tnoise(x, y, P, s = 0) {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const m = (n) => ((n % P) + P) % P;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const a = hash2(m(xi), m(yi), s);
  const b = hash2(m(xi + 1), m(yi), s);
  const c = hash2(m(xi), m(yi + 1), s);
  const d = hash2(m(xi + 1), m(yi + 1), s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

/** fbm periòdic a [0,1]^2 amb `freq` cel·les per costat. Retorna ~[0,1]. */
export function tfbm(u, v, freq, oct = 4, s = 0) {
  let sum = 0; let amp = 0.5; let f = freq; let norm = 0;
  for (let i = 0; i < oct; i += 1) {
    sum += amp * tnoise(u * f, v * f, f, s + i * 3);
    norm += amp; f *= 2; amp *= 0.5;
  }
  return sum / norm;
}

/** fbm no periòdic (terreny). */
export function fbm(x, y, oct = 4, s = 0) {
  let sum = 0; let amp = 0.5; let f = 1; let norm = 0;
  for (let i = 0; i < oct; i += 1) {
    sum += amp * tnoise(x * f, y * f, 1 << 20, s + i * 5);
    norm += amp; f *= 2; amp *= 0.5;
  }
  return sum / norm;
}

export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export function seeded(i) {
  const x = Math.sin(i * 91.137 + 17.41) * 43758.5453;
  return x - Math.floor(x);
}
