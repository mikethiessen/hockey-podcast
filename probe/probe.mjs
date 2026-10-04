import { chromium } from 'playwright';
import fs from 'fs';
const TEAM = 'Nz7BgbzbxfrhWtft';
const urls = [
  `https://canlanstats.sportninja.com/team/${TEAM}/statistics`,
  `https://canlanstats.sportninja.com/team/${TEAM}/statistics?sn_schedule=d6ieKFuhvhmS8Q7y&sn_sort=desc`,
  `https://canlanstats.sportninja.com/team/${TEAM}?sn_schedule=d6ieKFuhvhmS8Q7y`,
];
fs.mkdirSync('probe/out', { recursive: true });
const browser = await chromium.launch();
const log = [];
let n = 0;
for (const url of urls) {
  const page = await browser.newPage();
  page.on('response', async (r) => {
    const u = r.url();
    if (!/sportninja/.test(u) || /\.(js|css|png|svg|woff2?|ico)(\?|$)/.test(u)) return;
    let body = '';
    try { body = (await r.text()).slice(0, 6000); } catch {}
    const f = `probe/out/resp${n++}.json`;
    fs.writeFileSync(f, body);
    log.push({ page: url, status: r.status(), method: r.request().method(), url: u, file: f });
  });
  try { await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }); await page.waitForTimeout(3000); }
  catch (e) { log.push({ page: url, error: String(e) }); }
  fs.writeFileSync(`probe/out/page${urls.indexOf(url)}.txt`, (await page.innerText('body').catch(()=>'')).slice(0, 6000));
  await page.close();
}
fs.writeFileSync('probe/out/log.json', JSON.stringify(log, null, 2));
await browser.close();
