const fs = require('fs');
const port = process.env.CDP_PORT || '9222';
const out = process.env.OUT || 'harvest.json';
const MIXES = (process.env.MIXES || '7698297594887604287,7686278450684004352,7686145209003935770,7685362419392071726').split(',');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json());
  const page = list.find(t => t.type === 'page' && t.url.includes('douyin.com')) || list.find(t => t.type === 'page');
  if (!page) { console.log('NO_PAGE'); return; }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const reqMap = new Map();
  const bodies = [];
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
    if (m.method === 'Network.responseReceived' && /mix\/aweme|aweme\/post/.test(m.params.response.url)) {
      reqMap.set(m.params.requestId, { url: m.params.response.url, status: m.params.response.status });
    }
    if (m.method === 'Network.loadingFinished' && reqMap.has(m.params.requestId)) {
      const rid = m.params.requestId; const meta = reqMap.get(rid);
      try {
        const b = await send('Network.getResponseBody', { requestId: rid });
        const body = b.base64Encoded ? Buffer.from(b.body, 'base64').toString('utf8') : b.body;
        bodies.push({ mix: currentMix, url: meta.url, status: meta.status, body });
        console.log('  CAP', currentMix, body.length, (meta.url.match(/cursor=(\d+)/) || [])[1] || 'init');
      } catch (e) { console.log('  BODY_ERR', e.message); }
    }
  };

  let currentMix = '';
  const evalJs = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result && r.result.value;
  };

  const clickMore = `(()=>{
    var es=Array.from(document.querySelectorAll('div,span,button,a,p')).filter(function(e){
      return e.children.length===0 && /点击加载更多|加载更多|展开更多/.test((e.textContent||'').trim());
    });
    if(es.length){es[0].click();return 'clicked';}
    return 'none';
  })()`;

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    await send('Runtime.enable');
    for (const mix of MIXES) {
      currentMix = mix;
      const url = `https://www.douyin.com/collection/${mix}/1`;
      console.log('MIX', mix);
      await send('Page.navigate', { url });
      await sleep(7000);
      for (let i = 0; i < 12; i++) {
        const r = await evalJs(clickMore);
        console.log('  more click', i, r);
        if (r !== 'clicked') break;
        await sleep(2600);
      }
      await sleep(1200);
      const cnt = await evalJs(`document.querySelectorAll('a[href*="/video/"]').length`);
      console.log('  video links on page', cnt);
    }
    fs.writeFileSync(out, JSON.stringify(bodies, null, 2));
    console.log('DONE responses', bodies.length, 'saved', out);
    ws.close();
  };
  ws.onerror = (e) => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
