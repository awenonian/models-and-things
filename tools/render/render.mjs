// Usage: node render.mjs <file.stl> <outprefix> [views...]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const [stl, outPrefix, ...viewArgs] = process.argv.slice(2);
const here0 = path.dirname(new URL(import.meta.url).pathname);
const threeDir = process.env.THREE_DIR || path.join(here0, 'node_modules', 'three');
const here = path.dirname(new URL(import.meta.url).pathname);
const VIEWS = {
  hero:     { eye: [380, 520, 330], target: [0, 10, 70] },
  front:    { eye: [0, 720, 160], target: [0, 0, 90], fov: 30 },
  back:     { eye: [-330, -560, 300], target: [0, -40, 60] },
  top:      { eye: [0, 40, 900], target: [0, 0, 0], fov: 32 },
  arch:     { eye: [-60, 260, 120], target: [0, 0, 120], fov: 40 },
  box:      { eye: [60, 170, 135], target: [160, 0, 125], fov: 40 },
  apron:    { eye: [120, 260, 90], target: [60, 60, 20], fov: 40 },
  backstage:{ eye: [60, -320, 140], target: [60, -70, 40], fov: 40 },
  marquee:  { eye: [20, 160, 200], target: [0, 0, 180], fov: 35 },
  s_hero:   { eye: [-420, -330, 360], target: [0, 150, 20] },
  s_stage:  { eye: [0, -260, 140], target: [0, 200, 40], fov: 40 },
  s_rows:   { eye: [150, 40, 90], target: [60, 160, 20], fov: 40 },
  s_wall:   { eye: [-40, 150, 110], target: [-90, 300, 80], fov: 40 },
  s_pit:    { eye: [-60, -90, 90], target: [-50, 40, 10], fov: 40 },
  s_back:   { eye: [380, 650, 330], target: [0, 150, 30] },
  scene:    { eye: [-620, 900, 520], target: [0, 260, 40], fov: 38 },
  scene2:   { eye: [560, -420, 420], target: [0, 280, 40], fov: 38 },
  s_bal:    { eye: [-150, 90, 170], target: [-20, 215, 90], fov: 40 },
  s_under:  { eye: [70, 110, 60], target: [20, 225, 60], fov: 45 },
  pit:      { eye: [-170, 290, 110], target: [-40, 130, 15], fov: 40 },
  plate:    { eye: [394, -820, 620], target: [394, -110, 0], fov: 38 },
  dove:     { eye: [-40, 120, 120], target: [-88, 0, 158], fov: 30 },
  // Reaper VIP penthouse (origin at the middle of the flat, +Y = north on the map)
  p_top:    { eye: [0, -40, 1500], target: [0, 0, 0], fov: 32 },
  p_hero:   { eye: [-520, -900, 760], target: [0, -20, 0], fov: 38 },
  p_ne:     { eye: [520, 760, 640], target: [0, 20, 0], fov: 38 },
  p_gym:    { eye: [120, 40, 210], target: [-20, 230, 5], fov: 40 },
  p_spa:    { eye: [260, -70, 200], target: [190, 170, 5], fov: 40 },
  p_dining: { eye: [130, -470, 230], target: [40, -170, 5], fov: 40 },
  p_holo:   { eye: [430, -390, 210], target: [280, -150, 5], fov: 40 },
  p_bed:    { eye: [-250, -430, 220], target: [-290, -160, 5], fov: 40 },
  p_kitchen:{ eye: [-10, -240, 200], target: [-50, 0, 5], fov: 40 },
  p_corr:   { eye: [-150, -80, 200], target: [-220, 140, 5], fov: 40 },
  p_sdc:    { eye: [250, -170, 200], target: [290, 30, 5], fov: 40 },
  p_guest:  { eye: [-180, -220, 200], target: [-270, 10, 5], fov: 40 },
  p_paint:  { eye: [300, -150, 45], target: [240, -218, 16], fov: 30 },
  p_plate:  { eye: [531, -1250, 900], target: [531, -142, 0], fov: 40 },
  t_top:    { eye: [0, -30, 420], target: [0, 0, 0], fov: 40 },
  t_low:    { eye: [-160, -240, 160], target: [0, 0, 5], fov: 40 },
  p_piers:  { eye: [140, -350, 120], target: [240, -225, 10], fov: 40 },
  f_south:  { eye: [180, -520, 260], target: [130, -200, 0], fov: 40 },
  f_spa:    { eye: [140, 60, 260], target: [150, 150, 0], fov: 45 },
  f_closet: { eye: [-260, -230, 200], target: [-150, -170, 0], fov: 40 },
  p_bath:   { eye: [-90, -320, 170], target: [-120, -150, 5], fov: 40 },
};
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let f;
  if (u.startsWith('/three/')) f = path.join(threeDir, u.slice(7));
  else if (u === '/model.stl') f = path.resolve(stl);
  else f = path.join(here, u);
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : 'application/octet-stream' });
    res.end(d);
  });
}).listen(0);
const port = server.address().port;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
await page.goto(`http://localhost:${port}/viewer.html`);
await page.waitForFunction(() => window.ready === true);
for (const v of (viewArgs.length ? viewArgs : ['hero'])) {
  const spec = VIEWS[v];
  await page.evaluate(([e, t, f]) => window.renderView('/model.stl', e, t, f), [spec.eye, spec.target, spec.fov]);
  await page.locator('canvas').screenshot({ path: `${outPrefix}_${v}.png` });
  console.log(`${outPrefix}_${v}.png`);
}
await browser.close(); server.close();
