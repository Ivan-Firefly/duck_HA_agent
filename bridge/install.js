// Copies the bundled Home Assistant integration into /config/custom_components
// (mounted at /homeassistant) and, if needed, restarts Home Assistant once.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SRC = '/opt/integration/custom_components/duckai_web_search';
const CONFIG_DIR = '/homeassistant';
const DST = path.join(CONFIG_DIR, 'custom_components', 'duckai_web_search');
const log = (m) => console.log(`[duckai] ${m}`);

function digest(dir) {
  const h = crypto.createHash('sha256');
  const walk = (d) => {
    const entries = fs.readdirSync(d, { withFileTypes: true })
      .sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    for (const e of entries) {
      if (e.name === '__pycache__') continue;   // created by Home Assistant itself
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else { h.update(path.relative(dir, p)); h.update(fs.readFileSync(p)); }
    }
  };
  walk(dir);
  return h.digest('hex');
}

function readOptions() {
  try { return JSON.parse(fs.readFileSync('/data/options.json', 'utf8')); } catch { return {}; }
}

function hostUptimeSeconds() {
  try { return Number(fs.readFileSync('/proc/uptime', 'utf8').split(' ')[0]); } catch { return Infinity; }
}

async function restartCore() {
  const token = process.env.SUPERVISOR_TOKEN;
  if (!token) { log('No SUPERVISOR_TOKEN; please restart Home Assistant manually.'); return; }
  try {
    const res = await fetch('http://supervisor/core/restart', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(30000),
    });
    if (res.ok) log('Home Assistant restart requested.');
    else log(`Restart request failed (HTTP ${res.status}); please restart Home Assistant manually.`);
  } catch (e) {
    log(`Restart request failed (${e.message}); please restart Home Assistant manually.`);
  }
}

async function main() {
  if (!fs.existsSync(CONFIG_DIR)) {
    log(`${CONFIG_DIR} is not mounted; integration was not installed. Copy it manually.`);
    return;
  }
  const upToDate = fs.existsSync(DST) && digest(SRC) === digest(DST);
  if (upToDate) { log('Integration is up to date.'); return; }

  fs.rmSync(DST, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(DST), { recursive: true });
  fs.cpSync(SRC, DST, { recursive: true });
  log(`Integration installed/updated in ${DST}`);

  const opts = readOptions();
  if (opts.auto_restart_ha === false) {
    log('Restart Home Assistant to load the integration (auto restart is disabled).');
  } else if (hostUptimeSeconds() < 600) {
    log('Host just booted; Home Assistant will load the new files on its own start.');
  } else {
    await restartCore();
  }
}

await main();
