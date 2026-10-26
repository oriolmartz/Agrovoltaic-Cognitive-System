/* Cultius realistes: cada planta és una geometria fusionada (color per vèrtex) i
   cada camp és un InstancedMesh (centenars de plantes en 1-4 crides de dibuix). */
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { hash2, seeded } from './noise.js';
import { enableSway } from './sway.js';

function jitter(geo, amt, seed) {
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i += 1) {
    const x = p.getX(i); const y = p.getY(i); const z = p.getZ(i);
    p.setXYZ(i, x + (hash2(x * 7.3 + seed, y * 5.1 + z * 3.7) - 0.5) * amt,
      y + (hash2(y * 6.1 + seed, z * 4.3 + x * 2.9) - 0.5) * amt,
      z + (hash2(z * 5.7 + seed, x * 3.1 + y * 6.7) - 0.5) * amt);
  }
}

function part(geo, color, { pos = [0, 0, 0], rot = [0, 0, 0], scale = [1, 1, 1] } = {}) {
  const g = geo.index ? geo.toNonIndexed() : geo.clone();
  g.applyMatrix4(new THREE.Matrix4().compose(
    new THREE.Vector3(...pos), new THREE.Quaternion().setFromEuler(new THREE.Euler(...rot)), new THREE.Vector3(...scale)));
  const c = new THREE.Color(color);
  const n = g.attributes.position.count;
  const arr = new Float32Array(n * 3);
  for (let i = 0; i < n; i += 1) { arr[i * 3] = c.r; arr[i * 3 + 1] = c.g; arr[i * 3 + 2] = c.b; }
  g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  g.deleteAttribute('uv');
  return g;
}
const merge = (parts) => mergeGeometries(parts, false);

/* ---------- Plantes ---------- */
export function lettucePlant() {
  const leaf = new THREE.IcosahedronGeometry(0.2, 1);
  jitter(leaf, 0.05, 1);
  const parts = [];
  const rings = [
    [8, 0.17, 0.35, 1.0, 0.09, '#4a8c44'],
    [7, 0.12, 0.62, 0.86, 0.15, '#68a954'],
    [6, 0.075, 0.95, 0.72, 0.21, '#8ec462'],
    [4, 0.035, 1.2, 0.55, 0.26, '#b4da7c'],
  ];
  rings.forEach(([n, rad, tilt, sc, y, col], ri) => {
    for (let i = 0; i < n; i += 1) {
      const a = (i / n) * Math.PI * 2 + ri * 0.55;
      parts.push(part(leaf, col, { pos: [Math.cos(a) * rad, y, Math.sin(a) * rad], rot: [0, -a, tilt * 0.8], scale: [1.45 * sc, 0.34, 0.95 * sc] }));
    }
  });
  return merge(parts);
}

export function tomatoPlant() {
  const parts = [];
  parts.push(part(new THREE.CylinderGeometry(0.016, 0.022, 1.0, 6), '#5b8f45', { pos: [0, 0.5, 0] }));
  parts.push(part(new THREE.CylinderGeometry(0.012, 0.014, 1.45, 5), '#b99a6a', { pos: [0.09, 0.72, 0.03] }));   // tutor
  const leaf = new THREE.SphereGeometry(0.11, 7, 5);
  const cols = ['#3d8739', '#4a9645', '#34772f'];
  for (let i = 0; i < 12; i += 1) {
    const a = i * 2.4; const y = 0.18 + (i / 12) * 0.85; const r = 0.13 + (i % 3) * 0.03;
    parts.push(part(leaf, cols[i % 3], { pos: [Math.cos(a) * r, y, Math.sin(a) * r], rot: [0, -a, -0.35], scale: [2.1, 0.22, 1.15] }));
  }
  const fruit = new THREE.SphereGeometry(0.058, 8, 6);
  [[0.1, 0.34, 0.06, '#d2402d'], [-0.09, 0.46, 0.08, '#d8512f'], [0.07, 0.6, -0.1, '#c93a29'], [-0.07, 0.72, -0.07, '#9bbd4f'],
    [0.11, 0.84, 0.05, '#86b04a'], [-0.1, 0.28, -0.06, '#d94a2e']].forEach(([x, y, z, c]) => parts.push(part(fruit, c, { pos: [x, y, z] })));
  return merge(parts);
}

/** Ceps: soc, braços (cordó) al llarg de l'eix de la fila (z), brots, fulles i raïms. */
export function vinePlant() {
  const parts = [];
  parts.push(part(new THREE.CylinderGeometry(0.045, 0.065, 0.85, 7), '#6d5236', { pos: [0, 0.43, 0] }));
  parts.push(part(new THREE.CylinderGeometry(0.025, 0.03, 1.5, 6), '#6d5236', { pos: [0, 0.86, 0], rot: [Math.PI / 2, 0, 0] }));
  const blob = new THREE.IcosahedronGeometry(0.2, 1);
  jitter(blob, 0.08, 3);
  const cols = ['#4c873c', '#5a9645', '#6aa650', '#437c35'];
  for (let i = 0; i < 22; i += 1) {
    const zz = (hash2(i, 1, 9) - 0.5) * 1.5;
    const xx = (hash2(i, 2, 9) - 0.5) * 0.4;
    const yy = 0.95 + hash2(i, 3, 9) * 0.65;
    const s = 0.8 + hash2(i, 4, 9) * 0.7;
    parts.push(part(blob, cols[i % 4], { pos: [xx, yy, zz], scale: [s, s * 0.85, s * 1.05] }));
  }
  const grape = new THREE.SphereGeometry(0.036, 6, 5);
  const gc = ['#43346e', '#52417f', '#3a2c60'];
  for (let b = 0; b < 5; b += 1) {
    const bz = (hash2(b, 5, 9) - 0.5) * 1.2; const bx = (hash2(b, 6, 9) - 0.5) * 0.25;
    for (let k = 0; k < 9; k += 1) {
      parts.push(part(grape, gc[(b + k) % 3], { pos: [bx + (hash2(k, b, 2) - 0.5) * 0.09, 0.74 - (k / 9) * 0.17, bz + (hash2(k, b, 3) - 0.5) * 0.09] }));
    }
  }
  return merge(parts);
}

/* ---------- Camp ---------- */
const FIELDS = {
  enciam: { rows: 9, gx: 1.15, step: 0.62, maker: lettucePlant, scale: [0.9, 1.15], yaw: true, support: null },
  tomaquet: { rows: 9, gx: 1.15, step: 0.86, maker: tomatoPlant, scale: [0.88, 1.12], yaw: true, support: 'tomato' },
  vinya: { rows: 5, gx: 2.3, step: 1.5, maker: vinePlant, scale: [0.92, 1.08], yaw: false, support: 'vine' },
};

export function cropKind(type) {
  const t = String(type || '').toLowerCase();
  return t.includes('enciam') ? 'enciam' : t.includes('vinya') ? 'vinya' : 'tomaquet';
}

export function createCropField(type) {
  const kind = cropKind(type);
  const cfg = FIELDS[kind];
  const group = new THREE.Group();
  const mats = [];
  const rowsX = Array.from({ length: cfg.rows }, (_, k) => (k - (cfg.rows - 1) / 2) * cfg.gx);

  const zs = [];
  const n = Math.floor(10.6 / cfg.step) + 1;
  for (let i = 0; i < n; i += 1) zs.push(-5.3 + (i * 10.6) / (n - 1));

  const mat = enableSway(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82 }), kind === 'vinya' ? 0.06 : 0.16);
  mats.push(mat);
  const mesh = new THREE.InstancedMesh(cfg.maker(), mat, rowsX.length * zs.length);
  const m = new THREE.Matrix4(); const q = new THREE.Quaternion(); const e = new THREE.Euler(); const col = new THREE.Color();
  let idx = 0;
  rowsX.forEach((x, r) => zs.forEach((z, i) => {
    const s = cfg.scale[0] + seeded(r * 31 + i * 7) * (cfg.scale[1] - cfg.scale[0]);
    e.set(0, cfg.yaw ? seeded(r * 13 + i * 5) * Math.PI * 2 : (seeded(r + i) - 0.5) * 0.2, 0);
    q.setFromEuler(e);
    m.compose(new THREE.Vector3(x + (seeded(r * 3 + i) - 0.5) * 0.06, 0, z + (seeded(r + i * 3) - 0.5) * 0.1), q, new THREE.Vector3(s, s * (0.92 + seeded(i * 11 + r) * 0.2), s));
    mesh.setMatrixAt(idx, m);
    col.setScalar(0.86 + seeded(r * 17 + i * 3) * 0.28);
    mesh.setColorAt(idx, col);
    idx += 1;
  }));
  mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false;
  group.add(mesh);

  /* Cinta de reg per degoteig a cada fila. */
  const tapeMat = new THREE.MeshStandardMaterial({ color: 0x1d2225, roughness: 0.6 });
  const tape = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.017, 0.017, 12.2, 6), tapeMat, rowsX.length);
  rowsX.forEach((x, i) => {
    q.setFromEuler(e.set(Math.PI / 2, 0, 0));
    m.compose(new THREE.Vector3(x + 0.12, 0.03, 0), q, new THREE.Vector3(1, 1, 1));
    tape.setMatrixAt(i, m);
  });
  tape.frustumCulled = false;
  group.add(tape);

  /* Suports: fil superior dels tomaquets / espatllera de la vinya. */
  const wood = new THREE.MeshStandardMaterial({ color: 0x8a6b45, roughness: 0.9 });
  const wire = new THREE.MeshStandardMaterial({ color: 0xa4adb1, metalness: 0.7, roughness: 0.4 });
  const lineGeo = new THREE.CylinderGeometry(0.008, 0.008, 11.4, 4);
  if (cfg.support === 'tomato') {
    rowsX.forEach((x) => {
      const w = new THREE.Mesh(lineGeo, wire);
      w.rotation.x = Math.PI / 2; w.position.set(x + 0.09, 1.42, 0); group.add(w);
    });
  } else if (cfg.support === 'vine') {
    const postGeo = new THREE.CylinderGeometry(0.05, 0.06, 1.95, 7);
    rowsX.forEach((x) => {
      [-5.3, 0, 5.3].forEach((z) => {
        const p = new THREE.Mesh(postGeo, wood);
        p.position.set(x, 0.97, z); p.castShadow = true; group.add(p);
      });
      [0.78, 1.18, 1.6].forEach((y) => {
        const w = new THREE.Mesh(lineGeo, wire);
        w.rotation.x = Math.PI / 2; w.position.set(x, y, 0); group.add(w);
      });
    });
  }
  return { group, kind, rowsX, mats };
}
