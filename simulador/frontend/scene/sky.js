/* Cel: degradat zenit-horitzó, resplendor solar, núvols en sprites, disc solar i
   escena d'entorn (per als reflexos reals del cel als panells). */
import * as THREE from 'three';
import { seeded } from './noise.js';
import { cloudTexture, glowTexture } from './textures.js';

export function createSky() {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    toneMapped: false,
    uniforms: {
      top: { value: new THREE.Color(0x3f86d6) },
      horizon: { value: new THREE.Color(0xbfe0f5) },
      glow: { value: new THREE.Color(0xffd9a0) },
      sunDir: { value: new THREE.Vector3(0, 1, 0) },
      glowAmt: { value: 0.4 },
    },
    vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `
      uniform vec3 top; uniform vec3 horizon; uniform vec3 glow; uniform vec3 sunDir; uniform float glowAmt;
      varying vec3 vDir;
      void main(){
        float h = clamp(vDir.y, 0.0, 1.0);
        vec3 col = mix(horizon, top, pow(h, 0.5));
        float s = max(dot(normalize(vDir), normalize(sunDir)), 0.0);
        col += glow * (pow(s, 5.0) * 0.30 + pow(s, 80.0) * 0.95) * glowAmt;
        col = mix(col, horizon, smoothstep(0.0, -0.2, vDir.y));
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(190, 32, 20), mat);
  dome.renderOrder = -10;
  return dome;
}

let CLOUD_TEX = null;

/** Un núvol = cúmul de sprites. S'enlaira i es tenyeix amb l'hora (twin3d). */
export function createCloud(idx) {
  CLOUD_TEX ??= cloudTexture();
  const g = new THREE.Group();
  const n = 6 + Math.floor(seeded(idx * 5) * 4);
  for (let i = 0; i < n; i += 1) {
    const mat = new THREE.SpriteMaterial({ map: CLOUD_TEX, transparent: true, depthWrite: false, fog: false, opacity: 0 });
    const sp = new THREE.Sprite(mat);
    const w = 34 + seeded(idx * 13 + i) * 30;
    sp.scale.set(w, w * 0.5, 1);
    sp.position.set((i - n / 2) * 15 * (0.7 + seeded(idx * 3 + i) * 0.5), (seeded(idx * 17 + i) - 0.4) * 7, (seeded(idx * 19 + i) - 0.5) * 12);
    sp.userData.k = 0.55 + seeded(idx * 23 + i) * 0.45;
    g.add(sp);
  }
  g.userData = { speed: 0.5 + seeded(idx * 29) * 0.7 };
  g.position.set(-190 + idx * 52, 62 + seeded(idx * 7) * 26, 80 + (idx % 4) * 34);
  return g;
}

export function createSunGlow() {
  const mat = new THREE.SpriteMaterial({ map: glowTexture(), transparent: true, depthWrite: false, fog: false, blending: THREE.AdditiveBlending, opacity: 0.9 });
  const sp = new THREE.Sprite(mat);
  sp.scale.setScalar(90);
  sp.renderOrder = -5;
  return sp;
}

/** Escena lleugera (cel + terra) que només serveix per generar l'entorn PMREM. */
export function createEnvScene(skyMaterial) {
  const sc = new THREE.Scene();
  sc.add(new THREE.Mesh(new THREE.SphereGeometry(100, 24, 16), skyMaterial));
  const gnd = new THREE.Mesh(new THREE.CircleGeometry(100, 24), new THREE.MeshBasicMaterial({ color: 0x6f8c5a, side: THREE.DoubleSide }));
  gnd.rotation.x = -Math.PI / 2;
  gnd.position.y = -0.5;
  sc.add(gnd);
  const sun = new THREE.Mesh(new THREE.SphereGeometry(4.2, 12, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(14, 12, 9), toneMapped: false }));
  sc.add(sun);
  return { scene: sc, sun, ground: gnd };
}
