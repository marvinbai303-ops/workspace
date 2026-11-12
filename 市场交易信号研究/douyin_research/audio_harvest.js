const fs = require('fs');
const port = process.env.CDP_PORT || '9222';
const videos = JSON.parse(fs.readFileSync(process.env.VIDEOS || 'videos.json', 'utf8'));
const ids = videos.map(v => v.id);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const WAIT = parseInt(process.env.WAIT || '4200', 10);
const START = parseInt(process.env.START || '0', 10);
const END = parseInt(process.env.END || String(ids.length), 10);

async function main() {
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json());
  const page = list.find(t => t.type === 'page' && t.url.includes('douyin.com')) || list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0, current = '';
  const pending = new Map();
  const found = {};
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++id; pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });

  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result);
      return;
    }
    if (m.method === 'Network.requestWillBeSent' && current) {
      const u = m.params.request.url;
      if (/media-audio/.test(u) && !found[current]) {
        found[current] = u;
        console.log('  AUDIO_OK', current, u.length);
      }
    }
  };

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    for (let i = START; i < Math.min(END, ids.length); i++) {
      current = ids[i];
      await send('Page.navigate', { url: `https://www.douyin.com/video/${current}` });
      await sleep(WAIT);
      if (!found[current]) console.log('  MISS', i, current);
      if (i % 10 === 9) fs.writeFileSync(process.env.OUT || 'audio_urls.json', JSON.stringify(found, null, 2));
    }
    fs.writeFileSync(process.env.OUT || 'audio_urls.json', JSON.stringify(found, null, 2));
    console.log('DONE', Object.keys(found).length, '/', ids.length);
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
