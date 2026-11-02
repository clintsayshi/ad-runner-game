// Headless smoke test for the 3D game: three.js and the DOM are stubbed
// (every call is a no-op), so this checks the GAME LOGIC, not the visuals.
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
let js = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
js = js.replace(/^import .*$/gm, '');

// A value that absorbs any property access, call or `new`.
const any = new Proxy(function(){}, {
  get: (t, k) => k === Symbol.toPrimitive ? () => 0 : (k in t && k !== 'prototype' ? t[k] : any),
  set: () => true,
  apply: () => any,
  construct: () => any,
});
const ctxStub = new Proxy({}, { get: (t, k) => (k in t ? t[k] : () => any), set: (t, k, v) => { t[k] = v; return true; } });
const el = () => ({
  classList: { add(){}, remove(){}, toggle(){} }, style: {}, dataset: {},
  addEventListener(){}, appendChild(){}, getContext: () => ctxStub, focus(){}, setPointerCapture(){},
  getBoundingClientRect: () => ({ left:0, top:0, width:140, height:140 }),
  innerHTML: '', textContent: '', disabled: true, width: 0, height: 0,
});
const intervals = [];
Object.assign(global, {
  THREE: any, Sky: any, Lensflare: any, LensflareElement: any, mergeGeometries: any, mergeVertices: any, intervals, window: global, innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1,
  document: { getElementById: el, querySelectorAll: () => [], createElement: el, addEventListener(){}, pointerLockElement: null, exitPointerLock(){} },
  addEventListener(){}, matchMedia: () => ({ matches: false }), location: { search: '' },
  localStorage: { getItem: () => null, setItem(){} },
  requestAnimationFrame(){},
  setInterval: f => intervals.push(f), clearInterval: i => { intervals[i-1] = null; },
});
vm.runInThisContext(js);

const G = global.__game, keys = G.keys;
const out = [];
let frames = 0;
function tick(){ G.update(1/30); G.sync(1/30); if (frames % 5 === 0) G.drawHUD(); frames++; }
function check(){ for (const v of [G.P.x, G.P.y, G.P.hp]) if (!Number.isFinite(v)) throw new Error('NaN state at t=' + G.S.t); }

for (let run = 0; run < 6; run++){
  G.start();
  while (G.running && G.S.t < 400 && frames < 400000){
    if (frames % 45 === 0){
      for (const k of ['KeyW','KeyA','KeyS','KeyD']) keys[k] = Math.random() < 0.4;
      for (const k of ['ShiftLeft','KeyC','Space','KeyE','KeyQ','KeyF']) keys[k] = Math.random() < 0.2;
    }
    if (G.S.paused){ for (const f of intervals) if (f) f(); continue; }
    tick(); check();
  }
  out.push({ survived: +G.S.t.toFixed(1), level: G.S.level, ads: G.S.ads, helis: G.helis.length });
}

// no-damage run to reach late levels: snipers, 6 choppers, cars
G.start(); G.S.t = 90; let snipeShots = 0, carFrames = 0, bulletsSeen = 0;
while (G.S.t < 300){
  if (frames % 45 === 0) for (const k of ['KeyW','KeyA','KeyS','KeyD','ShiftLeft','Space','KeyE','KeyQ','KeyF']) keys[k] = Math.random() < 0.3;
  if (G.P.car) carFrames++;
  else if (frames % 300 === 0){
    const c = G.S.w.cars.find(c => !c.dead && c.fuel > 0);
    if (c){ G.P.x = c.x + 1.5; G.P.y = c.y; G.P.fHeld = false; keys.KeyF = true; }
  }
  G.P.hp = 100; tick(); check();
  for (const b of G.bullets) if (!b.counted){ b.counted = true; bulletsSeen++; if (b.big) snipeShots++; }
}
out.push({ godRunLevel: G.S.level, helis: G.helis.length, snipers: G.helis.filter(h => h.sniper).length,
           bullets: bulletsSeen, snipeShots, carFrames, carsWrecked: G.S.w.cars.filter(c => c.dead).length,
           treesBurnt: G.S.w.trees.filter(t => t.burnt).length });
console.log(JSON.stringify(out, null, 0));
