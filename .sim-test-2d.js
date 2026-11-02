// Headless smoke test: stubs the browser, runs bot games, reports crashes.
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

const ctxStub = new Proxy({}, {
  get: (t, k) => (k in t ? t[k] : () => ({ addColorStop(){} })),
  set: (t, k, v) => { t[k] = v; return true; },
});
const el = () => ({
  classList: { add(){}, remove(){}, toggle(){} }, style: {}, dataset: {},
  addEventListener(){}, getContext: () => ctxStub, focus(){}, setPointerCapture(){},
  getBoundingClientRect: () => ({ left:0, top:0, width:140, height:140 }),
  innerHTML: '', textContent: '',
});
const intervals = [];
Object.assign(global, {
  intervals, window: global, innerWidth: 1280, innerHeight: 720,
  document: { getElementById: el, querySelectorAll: () => [] },
  addEventListener(){}, matchMedia: () => ({ matches: false }),
  localStorage: { getItem: () => null, setItem(){} },
  requestAnimationFrame(){},
  setInterval: f => intervals.push(f), clearInterval: i => { intervals[i-1] = null; },
});

const test = `
let frames = 0; const out = [];
for (let run = 0; run < 6; run++){
  start();
  while (running && S.t < 400 && frames < 400000){
    if (frames % 45 === 0){
      for (const k of ['KeyW','KeyA','KeyS','KeyD']) keys[k] = Math.random() < 0.4;
      for (const k of ['ShiftLeft','KeyC','Space','KeyE','KeyQ','KeyF']) keys[k] = Math.random() < 0.2;
    }
    if (S.paused){ for (const f of intervals) if (f) f(); continue; }
    update(1/30); if (frames % 7 === 0) draw(); frames++;
    for (const v of [P.x, P.y, P.hp]) if (!Number.isFinite(v)) throw new Error('NaN state at t=' + S.t);
  }
  out.push({ survived: +S.t.toFixed(1), level: S.level, ads: S.ads, helis: helis.length, snipers: helis.filter(h=>h.sniper).length, smokesLeft: P.smoke });
}
// god-mode run to exercise late levels (snipers, 6 choppers)
start(); S.t = 90; let snipeShots = 0, carFrames = 0;
while (S.t < 300){
  if (frames % 45 === 0) for (const k of ['KeyW','KeyA','KeyS','KeyD','ShiftLeft','Space','KeyE','KeyQ','KeyF']) keys[k] = Math.random() < 0.3;
  if (P.car) carFrames++;
  else if (frames % 300 === 0){ // walk the bot up to a car and hop in
    const c = S.w.cars.find(c => !c.dead && c.fuel > 0);
    if (c){ P.x = c.x + 25; P.y = c.y; P.fHeld = false; keys.KeyF = true; }
  }
  P.hp = 100; update(1/30); if (frames % 7 === 0) draw(); frames++;
  snipeShots += bullets.filter(b => b.big && !b.counted && (b.counted = true)).length;
}
out.push({ godRunLevel: S.level, helis: helis.length, snipers: helis.filter(h=>h.sniper).length, snipeShots, carFrames, carsWrecked: S.w.cars.filter(c=>c.dead).length });
console.log(JSON.stringify(out));
`;
vm.runInThisContext(js + test);
