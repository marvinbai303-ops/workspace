// 抓取抖音用户主页 aweme/post 作品列表响应，自动滚动翻页。
const fs = require('fs');
const port = process.env.CDP_PORT || '9222';
const out = process.env.OUT || 'user_post_cap.json';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const HOME = 'https://www.douyin.com/user/MS4wLjABAAAAHwe0CgM38CCjWMNxHSvkydtX5zlrG38YoPTtrvkX7bRzlN2xJje0cqecaY-1jSay?from_tab_name=main';

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
    if (m.method === 'Network.responseReceived') {
      const u = m.params.response.url;
      if (/aweme\/v1\/web/.test(u)) {
        seen.push(m.params.response.status + ' ' + u.split('?')[0]);
        if (/aweme\/post|mix\/list|aweme\/detail/.test(u)) {
          reqMap.set(m.params.requestId, { url: u, status: m.params.response.status });
        }
      }
    }
    if (m.method === 'Network.loadingFinished' && reqMap.has(m.params.requestId)) {
      const rid = m.params.requestId;
      const meta = reqMap.get(rid); reqMap.delete(rid);
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
    await send('Runtime.enable');
    await send('Page.navigate', { url: HOME });
    await sleep(8000);
    for (let i = 0; i < 15; i++) {
      const before = bodies.length;
      await send('Runtime.evaluate', {
        expression: `window.scrollTo(0, document.body.scrollHeight); document.querySelectorAll('a[href*="/video/"]').length`,
        returnByValue: true,
      });
      await sleep(2600);
      const last = bodies.filter(b => /aweme\/post/.test(b.url)).pop();
      let hasMore = null;
      try { hasMore = last ? JSON.parse(last.body).has_more : null; } catch (e) {}
      console.log('scroll', i, 'bodies', bodies.length, '(+' + (bodies.length - before) + ')', 'has_more', hasMore);
      if (hasMore === 0 && i >= 2) break;
    }
    fs.writeFileSync(out, JSON.stringify(bodies, null, 2));
    fs.writeFileSync(out.replace('.json', '_seen.txt'), seen.join('\n'));
    console.log('TOTAL', bodies.length, 'SEEN', seen.length, 'saved', out);
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
