// Initial-load JS budget for the admin SPA (run after `vite build`).
// Entry chunk < 300 kB, and everything the sign-in screen loads (entry + modulepreloads) < 400 kB,
// minified, not gzipped. Screens are lazy route chunks (src/App.jsx) and are not counted.
import fs from 'node:fs';
import path from 'node:path';

const dist = path.resolve(process.argv[2] || 'dist');
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const entry = html.match(/<script type="module"[^>]*src="([^"]+)"/)?.[1];
const preloads = [...html.matchAll(/<link rel="modulepreload"[^>]*href="([^"]+)"/g)].map((m) => m[1]);
if (!entry) throw new Error('no module entry in dist/index.html');
const kb = (f) => fs.statSync(path.join(dist, f.replace(/^\//, ''))).size / 1024;
const ENTRY_KB = Number(process.env.ADMIN_ENTRY_BUDGET_KB || 300);
const INITIAL_KB = Number(process.env.ADMIN_INITIAL_BUDGET_KB || 400);
const entryKb = kb(entry);
const total = [entry, ...preloads].reduce((s, f) => s + kb(f), 0);
for (const f of [entry, ...preloads]) console.log(`${kb(f).toFixed(1).padStart(7)} kB  ${f}`);
console.log(`entry ${entryKb.toFixed(1)} kB (budget ${ENTRY_KB}), initial ${total.toFixed(1)} kB (budget ${INITIAL_KB})`);
if (entryKb > ENTRY_KB || total > INITIAL_KB) {
  console.error('admin initial JS over budget: lazy-load the new code (see src/App.jsx)');
  process.exit(1);
}
