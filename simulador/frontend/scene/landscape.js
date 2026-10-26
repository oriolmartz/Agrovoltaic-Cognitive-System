/* Paisatge: relleu amb serralada al nord, mosaic de parcel·les, boscos instanciats
   (olivera, pi, xiprer, planifoli) i tanca perimetral. */
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { fbm, smooth, clamp, hash2, seeded } from './noise.js';
import { detailTexture } from './textures.js';
import { enableSway } from './sway.js';

export function terrainHeight(x, z) {
  const dx = Math.max(Math.abs(x) - 38, 0);
  const dz = Math.max(Math.abs(z) - 26, 0);
  const d = Math.hypot(dx, dz);
  const mask = smooth(2, 78, d);
  const rolling = (fbm(x * 0.012 + 11, z * 0.012 + 5, 4) - 0.5) * 15;
  const hills = Math.max(0, fbm(x * 0.006 + 3, z * 0.006 + 9, 3) - 0.46) * 62;
  const ridge = smooth(38, 170, z) * (24 + 46 * fbm(x * 0.009 + 20, z * 0.009 + 2, 5));
  const sides = smooth(95, 210, Math.abs(x)) * (10 + 22 * fbm(x * 0.01, z * 0.01 + 40, 3));
  return -0.12 + mask * (rolling + hills + ridge + sides);
}

const PALETTE = [
  [0.52, 0.66, 0.36], [0.47, 0.60, 0.33], [0.72, 0.68, 0.43], [0.61, 0.50, 0.34],
  [0.40, 0.54, 0.30], [0.77, 0.70, 0.49], [0.55, 0.62, 0.30],
];

function buildTerrain() {
  const size = 600;
  const seg = 190;
  const geo = new THREE.PlaneGeometry(size, size, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i += 1) pos.setY(i, terrainHeight(pos.getX(i), pos.getZ(i)));
  geo.computeVertexNormals();
  const nor = geo.attributes.normal;
  const col = new Float32Array(pos.count * 3);
  const ca = Math.cos(0.38); const sa = Math.sin(0.38);
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i); const z = pos.getZ(i); const h = pos.getY(i);
    const xr = x * ca - z * sa; const zr = x * sa + z * ca;
    const cx = Math.floor(xr / 40); const cz = Math.floor(zr / 30);
    const id = hash2(cx, cz, 4);
    const base = PALETTE[Math.floor(id * PALETTE.length)];
    let r = base[0]; let g = base[1]; let b = base[2];
    const fx = (xr / 40) - cx; const fz = (zr / 30) - cz;
    const edge = Math.min(fx, 1 - fx, fz, 1 - fz);
    const hedge = 1 - smooth(0.012, 0.045, edge);
    r = r * (1 - hedge) + 0.26 * hedge; g = g * (1 - hedge) + 0.38 * hedge; b = b * (1 - hedge) + 0.22 * hedge;
    const n = 0.78 + 0.2 * fbm(x * 0.05, z * 0.05, 3, 7);
    r *= n; g *= n; b *= n;
    const slope = 1 - nor.getY(i);
    const scrub = smooth(7, 26, h) * 0.85;
    r = r * (1 - scrub) + 0.30 * scrub; g = g * (1 - scrub) + 0.40 * scrub; b = b * (1 - scrub) + 0.22 * scrub;
    const rock = clamp(smooth(0.22, 0.5, slope) * 0.8 + smooth(38, 60, h) * 0.7, 0, 1);
    r = r * (1 - rock) + 0.40 * rock; g = g * (1 - rock) + 0.38 * rock; b = b * (1 - rock) + 0.34 * rock;
    col[i * 3] = r; col[i * 3 + 1] = g; col[i * 3 + 2] = b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const detail = detailTexture(256, [150, 150]);
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, map: detail, roughness: 1, metalness: 0 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  return { mesh, mat };
}

/* ---------- Arbres (geometria fusionada amb color per vèrtex) ---------- */
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

function oliveGeo() {
  const blob = new THREE.IcosahedronGeometry(1, 1); jitter(blob, 0.28, 1);
  const parts = [part(new THREE.CylinderGeometry(0.13, 0.22, 1.5, 7), '#5e4a38', { pos: [0, 0.75, 0], rot: [0.08, 0, 0.1] })];
  const cols = ['#7e9462', '#8aa06b', '#73895a', '#94a875'];
  for (let i = 0; i < 7; i += 1) {
    const a = (i / 7) * Math.PI * 2; const r = i ? 0.95 : 0;
    parts.push(part(blob, cols[i % 4], { pos: [Math.cos(a) * r, 1.9 + (i % 3) * 0.28, Math.sin(a) * r], scale: [1.15, 0.78, 1.15] }));
  }
  return merge(parts);
}
function pineGeo() {
  const parts = [part(new THREE.CylinderGeometry(0.14, 0.24, 2.2, 7), '#5a4535', { pos: [0, 1.1, 0] })];
  const cols = ['#3b5c3a', '#36563a', '#41653f', '#355238'];
  for (let i = 0; i < 5; i += 1) {
    const c = new THREE.ConeGeometry(1.7 - i * 0.28, 2.1, 9); jitter(c, 0.12, i + 3);
    parts.push(part(c, cols[i % 4], { pos: [0, 2.6 + i * 1.25, 0] }));
  }
  return merge(parts);
}
function cypressGeo() {
  const c = new THREE.ConeGeometry(0.62, 6.2, 10); jitter(c, 0.1, 5);
  const c2 = new THREE.SphereGeometry(0.62, 10, 8);
  return merge([part(new THREE.CylinderGeometry(0.08, 0.12, 0.7, 6), '#53402f', { pos: [0, 0.35, 0] }),
    part(c, '#2e4b38', { pos: [0, 3.7, 0] }), part(c2, '#2e4b38', { pos: [0, 0.9, 0], scale: [1, 1.2, 1] })]);
}
function broadleafGeo() {
  const blob = new THREE.IcosahedronGeometry(1, 1); jitter(blob, 0.3, 2);
  const parts = [part(new THREE.CylinderGeometry(0.16, 0.28, 2.6, 7), '#60493a', { pos: [0, 1.3, 0] })];
  const cols = ['#5f8f45', '#6a9a4c', '#548440', '#76a455'];
  [[0, 3.6, 0, 1.8], [1.1, 3.1, 0.4, 1.3], [-1.0, 3.2, -0.5, 1.4], [0.2, 4.5, -0.3, 1.2], [-0.3, 3.0, 1.1, 1.2]].forEach(([x, y, z, s], i) => {
    parts.push(part(blob, cols[i % 4], { pos: [x, y, z], scale: [s, s * 0.88, s] }));
  });
  return merge(parts);
}

function plantTrees(group) {
  const geos = { olive: oliveGeo(), pine: pineGeo(), cypress: cypressGeo(), broad: broadleafGeo() };
  const mats = {};
  Object.keys(geos).forEach((k) => {
    mats[k] = enableSway(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }), k === 'cypress' ? 0.006 : 0.012);
  });
  const list = { olive: [], pine: [], cypress: [], broad: [] };
  const inFarm = (x, z) => Math.abs(x) < 38 && Math.abs(z) < 26;
  // Bosc i oliverars escampats pel paisatge
  for (let i = 0; i < 900; i += 1) {
    const a = seeded(i * 3 + 1); const b = seeded(i * 7 + 2);
    const x = (a - 0.5) * 420; const z = (b - 0.5) * 420 + 40;
    if (inFarm(x, z) || Math.hypot(x, z) < 44) continue;
    const grove = fbm(x * 0.02 + 5, z * 0.02 + 8, 3, 3);
    if (grove < 0.5) continue;
    const h = terrainHeight(x, z);
    if (h > 30) continue;
    const t = seeded(i * 11 + 3);
    const kind = h > 14 ? 'pine' : t < 0.46 ? 'olive' : t < 0.7 ? 'broad' : t < 0.88 ? 'pine' : 'cypress';
    list[kind].push([x, h, z, 0.8 + seeded(i * 13 + 4) * 0.8]);
  }
  // Cortina de xiprers al nord de la finca + oliveres a la vora
  for (let x = -34; x <= 34; x += 3.6) list.cypress.push([x + (seeded(x * 3) - 0.5), 0, 27.5 + seeded(x * 5) * 1.2, 1.0 + seeded(x * 7) * 0.45]);
  for (let i = 0; i < 16; i += 1) {
    const side = i % 2 ? 1 : -1;
    list.olive.push([side * (40 + seeded(i * 5) * 12), terrainHeight(side * 44, -14 + i * 2.2), -16 + seeded(i * 9) * 38, 0.9 + seeded(i * 3) * 0.5]);
  }
  const m = new THREE.Matrix4(); const q = new THREE.Quaternion(); const e = new THREE.Euler(); const col = new THREE.Color();
  Object.entries(list).forEach(([k, arr]) => {
    if (!arr.length) return;
    const im = new THREE.InstancedMesh(geos[k], mats[k], arr.length);
    arr.forEach(([x, y, z, s], i) => {
      e.set(0, seeded(i * 17 + k.length) * Math.PI * 2, 0);
      q.setFromEuler(e);
      m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(s, s * (0.9 + seeded(i + 3) * 0.3), s));
      im.setMatrixAt(i, m);
      col.setScalar(0.82 + seeded(i * 19 + 5) * 0.32);
      im.setColorAt(i, col);
    });
    im.castShadow = true; im.receiveShadow = false; im.frustumCulled = false;
    group.add(im);
  });
}

function buildFence(group) {
  const wood = new THREE.MeshStandardMaterial({ color: 0x7f6648, roughness: 0.9 });
  const wire = new THREE.MeshStandardMaterial({ color: 0x9aa4a8, metalness: 0.7, roughness: 0.4 });
  const xs = 34; const zs = 22;
  const pts = [];
  for (let x = -xs; x <= xs + 0.01; x += 3.4) { pts.push([x, -zs]); pts.push([x, zs]); }
  for (let z = -zs + 3.4; z < zs - 0.5; z += 3.4) { pts.push([-xs, z]); pts.push([xs, z]); }
  const posts = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.045, 0.06, 1.45, 6), wood, pts.length);
  const m = new THREE.Matrix4();
  pts.forEach(([x, z], i) => { m.makeTranslation(x, 0.72, z); posts.setMatrixAt(i, m); });
  posts.castShadow = true; posts.frustumCulled = false;
  group.add(posts);
  const rail = (len, x, y, z, rotY) => {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, len, 4), wire);
    r.rotation.z = Math.PI / 2; r.rotation.y = rotY; r.position.set(x, y, z); group.add(r);
  };
  [0.5, 0.95, 1.38].forEach((y) => {
    rail(xs * 2, 0, y, -zs, 0); rail(xs * 2, 0, y, zs, 0);
    rail(zs * 2, -xs, y, 0, Math.PI / 2); rail(zs * 2, xs, y, 0, Math.PI / 2);
  });
}

export function createLandscape() {
  const group = new THREE.Group();
  const { mesh, mat } = buildTerrain();
  group.add(mesh);
  plantTrees(group);
  buildFence(group);
  return { group, terrainMat: mat };
}

/** Mates d'herba instanciades dins la finca (fora dels bancals i del camí). */
export function createGrass() {
  const blade = new THREE.ConeGeometry(0.026, 0.36, 3);
  const parts = [];
  for (let i = 0; i < 7; i += 1) {
    const a = (i / 7) * Math.PI * 2;
    parts.push(part(blade, '#ffffff', { pos: [Math.cos(a) * 0.05, 0.22, Math.sin(a) * 0.05], rot: [Math.sin(a) * 0.35, a, Math.cos(a) * 0.35], scale: [1, 0.8 + (i % 3) * 0.2, 1] }));
  }
  const geo = merge(parts);
  const p = geo.attributes.position; const col = geo.attributes.color;
  const base = new THREE.Color('#5a7a3a'); const tip = new THREE.Color('#b7cf78'); const c = new THREE.Color();
  for (let i = 0; i < p.count; i += 1) {
    c.copy(base).lerp(tip, clamp(p.getY(i) / 0.38, 0, 1));
    col.setXYZ(i, c.r, c.g, c.b);
  }
  const mat = enableSway(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, side: THREE.DoubleSide }), 0.4);
  const spots = [];
  const inBed = (x, z) => [-13, 0, 13].some((sx) => Math.abs(x - sx) < 6.1 && Math.abs(z) < 6.8);
  const inPath = (x, z) => z < -8.4 && z > -12;
  for (let i = 0; i < 16000 && spots.length < 5200; i += 1) {
    const x = (seeded(i * 3 + 11) - 0.5) * 68; const z = (seeded(i * 7 + 5) - 0.5) * 44;
    if (inBed(x, z) || inPath(x, z)) continue;
    // més densitat a les vores i al voltant dels bancals
    const edge = Math.min(Math.abs(Math.abs(x) - 34), Math.abs(Math.abs(z) - 22));
    if (edge > 6 && seeded(i * 13 + 2) > 0.3) continue;
    spots.push([x, z, 0.7 + seeded(i * 17 + 9) * 0.9]);
  }
  const im = new THREE.InstancedMesh(geo, mat, spots.length);
  const m = new THREE.Matrix4(); const q = new THREE.Quaternion(); const e = new THREE.Euler(); const cc = new THREE.Color();
  spots.forEach(([x, z, s], i) => {
    q.setFromEuler(e.set(0, seeded(i * 19 + 3) * Math.PI * 2, 0));
    m.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(s, s * (0.8 + seeded(i * 23 + 1) * 0.6), s));
    im.setMatrixAt(i, m);
    cc.setScalar(0.8 + seeded(i * 29 + 4) * 0.35);
    im.setColorAt(i, cc);
  });
  im.receiveShadow = true; im.frustumCulled = false;
  return im;
}
