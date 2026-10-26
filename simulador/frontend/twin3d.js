import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { PMREMGenerator } from 'three';
import { actionCategory, actionLabel, cropLabel, sectorLabel } from './ui.js';
import { clamp, lerp, smooth, seeded } from './scene/noise.js';
import { grassTextures, soilTextures, gravelTextures, panelTexture, dropTexture, flowTexture, wetStripeTexture } from './scene/textures.js';
import { createSky, createCloud, createSunGlow, createEnvScene } from './scene/sky.js';
import { createLandscape, createGrass } from './scene/landscape.js';
import { createCropField } from './scene/crops.js';
import { SWAY } from './scene/sway.js';

const DEG = Math.PI / 180;

/* Orientació: el sol és al sud (-z). La càmera mira des del sud, amb el sol a
   l'esquena, de manera que els panells i els cultius queden il·luminats. */
const PRESETS = {
  overview: { pos: [28, 17, -30], target: [0, 1.5, 0] },
  solar: { pos: [16, 7.5, -17], target: [0, 2.4, 0] },
  crop: { pos: [9, 3.0, -15], target: [0, 0.9, 0] },
  top: { pos: [0.1, 38, -4], target: [0, 0, 0] },
};
const SECTOR_X = { Sector_1: -13, Sector_2: 0, Sector_3: 13 };

const COL = {
  dayTop: new THREE.Color(0x3d83d4), dayHor: new THREE.Color(0xbfe1f6),
  cloudTop: new THREE.Color(0x8797a6), cloudHor: new THREE.Color(0xc6ced3),
  twiTop: new THREE.Color(0x4a6aa8), twiHor: new THREE.Color(0xf6b27a),
  nightTop: new THREE.Color(0x070f23), nightHor: new THREE.Color(0x1a2b48),
  sunWhite: new THREE.Color(0xfff0ce), sunWarm: new THREE.Color(0xff9a52),
  soilDry: new THREE.Color(0xffffff), soilWet: new THREE.Color(0x7d7264),
  white: new THREE.Color(0xffffff), cropDry: new THREE.Color(0xe9d98f),
  borderOk: new THREE.Color(0x8b6a47), borderRisk: new THREE.Color(0xd2694f),
  ghostOk: new THREE.Color(0xb4c0bb), ghostOff: new THREE.Color(0xf4b942),
  cloudWhite: new THREE.Color(0xffffff), cloudWarm: new THREE.Color(0xffc9a0), cloudNight: new THREE.Color(0x1d2740),
};

/* ---------- Materials compartits ---------- */
const SHARED = {};
const shared = (key, make) => (SHARED[key] ??= make());
const metalMat = () => shared('metal', () => new THREE.MeshStandardMaterial({ color: 0x9aa5a8, metalness: 0.8, roughness: 0.38 }));
const concreteMat = () => shared('concrete', () => new THREE.MeshStandardMaterial({ color: 0xa7a8a2, roughness: 0.95 }));

function panelMaterials() {
  return shared('panelMats', () => {
    const top = new THREE.MeshPhysicalMaterial({
      map: panelTexture(), metalness: 0.2, roughness: 0.22, clearcoat: 1.0, clearcoatRoughness: 0.05, envMapIntensity: 1.7,
    });
    const frame = new THREE.MeshStandardMaterial({ color: 0xcbd3d8, metalness: 0.85, roughness: 0.32 });
    const back = new THREE.MeshStandardMaterial({ color: 0xe4e7e8, roughness: 0.6 });
    return [frame, frame, top, back, frame, frame];
  });
}

function createPanelRig(panelId, sectorId) {
  const root = new THREE.Group();
  root.userData = { sector: sectorId, panel: panelId, kind: 'panel-rig' };
  const metal = metalMat();

  const postGeo = shared('postGeo', () => new THREE.CylinderGeometry(0.085, 0.1, 2.3, 12));
  const footGeo = shared('footGeo', () => new THREE.CylinderGeometry(0.2, 0.24, 0.14, 12));
  const bracketGeo = shared('bracketGeo', () => new THREE.BoxGeometry(0.26, 0.12, 0.34));
  [-1.75, 1.75].forEach((x) => {
    const post = new THREE.Mesh(postGeo, metal);
    post.position.set(x, 1.15, 0);
    post.castShadow = true; post.receiveShadow = true;
    root.add(post);
    const foot = new THREE.Mesh(footGeo, concreteMat());
    foot.position.set(x, 0.07, 0);
    foot.castShadow = true; foot.receiveShadow = true;
    root.add(foot);
    const br = new THREE.Mesh(bracketGeo, metal);
    br.position.set(x, 2.3, 0);
    br.castShadow = true;
    root.add(br);
  });

  const pivot = new THREE.Group();
  pivot.position.y = 2.42;
  root.add(pivot);

  const tube = new THREE.Mesh(shared('tubeGeo', () => new THREE.CylinderGeometry(0.075, 0.075, 5.3, 12)), metal);
  tube.rotation.z = Math.PI / 2;
  tube.position.y = -0.1;
  tube.castShadow = true;
  pivot.add(tube);
  const clampGeo = shared('clampGeo', () => new THREE.BoxGeometry(0.18, 0.1, 0.5));
  [-1.9, 0, 1.9].forEach((x) => {
    const c = new THREE.Mesh(clampGeo, metal);
    c.position.set(x, -0.065, 0);
    pivot.add(c);
  });
  const motor = new THREE.Mesh(shared('motorGeo', () => new THREE.BoxGeometry(0.34, 0.3, 0.3)), shared('motorMat', () => new THREE.MeshStandardMaterial({ color: 0x31393d, roughness: 0.5, metalness: 0.4 })));
  motor.position.set(-2.55, -0.1, 0);
  motor.castShadow = true;
  pivot.add(motor);

  const panelGroup = new THREE.Group();
  const panel = new THREE.Mesh(new THREE.BoxGeometry(5.45, 0.07, 2.28), panelMaterials());
  panel.castShadow = true;
  panel.receiveShadow = true;
  panel.userData = { sector: sectorId, panel: panelId, kind: 'solar-panel' };
  panelGroup.add(panel);
  pivot.add(panelGroup);

  /* Posició òptima (fantasma): s'escalfa de color quan el panell se n'allunya. */
  const optimumPivot = new THREE.Group();
  optimumPivot.position.y = 2.42;
  const ghostMat = new THREE.MeshBasicMaterial({ color: 0xb4c0bb, wireframe: true, transparent: true, opacity: 0.18, depthWrite: false });
  const ghost = new THREE.Mesh(new THREE.BoxGeometry(5.65, 0.05, 2.45), ghostMat);
  optimumPivot.add(ghost);
  root.add(optimumPivot);

  return { root, pivot, optimumPivot, panel, ghost };
}

/* ---------- Reg per degoteig: sortidors d'aigua, franges d'humitat, canonades amb flux i vàlvula amb LED ---------- */
let DROP_TEX = null;

function createIrrigation(sectorId, rowsX) {
  DROP_TEX ??= dropTexture();
  const group = new THREE.Group();
  const pipeMat = shared('pipeMat', () => new THREE.MeshStandardMaterial({ color: 0x4f6f86, metalness: 0.45, roughness: 0.5 }));
  const flowTex = flowTexture(10.6 / 1.2);
  const manMat = new THREE.MeshStandardMaterial({ color: 0x4f6f86, metalness: 0.45, roughness: 0.5, emissive: 0x4ec0ff, emissiveMap: flowTex, emissiveIntensity: 0 });
  const manifold = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 10.6, 12), manMat);
  manifold.rotation.z = Math.PI / 2;
  manifold.position.set(0, 0.12, 6.45);
  manifold.castShadow = true;
  group.add(manifold);

  const valveMat = new THREE.MeshStandardMaterial({ color: 0x1f2a30, roughness: 0.5, emissive: 0x55b8ee, emissiveIntensity: 0 });
  const valve = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.36, 0.42), shared('valveBox', () => new THREE.MeshStandardMaterial({ color: 0x2c3a40, roughness: 0.55, metalness: 0.3 })));
  valve.position.set(0, 0.22, 6.95);
  valve.castShadow = true;
  group.add(valve);
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 10), valveMat);
  led.position.set(0, 0.46, 6.95);
  group.add(led);
  const branch = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.9, 8), pipeMat);
  branch.rotation.x = Math.PI / 2;
  branch.position.set(0, 0.12, 6.9);
  group.add(branch);

  /* Franges d'humitat sobre les files (es veuen sota el reg). */
  const wetTex = wetStripeTexture();
  const wetMat = new THREE.MeshBasicMaterial({ map: wetTex, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, color: 0x6cc2ff });
  const wet = new THREE.Mesh(new THREE.PlaneGeometry(10.4, 11.8), wetMat);
  wet.rotation.x = -Math.PI / 2;
  wet.position.set(0, 0.11, 0);
  wet.renderOrder = 2;
  group.add(wet);

  const count = 1900;
  const positions = new Float32Array(count * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({ color: 0x8ad4ff, size: 0.3, map: DROP_TEX, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  points.renderOrder = 3;
  group.add(points);
  group.userData = { sector: sectorId };

  const irr = { group, points, positions, seeds: [], valveMat, manMat, flowTex, wetMat, wet, strength: 0, targetStrength: 0 };
  irr.setRows = (xs) => {
    irr.seeds = Array.from({ length: count }, (_, i) => ({
      x: xs[i % xs.length] + 0.12,
      z: -5.6 + Math.floor(seeded(i * 3 + 1) * 19) * 0.6 + (seeded(i * 13 + 6) - 0.5) * 0.1,
      ang: seeded(i * 5 + 2) * Math.PI * 2,
      rad: 0.2 + seeded(i * 7 + 3) * 0.55,
      H: 0.45 + seeded(i * 17 + 5) * 0.85,
      phase: seeded(i * 11 + 4),
    }));
    const step = xs.length > 1 ? Math.abs(xs[1] - xs[0]) : 1.15;
    wetTex.repeat.set(xs.length, 1);
    wet.scale.x = Math.min(1, (xs.length * step) / 10.4);
    wet.geometry.dispose();
    wet.geometry = new THREE.PlaneGeometry(Math.min(10.4, xs.length * step), 11.8);
    wet.scale.x = 1;
  };
  irr.setRows(rowsX);
  return irr;
}

export class DigitalTwin3D {
  constructor(container, tooltipEl = null) {
    this.container = container;
    this.tooltipEl = tooltipEl;
    this.onPick = null;
    this.state = null;
    this.elapsed = 0;
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.pickables = [];
    this.sectors = new Map();
    this.clouds = [];
    this.groundMats = [];
    this.rainStrength = 0;
    this.targetRain = 0;
    this.wind = 0;
    this.windStrength = 0;
    this.cloudiness = 0;
    this.targetCloudiness = 0;
    this.daylight = 0.85;
    this.targetDaylight = 0.85;
    this.sunElevation = 45;
    this.sunAzimuth = 180;
    this.selected = null;
    this.hovered = null;
    this._visible = true;
    this._dark = 0;
    this._twi = 0;
    this._envT = 0;

    const coarse = window.matchMedia?.('(pointer: coarse)').matches;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xbfe1f6);
    this.scene.fog = new THREE.FogExp2(0xbfe1f6, 0.0033);

    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 700);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.className = 'tag-layer';
    this.labelRenderer.domElement.style.pointerEvents = 'none';
    this.container.appendChild(this.labelRenderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.055;
    this.controls.minDistance = 9;
    this.controls.maxDistance = 85;
    this.controls.maxPolarAngle = Math.PI / 2.03;

    this.sky = createSky();
    this.scene.add(this.sky);
    this.sunGlow = createSunGlow();
    this.scene.add(this.sunGlow);

    /* Reflexos reals: el cel es converteix en mapa d'entorn (PMREM) i es refresca
       quan el sol o els núvols canvien prou. */
    this.pmrem = new PMREMGenerator(this.renderer);
    this.env = createEnvScene(this.sky.material);

    this.hemi = new THREE.HemisphereLight(0xcfe8ff, 0x6f765b, 1.0);
    this.scene.add(this.hemi);
    this.sunLight = new THREE.DirectionalLight(0xfff0ce, 3.4);
    this.sunLight.castShadow = true;
    const sm = coarse ? 2048 : 4096;
    this.sunLight.shadow.mapSize.set(sm, sm);
    const sc = this.sunLight.shadow.camera;
    sc.left = -36; sc.right = 36; sc.top = 30; sc.bottom = -30; sc.near = 0.5; sc.far = 140;
    this.sunLight.shadow.bias = -0.00012;
    this.sunLight.shadow.normalBias = 0.03;
    this.scene.add(this.sunLight);
    this.scene.add(this.sunLight.target);
    this.sunLight.target.position.set(0, 0, 0);

    const land = createLandscape();
    this.scene.add(land.group);
    this.groundMats.push(land.terrainMat);

    this._buildWorld();
    this._buildWeather();
    this._buildWind();
    this._bindResize();
    this._bindPicking();
    this.setCameraPreset('overview', true);
    this.setDefaultCrops();

    if ('IntersectionObserver' in window) {
      this._io = new IntersectionObserver(([entry]) => { this._visible = entry.isIntersecting; });
      this._io.observe(this.container);
    }
    this._animate = this._animate.bind(this);
    this._last = performance.now();
    this._updateSun(0.016);
    this._refreshEnv();
    this._animate(this._last);
  }

  /* ---------- Escena ---------- */
  _buildWorld() {
    const grass = grassTextures(512, [68 / 7, 44 / 7]);
    const farmMat = new THREE.MeshStandardMaterial({ map: grass.map, normalMap: grass.normalMap, normalScale: new THREE.Vector2(0.7, 0.7), roughness: 1 });
    const terrain = new THREE.Mesh(new THREE.PlaneGeometry(68, 44, 1, 1), farmMat);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    this.scene.add(terrain);
    this.groundMats.push(farmMat);

    const gravel = gravelTextures(512, [58 / 6, 1]);
    const pathMat = new THREE.MeshStandardMaterial({ map: gravel.map, normalMap: gravel.normalMap, roughness: 0.97 });
    const path = new THREE.Mesh(new THREE.PlaneGeometry(58, 3.2), pathMat);
    path.rotation.x = -Math.PI / 2;
    path.position.set(0, 0.014, -10.2);
    path.receiveShadow = true;
    this.scene.add(path);
    this.groundMats.push(pathMat);

    const soil = soilTextures(512, [11 / 1.15, 3]);
    const borderMat = new THREE.MeshStandardMaterial({ color: 0x8b6a47, roughness: 0.88, emissive: 0xe8745f, emissiveIntensity: 0 });

    const sectorXs = [-13, 0, 13];
    ['Sector_1', 'Sector_2', 'Sector_3'].forEach((sectorId, idx) => {
      const group = new THREE.Group();
      group.position.x = sectorXs[idx];
      this.scene.add(group);

      const soilMat = new THREE.MeshStandardMaterial({ map: soil.map, normalMap: soil.normalMap, normalScale: new THREE.Vector2(1.1, 1.1), roughness: 0.95 });
      const bed = new THREE.Mesh(new THREE.BoxGeometry(11, 0.34, 12), soilMat);
      bed.position.y = 0.22;
      bed.receiveShadow = true;
      bed.userData = { sector: sectorId, kind: 'soil' };
      group.add(bed);
      this.pickables.push(bed);

      /* Vora de fusta (es tenyeix quan hi ha risc). */
      const sectBorderMat = borderMat.clone();
      const boards = [[0, -6.1, 11.7, 0.16], [0, 6.1, 11.7, 0.16], [-5.6, 0, 0.16, 12.2], [5.6, 0, 0.16, 12.2]];
      boards.forEach(([x, z, w, d]) => {
        const b = new THREE.Mesh(new THREE.BoxGeometry(w, 0.42, d), sectBorderMat);
        b.position.set(x, 0.21, z);
        b.castShadow = true; b.receiveShadow = true;
        group.add(b);
      });

      /* Contorn de selecció/hover. */
      const outlineMat = new THREE.LineBasicMaterial({ color: 0xf6c453, transparent: true, opacity: 0, depthTest: false });
      const outline = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(11.9, 0.5, 12.9)), outlineMat);
      outline.position.y = 0.3;
      outline.renderOrder = 5;
      group.add(outline);

      const cropContainer = new THREE.Group();
      cropContainer.position.y = 0.39;
      group.add(cropContainer);

      const rig1 = createPanelRig(`${sectorId}_P1`, sectorId);
      rig1.root.position.set(0, 0.38, -2.75);
      group.add(rig1.root);
      const rig2 = createPanelRig(`${sectorId}_P2`, sectorId);
      rig2.root.position.set(0, 0.38, 2.75);
      group.add(rig2.root);
      this.pickables.push(rig1.panel, rig2.panel);

      const irrigation = createIrrigation(sectorId, [0]);
      irrigation.group.position.set(0, 0.3, 0);
      group.add(irrigation.group);

      /* Etiqueta HTML dins l'escena (vora sud del sector). */
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'tag';
      el.dataset.sector = sectorId;
      el.innerHTML = '<i class="tag-dot"></i><span class="tag-name"></span><span class="tag-crop"></span><span class="tag-act"></span><span class="tag-irr"></span>';
      el.querySelector('.tag-name').textContent = sectorLabel(sectorId);
      el.addEventListener('click', (ev) => { ev.stopPropagation(); this.onPick?.(sectorId); });
      el.addEventListener('pointerenter', () => { this.hovered = sectorId; });
      el.addEventListener('pointerleave', () => { if (this.hovered === sectorId) this.hovered = null; });
      const label = new CSS2DObject(el);
      label.position.set(0, 0.5, -7.7);
      group.add(label);

      this.sectors.set(sectorId, {
        id: sectorId,
        group, bed, soilMat, borderMat: sectBorderMat, outlineMat,
        cropContainer, cropField: null, cropType: null,
        rigs: [rig1, rig2], irrigation, tag: el,
        currentAngle: 0, targetAngle: 0,
        currentOptimal: 0, targetOptimal: 0,
        currentWetness: 0.45, targetWetness: 0.45,
        riskLevel: 0, targetRisk: 0,
        action: '', risk: '', shown: {},
      });
    });

    /* Canonada principal des de la caseta de bombament fins a cada vàlvula. */
    const pipeMat = shared('pipeMat', () => new THREE.MeshStandardMaterial({ color: 0x4f6f86, metalness: 0.45, roughness: 0.5 }));
    this.mainFlow = flowTexture(37.4 / 1.2);
    this.mainMat = new THREE.MeshStandardMaterial({ color: 0x4f6f86, metalness: 0.45, roughness: 0.5, emissive: 0x4ec0ff, emissiveMap: this.mainFlow, emissiveIntensity: 0 });
    const main = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 37.4, 12), this.mainMat);
    main.rotation.z = Math.PI / 2;
    main.position.set(5, 0.1, 7.25);
    main.castShadow = true;
    this.scene.add(main);
    this.scene.add(createGrass());
    const feed = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 1.9, 10), pipeMat);
    feed.rotation.x = Math.PI / 2;
    feed.position.set(23.7, 0.1, 8.2);
    this.scene.add(feed);

    /* Dipòsit d'aigua i caseta de bombament (s'il·lumina quan hi ha reg). */
    this.tankMat = new THREE.MeshStandardMaterial({ color: 0xc4ccd0, metalness: 0.55, roughness: 0.38, emissive: 0x52b5ea, emissiveIntensity: 0 });
    const tank = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 2.8, 28), this.tankMat);
    tank.position.set(28, 1.4, 9.2);
    tank.castShadow = true; tank.receiveShadow = true;
    this.scene.add(tank);
    [0.5, 1.4, 2.3].forEach((y) => {
      const band = new THREE.Mesh(new THREE.TorusGeometry(1.5, 0.035, 6, 28), metalMat());
      band.rotation.x = Math.PI / 2; band.position.set(28, y, 9.2); this.scene.add(band);
    });
    const cap = new THREE.Mesh(new THREE.ConeGeometry(1.6, 0.7, 28), metalMat());
    cap.position.set(28, 3.15, 9.2);
    cap.castShadow = true;
    this.scene.add(cap);
    const ladder = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.9, 0.06), metalMat());
    ladder.position.set(26.55, 1.45, 9.2);
    this.scene.add(ladder);
    const hut = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.8, 2.2), new THREE.MeshStandardMaterial({ color: 0xdcd7c8, roughness: 0.92 }));
    hut.position.set(24.2, 0.9, 9.4);
    hut.castShadow = true; hut.receiveShadow = true;
    this.scene.add(hut);
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.4, 0.06), new THREE.MeshStandardMaterial({ color: 0x4a5a5e, roughness: 0.6, metalness: 0.4 }));
    door.position.set(24.2, 0.72, 8.28);
    this.scene.add(door);
    const roof = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.18, 2.6), new THREE.MeshStandardMaterial({ color: 0x8c5a43, roughness: 0.85 }));
    roof.position.set(24.2, 1.9, 9.4);
    roof.castShadow = true;
    this.scene.add(roof);
  }

  _buildWeather() {
    for (let i = 0; i < 10; i += 1) {
      const c = createCloud(i);
      this.scene.add(c);
      this.clouds.push(c);
    }
    /* Pluja: ratlles curtes inclinades pel vent (el nom rainPoints es manté). */
    const count = 2600;
    this.rainPositions = new Float32Array(count * 6);
    this.rainHead = new Float32Array(count * 3);
    this.rainSeeds = new Float32Array(count);
    for (let i = 0; i < count; i += 1) {
      this.rainHead[i * 3] = -34 + seeded(i * 7) * 68;
      this.rainHead[i * 3 + 1] = 0.5 + seeded(i * 11) * 22;
      this.rainHead[i * 3 + 2] = -22 + seeded(i * 17) * 44;
      this.rainSeeds[i] = seeded(i * 23);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.rainPositions, 3));
    this.rainMaterial = new THREE.LineBasicMaterial({ color: 0xbcdcef, transparent: true, opacity: 0, depthWrite: false });
    this.rainPoints = new THREE.LineSegments(geo, this.rainMaterial);
    this.rainPoints.frustumCulled = false;
    this.scene.add(this.rainPoints);
  }

  /* Ratxes de vent: fan visible el context de les decisions de seguretat. */
  _buildWind() {
    const count = 170;
    this.windSeeds = [];
    this.windPos = new Float32Array(count * 6);
    for (let i = 0; i < count; i += 1) {
      this.windSeeds.push({ x: seeded(i * 3 + 1) * 70 - 35, y: 0.8 + seeded(i * 5 + 2) * 6.6, z: -16 + seeded(i * 7 + 3) * 32, v: 0.7 + seeded(i * 11 + 4) * 0.6 });
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.windPos, 3));
    this.windMat = new THREE.LineBasicMaterial({ color: 0xf2f9ff, transparent: true, opacity: 0, depthWrite: false });
    this.windLines = new THREE.LineSegments(geo, this.windMat);
    this.windLines.frustumCulled = false;
    this.windLines.visible = false;
    this.scene.add(this.windLines);
  }

  _bindResize() {
    const resize = () => {
      const w = Math.max(1, this.container.clientWidth);
      const h = Math.max(1, this.container.clientHeight);
      this.camera.aspect = w / h;
      this.camera.fov = w / h < 1.25 ? 40 + (1.25 - w / h) * 42 : 40;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
      this.labelRenderer.setSize(w, h);
    };
    this.resizeObserver = new ResizeObserver(resize);
    this.resizeObserver.observe(this.container);
    resize();
  }

  _pick(event) {
    const canvas = this.renderer.domElement;
    const rect = canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.pickables, false);
    return { hit: hits[0] || null, rect };
  }

  _bindPicking() {
    const canvas = this.renderer.domElement;
    let down = null;
    canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; });
    canvas.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      down = null;
      if (moved > 5) return;
      const { hit } = this._pick(e);
      this.onPick?.(hit ? hit.object.userData.sector : null);
    });
    canvas.addEventListener('pointermove', (event) => {
      const { hit, rect } = this._pick(event);
      this.hovered = hit ? hit.object.userData.sector : null;
      canvas.style.cursor = hit ? 'pointer' : 'grab';
      if (!this.tooltipEl) return;
      if (!hit) { this.tooltipEl.hidden = true; return; }
      const data = hit.object.userData || {};
      const sector = data.sector ? this.sectors.get(data.sector) : null;
      const lines = [];
      if (data.sector) lines.push(`<strong>${sectorLabel(data.sector)}${data.panel ? ` · ${data.panel.replace(/^.*_P/, 'Panell ')}` : ''}</strong>`);
      if (sector) {
        lines.push(`<span>${sector.action ? actionLabel(sector.action) : 'Sense dades'}</span>`);
        if (data.kind === 'solar-panel') lines.push(`<span>Angle ${sector.currentAngle.toFixed(0)}° · òptim ${sector.currentOptimal.toFixed(0)}°</span>`);
        if (sector.risk) lines.push('<span class="risk">Risc actiu</span>');
      }
      this.tooltipEl.innerHTML = lines.join('');
      this.tooltipEl.style.left = `${Math.min(event.clientX - rect.left + 16, rect.width - 190)}px`;
      this.tooltipEl.style.top = `${event.clientY - rect.top + 16}px`;
      this.tooltipEl.hidden = false;
    });
    canvas.addEventListener('pointerleave', () => { this.hovered = null; if (this.tooltipEl) this.tooltipEl.hidden = true; });
  }

  /* ---------- API pública ---------- */
  setDefaultCrops() {
    const defaults = { Sector_1: 'tomaquet', Sector_2: 'enciam', Sector_3: 'vinya' };
    Object.entries(defaults).forEach(([id, crop]) => {
      const s = this.sectors.get(id);
      this._ensureCrop(s, crop);
      this._setTag(s, { crop: cropLabel(crop), action: '', cat: '', risk: false, water: false });
    });
  }

  _ensureCrop(sector, cropType) {
    const normalized = String(cropType || 'tomaquet').toLowerCase();
    if (sector.cropType === normalized) return;
    if (sector.cropField) {
      sector.cropContainer.remove(sector.cropField.group);
      sector.cropField.group.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    }
    sector.cropField = createCropField(normalized);
    sector.cropContainer.add(sector.cropField.group);
    sector.irrigation.setRows(sector.cropField.rowsX);
    sector.cropType = normalized;
  }

  _setTag(sector, { crop, action, cat, risk, water, irr = '' }) {
    const el = sector.tag;
    const sh = sector.shown;
    if (sh.irr !== irr) { el.querySelector('.tag-irr').textContent = irr; sh.irr = irr; }
    if (sh.crop !== crop) { el.querySelector('.tag-crop').textContent = crop; sh.crop = crop; }
    if (sh.action !== action) { el.querySelector('.tag-act').textContent = action; sh.action = action; }
    if (sh.cat !== cat) { el.dataset.cat = cat; sh.cat = cat; }
    if (sh.risk !== risk) { el.classList.toggle('risk', risk); sh.risk = risk; }
    if (sh.water !== water) { el.classList.toggle('water', water); sh.water = water; }
  }

  setSelected(name) {
    this.selected = name || null;
    this.sectors.forEach((s, id) => s.tag.classList.toggle('selected', id === this.selected));
  }

  focusSector(name) {
    const x = SECTOR_X[name];
    if (x === undefined) { this.setCameraPreset('overview'); return; }
    this._animateCamera([x + 11, 7.5, -17.5], [x, 1.7, 0]);
  }

  setState(frame) {
    if (!frame) return;
    this.state = frame;
    const g = frame.globals || {};
    this.targetRain = clamp((Number(g.rain || 0) / 3.0), 0, 1);
    this.targetCloudiness = clamp(Number(g.cloud || 0), 0, 1);
    this.wind = Math.max(0, Number(g.wind || 0));
    this.targetDaylight = clamp((Number(g.elevation || 0) + 14) / 62, 0.12, 1);
    this.sunElevation = Number(g.elevation || 0);
    this.sunAzimuth = Number(g.azimuth || 180);

    frame.sectors.forEach((s, name) => {
      const sector = this.sectors.get(name);
      if (!sector) return;
      this._ensureCrop(sector, s.cultiu);
      sector.targetAngle = Number(s.angle_real || 0);
      sector.targetOptimal = Number(s.angle_optim || 0);
      sector.targetWetness = clamp(Number(s.aigua_pct || 0) / 100, 0, 1);
      sector.irrigation.targetStrength = clamp(Number(s.reg_mm || 0) / 4, 0, 1);
      sector.action = s.accio || '';
      sector.risk = s.riscos || s.impas || '';
      sector.targetRisk = sector.risk ? 1 : 0;
      this._setTag(sector, {
        crop: cropLabel(s.cultiu),
        action: actionLabel(s.accio),
        cat: actionCategory(s.accio),
        risk: Boolean(sector.risk),
        water: Number(s.reg_mm || 0) > 0.05,
        irr: Number(s.reg_mm || 0) > 0.05 ? (Number(s.reg_dosi_pct) > 0.5 ? `Regant · ${Math.round(s.reg_dosi_pct)} %` : 'Regant') : '',
      });
    });
  }

  setCameraPreset(name, immediate = false) {
    const p = PRESETS[name] || PRESETS.overview;
    if (immediate) {
      this.camera.position.set(...p.pos);
      this.controls.target.set(...p.target);
      this.controls.update();
      return;
    }
    this._animateCamera(p.pos, p.target);
  }

  _animateCamera(pos, target) {
    this.cameraAnim = {
      fromPos: this.camera.position.clone(),
      toPos: new THREE.Vector3(...pos),
      fromTarget: this.controls.target.clone(),
      toTarget: new THREE.Vector3(...target),
      t: 0,
    };
  }

  /* ---------- Bucle ---------- */
  _refreshEnv() {
    const dir = this.sky.material.uniforms.sunDir.value.clone().normalize();
    this.env.sun.position.copy(dir).multiplyScalar(88);
    this.env.sun.visible = this.sunElevation > -2 && this.cloudiness < 0.85;
    this.env.ground.material.color.copy(this.scene.fog.color).multiplyScalar(0.5).lerp(new THREE.Color(0x5f7a4c), 0.5);
    const rt = this.pmrem.fromScene(this.env.scene, 0, 1, 400);
    this.scene.environment = rt.texture;
    this._envRT?.dispose();
    this._envRT = rt;
    this._envState = { el: this.sunElevation, az: this.sunAzimuth, cl: this.cloudiness };
    this._envT = performance.now();
  }

  _updateSun(dt) {
    const k = (r) => 1 - Math.exp(-dt * r);
    this.cloudiness = lerp(this.cloudiness, this.targetCloudiness, k(2.2));
    this.daylight = lerp(this.daylight, this.targetDaylight, k(2.6));
    const elDeg = this.sunElevation;
    const elev = elDeg * DEG;
    const az = this.sunAzimuth * DEG;
    const r = 52;
    const horiz = Math.cos(elev) * r;
    const x = Math.sin(az) * horiz;
    const z = Math.cos(az) * horiz;
    const yTrue = Math.sin(elev) * r;
    const y = Math.max(4, yTrue);
    this.sunLight.position.set(x, y, z);

    const cl = this.cloudiness;
    const dark = smooth(6, -10, elDeg);
    const twi = clamp(1 - Math.abs(elDeg - 4) / 16, 0, 1) * (1 - cl * 0.55);
    this._dark = dark; this._twi = twi;

    const pm = panelMaterials()[2];
    pm.envMapIntensity = 1.7 * (1 - 0.7 * cl);
    pm.roughness = 0.22 + 0.32 * cl;
    pm.clearcoat = 1 - 0.5 * cl;
    this.sunLight.intensity = clamp(0.18 + this.daylight * 3.9 * (1 - cl * 0.68), 0.1, 4.2);
    this.sunLight.color.copy(COL.sunWhite).lerp(COL.sunWarm, smooth(24, 2, elDeg) * (1 - cl * 0.5));
    this.hemi.intensity = 0.7 + this.daylight * (1 - cl * 0.28) * 0.8;
    this.scene.environmentIntensity = 0.12 + this.daylight * (1 - cl * 0.5) * 0.55;

    const u = this.sky.material.uniforms;
    u.top.value.copy(COL.dayTop).lerp(COL.cloudTop, cl * 0.8).lerp(COL.twiTop, twi * 0.5).lerp(COL.nightTop, dark);
    u.horizon.value.copy(COL.dayHor).lerp(COL.cloudHor, cl * 0.8).lerp(COL.twiHor, twi * 0.85).lerp(COL.nightHor, dark);
    u.sunDir.value.set(x, yTrue, z);
    u.glowAmt.value = (0.35 + twi * 0.9) * (1 - cl * 0.8) * (1 - dark);
    u.glow.value.copy(COL.sunWhite).lerp(COL.sunWarm, twi);
    this.scene.fog.color.copy(u.horizon.value);
    this.scene.background.copy(u.horizon.value);
    this.hemi.color.copy(u.top.value).lerp(COL.white, 0.45);
    this.renderer.toneMappingExposure = 0.86 + this.daylight * 0.4;

    /* Disc solar: resplendor additiu darrere del cel. */
    const d = new THREE.Vector3(x, yTrue, z).normalize().multiplyScalar(175);
    this.sunGlow.position.copy(d);
    this.sunGlow.visible = elDeg > -3 && cl < 0.95;
    this.sunGlow.material.opacity = clamp((1 - dark) * (1 - cl * 0.85), 0, 1) * (0.55 + twi * 0.4);
    this.sunGlow.material.color.copy(COL.sunWhite).lerp(COL.sunWarm, twi);
    this.sunGlow.scale.setScalar(70 + twi * 70);

    /* Entorn PMREM: només si ha canviat prou i com a màxim cada 450 ms. */
    const st = this._envState;
    if (st && performance.now() - this._envT > 450 && (Math.abs(elDeg - st.el) > 1.5 || Math.abs(this.sunAzimuth - st.az) > 4 || Math.abs(cl - st.cl) > 0.08)) this._refreshEnv();
  }

  _updateClouds(dt) {
    const speed = 0.7 + this.wind * 0.12;
    const cl = this.cloudiness;
    const col = COL.cloudWhite.clone().lerp(COL.cloudWarm, this._twi * 0.8).lerp(COL.cloudNight, this._dark);
    this.clouds.forEach((cloud) => {
      cloud.position.x += dt * speed * cloud.userData.speed;
      if (cloud.position.x > 240) cloud.position.x = -240;
      cloud.children.forEach((sp) => {
        sp.material.opacity = clamp((0.14 + cl * 0.95) * sp.userData.k, 0, 0.95) * (1 - this._dark * 0.45);
        sp.material.color.copy(col);
      });
    });
  }

  _updateRain(dt) {
    this.rainStrength = lerp(this.rainStrength, this.targetRain, 1 - Math.exp(-dt * 6));
    this.rainMaterial.opacity = this.rainStrength * 0.6;
    this.rainPoints.visible = this.rainStrength > 0.01;
    const wet = this.rainStrength;
    this.groundMats.forEach((m) => { m.color.setScalar(1 - 0.24 * wet); });
    if (!this.rainPoints.visible) return;
    const h = this.rainHead; const out = this.rainPositions;
    const drift = this.wind * 0.07;
    for (let i = 0; i < this.rainSeeds.length; i += 1) {
      const v = (14 + this.rainSeeds[i] * 10) * (0.8 + wet * 0.7);
      h[i * 3 + 1] -= dt * v;
      h[i * 3] += dt * v * drift * 0.25;
      if (h[i * 3 + 1] < 0.1) {
        h[i * 3 + 1] = 16 + this.rainSeeds[i] * 8;
        h[i * 3] = -34 + seeded(i * 29 + Math.floor(this.elapsed * 3)) * 68;
      }
      if (h[i * 3] > 36) h[i * 3] = -36;
      const L = 0.55 + wet * 0.5;
      out[i * 6] = h[i * 3]; out[i * 6 + 1] = h[i * 3 + 1]; out[i * 6 + 2] = h[i * 3 + 2];
      out[i * 6 + 3] = h[i * 3] - drift * 0.25 * L; out[i * 6 + 4] = h[i * 3 + 1] + L; out[i * 6 + 5] = h[i * 3 + 2];
    }
    this.rainPoints.geometry.attributes.position.needsUpdate = true;
  }

  _updateWind(dt) {
    const target = clamp((this.wind - 4) / 11, 0, 1);
    this.windStrength = lerp(this.windStrength, target, 1 - Math.exp(-dt * 3));
    this.windMat.opacity = this.windStrength * 0.5;
    this.windLines.visible = this.windStrength > 0.03;
    if (!this.windLines.visible) return;
    const speed = 6 + this.wind * 1.2;
    const len = 0.9 + this.windStrength * 2.8;
    const arr = this.windPos;
    for (let i = 0; i < this.windSeeds.length; i += 1) {
      const s = this.windSeeds[i];
      s.x += dt * speed * s.v;
      if (s.x > 35) s.x -= 70;
      arr[i * 6] = s.x; arr[i * 6 + 1] = s.y; arr[i * 6 + 2] = s.z;
      arr[i * 6 + 3] = s.x - len; arr[i * 6 + 4] = s.y; arr[i * 6 + 5] = s.z;
    }
    this.windLines.geometry.attributes.position.needsUpdate = true;
  }

  _updateIrrigation(irrig, dt) {
    irrig.strength = lerp(irrig.strength, irrig.targetStrength, 1 - Math.exp(-dt * 6));
    const k = irrig.strength;
    irrig.points.material.opacity = k * 0.95;
    irrig.points.visible = k > 0.015;
    irrig.valveMat.emissiveIntensity = k * 3;
    irrig.manMat.emissiveIntensity = k * 1.8;
    irrig.wetMat.opacity = k * 0.5 * (0.85 + 0.15 * Math.sin(this.elapsed * 3));
    irrig.flowTex.offset.y -= dt * 1.4 * k;
    if (!irrig.points.visible) return;
    const arr = irrig.positions;
    for (let i = 0; i < irrig.seeds.length; i += 1) {
      const s = irrig.seeds[i];
      const t = (this.elapsed * 0.95 + s.phase) % 1;
      arr[i * 3] = s.x + Math.cos(s.ang) * s.rad * t + this.wind * 0.01 * t;
      arr[i * 3 + 2] = s.z + Math.sin(s.ang) * s.rad * t;
      arr[i * 3 + 1] = 0.1 + s.H * 4 * t * (1 - t);
    }
    irrig.points.geometry.attributes.position.needsUpdate = true;
  }

  _updateSectors(dt) {
    const k = (r) => 1 - Math.exp(-dt * r);
    let irrigating = 0;
    this.sectors.forEach((sector, id) => {
      sector.currentAngle = lerp(sector.currentAngle, sector.targetAngle, k(4.5));
      sector.currentOptimal = lerp(sector.currentOptimal, sector.targetOptimal, k(4.5));
      sector.currentWetness = lerp(sector.currentWetness, sector.targetWetness, k(2.0));
      sector.riskLevel = lerp(sector.riskLevel, sector.targetRisk, k(3));
      const dev = clamp(Math.abs(sector.currentAngle - sector.currentOptimal) / 35, 0, 1);
      sector.rigs.forEach((rig) => {
        rig.pivot.rotation.x = sector.currentAngle * DEG;
        rig.optimumPivot.rotation.x = sector.currentOptimal * DEG;
        rig.ghost.material.opacity = 0.16 + dev * 0.55;
        rig.ghost.material.color.copy(COL.ghostOk).lerp(COL.ghostOff, smooth(0.1, 0.35, dev));
      });
      const wet = clamp(sector.currentWetness * 0.9 + this.rainStrength * 0.14, 0, 1);
      sector.soilMat.color.copy(COL.soilDry).lerp(COL.soilWet, smooth(0.15, 0.95, wet));
      sector.soilMat.roughness = lerp(sector.soilMat.roughness, clamp(0.97 - sector.currentWetness * 0.36, 0.55, 0.97), k(2.2));
      /* El cultiu s'esgroguoeix quan el sòl s'asseca (estrès hídric). */
      const dry = smooth(0.42, 0.18, sector.currentWetness);
      sector.cropField?.mats.forEach((m) => m.color.copy(COL.white).lerp(COL.cropDry, dry * 0.7));
      sector.borderMat.color.copy(COL.borderOk).lerp(COL.borderRisk, sector.riskLevel * 0.55);
      sector.borderMat.emissiveIntensity = sector.riskLevel * 0.12;
      const want = id === this.selected ? 0.95 : id === this.hovered ? 0.5 : 0;
      sector.outlineMat.opacity = lerp(sector.outlineMat.opacity, want, k(10));
      this._updateIrrigation(sector.irrigation, dt);
      irrigating = Math.max(irrigating, sector.irrigation.strength);
    });
    this.tankMat.emissiveIntensity = lerp(this.tankMat.emissiveIntensity, irrigating * 0.6, k(5));
    this.mainMat.emissiveIntensity = lerp(this.mainMat.emissiveIntensity, irrigating * 1.6, k(5));
    this.mainFlow.offset.y -= dt * 1.4 * irrigating;
  }

  _updateCamera(dt) {
    if (!this.cameraAnim) return;
    this.cameraAnim.t = clamp(this.cameraAnim.t + dt * 1.35, 0, 1);
    const t = 1 - Math.pow(1 - this.cameraAnim.t, 3);
    this.camera.position.lerpVectors(this.cameraAnim.fromPos, this.cameraAnim.toPos, t);
    this.controls.target.lerpVectors(this.cameraAnim.fromTarget, this.cameraAnim.toTarget, t);
    if (this.cameraAnim.t >= 1) this.cameraAnim = null;
  }

  _animate(now) {
    requestAnimationFrame(this._animate);
    const dt = clamp((now - this._last) / 1000, 0, 0.05);
    this._last = now;
    if (!this._visible) return;
    this.elapsed += dt;
    SWAY.uTime.value = this.elapsed;
    SWAY.uWind.value = clamp(this.wind / 18, 0, 1.1);
    this._updateSun(dt);
    this._updateClouds(dt);
    this._updateRain(dt);
    this._updateWind(dt);
    this._updateSectors(dt);
    this._updateCamera(dt);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
    if (!this._ready) { this._ready = true; this.container.dispatchEvent(new CustomEvent('twin-ready')); }
  }
}
