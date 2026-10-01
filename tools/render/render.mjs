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
  dove:     { eye: [-40, 120, 120], target: [-88, 0, 158], fov: 30 },
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
