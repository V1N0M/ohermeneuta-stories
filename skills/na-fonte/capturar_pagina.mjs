// Captura a página real (print) + coordenadas das frases citadas. Uso: node capturar_pagina.mjs <url> cfg.json  -> page.png, rects.json, page_text.txt
// cfg: {titleRe, passages:{id:'trecho exato'}, names:[] (tarja opcional), vw:520 (layout de celular)}. Imagens grandes da página são omitidas (direitos de imagem).
let pw; try { pw = await import('playwright'); } catch { pw = await import(process.env.PLAYWRIGHT_MJS || '/opt/node22/lib/node_modules/playwright/index.mjs'); }
const chromium = pw.chromium || pw.default.chromium;
import fs from 'fs';
const [url, cfgPath] = process.argv.slice(2); const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8')); const DSF = 3;
const b = await chromium.launch({ proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--ignore-certificate-errors'] });
const p = await (await b.newContext({ viewport: { width: cfg.vw || 1280, height: 900 }, deviceScaleFactor: DSF, ignoreHTTPSErrors: true, locale: 'pt-BR' })).newPage();
await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {}); await p.waitForTimeout(2500); await p.addStyleTag({ content: '[vw],[vw-access-button],[vw-plugin-wrapper],[class*="vpw"],[class*="vlibras"],[id*="vlibras"],[class*="access-button"]{display:none!important}' });
const out = await p.evaluate(({ passages, names, titleRe }) => {
  document.querySelectorAll('*').forEach(e => { const s = getComputedStyle(e); if (s.position === 'fixed' || s.position === 'sticky') e.remove(); });
  const h = [...document.querySelectorAll('h1,h2,h3')].find(e => new RegExp(titleRe).test(e.textContent)); let root = h; while (root && root.innerText.length < 3000) root = root.parentElement;
  // foto omitida
  const imgs = [...root.querySelectorAll('img')].filter(i => i.naturalWidth > 500);
  imgs.forEach(i => { const r = i.getBoundingClientRect(); const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${r.width}' height='${r.height}'><rect width='100%' height='100%' fill='#1b2433'/><text x='50%' y='50%' fill='#9fb0c8' font-family='sans-serif' font-size='22' text-anchor='middle'>Imagem do original omitida</text></svg>`; i.removeAttribute('srcset'); i.style.width = r.width + 'px'; i.style.height = r.height + 'px'; i.src = 'data:image/svg+xml;utf8,' + encodeURIComponent(svg); });
  // tarja nos nomes
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); const tn = []; while (names.length && tw.nextNode()) tn.push(tw.currentNode);
  const re = new RegExp('(' + (names.length ? names.join('|') : 'ZZZNEVERZZZ') + ')', 'g'); let nt = 0;
  tn.forEach(n => { if (!re.test(n.nodeValue)) return; re.lastIndex = 0; const f = document.createDocumentFragment(); let last = 0, m; const v = n.nodeValue;
    while ((m = re.exec(v))) { f.append(v.slice(last, m.index)); const s = document.createElement('span'); s.textContent = m[0]; s.style.cssText = 'background:#0b1220;color:#0b1220;border-radius:3px;box-decoration-break:clone'; f.append(s); last = m.index + m[0].length; nt++; }
    f.append(v.slice(last)); n.parentNode.replaceChild(f, n); });
  // índice de texto normalizado
  const w2 = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let s = ''; const map = [];
  while (w2.nextNode()) { const n = w2.currentNode; if (['SCRIPT', 'STYLE'].includes(n.parentNode.tagName)) continue; const t = n.nodeValue;
    for (let i = 0; i < t.length; i++) { const c = t[i]; if (c === '​') continue; if (/\s/.test(c)) { if (s.length && s[s.length - 1] !== ' ') { s += ' '; map.push([n, i]); } } else { s += c; map.push([n, i]); } } }
  const lines = r => { const rs = [...r.getClientRects()].filter(x => x.width > 1 && x.height > 4).map(x => [x.left + scrollX, x.top + scrollY, x.right + scrollX, x.bottom + scrollY]); const g = [];
    rs.sort((a, b) => a[1] - b[1] || a[0] - b[0]); rs.forEach(x => { const l = g.find(y => Math.abs(y[1] - x[1]) < 6 && Math.abs(y[3] - x[3]) < 8); if (l) { l[0] = Math.min(l[0], x[0]); l[2] = Math.max(l[2], x[2]); l[1] = Math.min(l[1], x[1]); l[3] = Math.max(l[3], x[3]); } else g.push(x.slice()); }); return g; };
  const res = {};
  for (const [k, str] of Object.entries(passages)) { const q = str.replace(/\s+/g, ' '); const i = s.indexOf(q); if (i < 0) { res[k] = null; continue; }
    const r = document.createRange(); r.setStart(map[i][0], map[i][1]); r.setEnd(map[i + q.length - 1][0], map[i + q.length - 1][1] + 1); res[k] = lines(r); }
  const rb = root.getBoundingClientRect();
  return { text: s, rects: res, root: [rb.left + scrollX, rb.top + scrollY, rb.right + scrollX, rb.bottom + scrollY], tarjas: nt, pageH: document.documentElement.scrollHeight, pageW: document.documentElement.scrollWidth };
}, cfg);
await p.screenshot({ path: 'page.png', fullPage: true }); fs.writeFileSync('page_text.txt', out.text); delete out.text; out.dsf = DSF; fs.writeFileSync('rects.json', JSON.stringify(out)); console.log(JSON.stringify({ tarjas: out.tarjas, pageH: out.pageH, pageW: out.pageW, missing: Object.entries(out.rects).filter(([, v]) => !v).map(([k]) => k) })); await b.close();
