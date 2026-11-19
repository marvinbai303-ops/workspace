const fs = require('fs');
const port = process.env.CDP_PORT || '9222';
const out = process.env.OUT || 'captured.json';
const hold = parseInt(process.env.HOLD || '14000', 10);
const reload = process.env.RELOAD !== '0';

async function main() {
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json());
  const page = list.find(t => t.type === 'page' && t.url.includes('douyin.com')) || list.find(t => t.type === 'page');
  if (!page) { console.log('NO_PAGE'); return; }
  console.log('PAGE', page.url);
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const reqMap = new Map();
  const bodies = [];
  const seen = [];
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++id;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });

  ws.onmessage = async (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result);
      return;
    }
    if (m.method === 'Network.responseReceived') {
      const u = m.params.response.url;
      if (/aweme\/v1\/web/.test(u)) {
        seen.push(m.params.response.status + ' ' + u.split('?')[0]);
        if (/mix\/aweme|aweme\/post|aweme\/detail|series\/list|mix\/list/.test(u)) {
          reqMap.set(m.params.requestId, { url: u, status: m.params.response.status });
        }
      }
    }
    if (m.method === 'Network.loadingFinished' && reqMap.has(m.params.requestId)) {
      const rid = m.params.requestId;
      const meta = reqMap.get(rid);
      try {
        const b = await send('Network.getResponseBody', { requestId: rid });
        const body = b.base64Encoded ? Buffer.from(b.body, 'base64').toString('utf8') : b.body;
        bodies.push({ url: meta.url, status: meta.status, body });
        console.log('GOT', meta.status, body.length, meta.url.split('?')[0]);
      } catch (e) { console.log('BODY_ERR', e.message); }
    }
  };

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    if (reload) await send('Page.reload', { ignoreCache: true });
    setTimeout(() => {
      fs.writeFileSync(out, JSON.stringify(bodies, null, 2));
      fs.writeFileSync(out.replace('.json', '_seen.txt'), seen.join('\n'));
      console.log('TOTAL', bodies.length, 'SEEN', seen.length, 'saved', out);
      ws.close();
    }, hold);
  };
  ws.onerror = (e) => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
