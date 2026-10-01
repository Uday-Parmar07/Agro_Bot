/* Pre-renders the public pages to static HTML after `npm run build`, so
   crawlers and link previews (WhatsApp, Facebook, X) see real content and
   per-page meta tags without running JavaScript.

   Output, read by serve_frontend() in backend/app/main.py:
     build/index.html   — "/"        (pre-rendered)
     build/login.html   — "/login"   (pre-rendered)
     build/signup.html  — "/signup"  (pre-rendered)
     build/app.html     — the untouched CRA shell, for the logged-in app and 404s

   Usage: CHROME_PATH=/usr/bin/chromium node scripts/prerender.js */
const fs = require('fs');
const http = require('http');
const path = require('path');
const puppeteer = require('puppeteer-core');

const BUILD_DIR = path.resolve(__dirname, '..', 'build');
const SHELL = path.join(BUILD_DIR, 'app.html');
const PAGES = [
  ['/', 'index.html'],
  ['/login', 'login.html'],
  ['/signup', 'signup.html'],
];

const TYPES = {
  '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon', '.txt': 'text/plain', '.xml': 'application/xml',
};

// Keep a pristine copy of the CRA shell; re-runs render from it, not from a snapshot.
if (!fs.existsSync(SHELL)) {
  fs.copyFileSync(path.join(BUILD_DIR, 'index.html'), SHELL);
}

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url.split('?')[0]);
  const file = path.join(BUILD_DIR, urlPath);
  const isAsset = file.startsWith(BUILD_DIR) && urlPath !== '/'
    && fs.existsSync(file) && fs.statSync(file).isFile();
  const target = isAsset ? file : SHELL;
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(target)] || 'application/octet-stream' });
  fs.createReadStream(target).pipe(res);
});

(async () => {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  try {
    for (const [route, outFile] of PAGES) {
      const page = await browser.newPage();
      await page.setRequestInterception(true);
      // Only the local build: no analytics hits, fonts or API calls at build time.
      page.on('request', (r) => (r.url().startsWith(origin) ? r.continue() : r.abort()));

      await page.goto(`${origin}${route}`, { waitUntil: 'networkidle0', timeout: 60000 });
      await page.waitForFunction(
        () => document.querySelector('#root > *') && !document.querySelector('.loading-screen'),
        { timeout: 30000 },
      );
      const html = await page.evaluate(() => `<!DOCTYPE html>${document.documentElement.outerHTML}`);
      const title = await page.title();
      if (route !== '/' && !title.includes('AgroBot')) {
        throw new Error(`${route} rendered without its page title: "${title}"`);
      }

      fs.writeFileSync(path.join(BUILD_DIR, outFile), html);
      console.log(`prerendered ${route} -> build/${outFile} (${title})`);
      await page.close();
    }
  } finally {
    await browser.close();
    server.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
