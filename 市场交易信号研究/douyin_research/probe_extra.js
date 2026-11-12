// 逐个打开候选视频页，抓取 aweme/detail 响应以核验作者与播放地址。
const fs = require('fs');
const ids = (process.env.IDS || '').split(',').filter(Boolean);
const port = process.env.CDP_PORT || '9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json());
  const page = list.find(t => t.type === 'page' && t.url.includes('douyin.com')) || list.find(t => t.type === 'page');
  if (!page) { console.log('NO_PAGE'); return; }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0, current = '';
  const pending = new Map();
  const reqMap = new Map();
  const bodies = [];
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++id; pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });

  ws.onmessage = async (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result);
      return;
    }
    if (m.method === 'Network.responseReceived' && /aweme\/detail/.test(m.params.response.url)) {
      reqMap.set(m.params.requestId, m.params.response.url);
    }
    if (m.method === 'Network.loadingFinished' && reqMap.has(m.params.requestId)) {
      const rid = m.params.requestId; const u = reqMap.get(rid); reqMap.delete(rid);
      try {
        const b = await send('Network.getResponseBody', { requestId: rid });
        const body = b.base64Encoded ? Buffer.from(b.body, 'base64').toString('utf8') : b.body;
        bodies.push({ probe: current, url: u, body });
        console.log('GOT', current, body.length);
      } catch (e) { console.log('BODY_ERR', current, e.message); }
    }
  };

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    for (const vid of ids) {
      current = vid;
      await send('Page.navigate', { url: `https://www.douyin.com/video/${vid}` });
      await sleep(4200);
    }
    fs.writeFileSync(process.env.OUT || 'extra_detail_cap.json', JSON.stringify(bodies, null, 2));
    console.log('DONE', bodies.length);
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
