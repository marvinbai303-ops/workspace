// 从视频页旁侧列表发现候选 ID，逐个核验作者归属并裁剪关键字段
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research';
const known = new Set(JSON.parse(fs.readFileSync(path.join(BASE, 'videos.json'), 'utf8')).map(v => String(v.id)));
const TARGET_SEC = 'MS4wLjABAAAAHwe0CgM38CCjWMNxHSvkydtX5zlrG38YoPTtrvkX7bRzlN2xJje0cqecaY-1jSay';
const ENTRIES = ['7686279141561598179', '7686146252223881152', '7706497063014957027', '7685362553472801187'];

async function main() {
  const list = await fetch('http://127.0.0.1:9222/json/list').then(r => r.json());
  const page = list.find(t => t.type === 'page') || list[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0, current = '';
  const pend = new Map(), reqMap = new Map(), details = [];
  const send = (m, q = {}) => new Promise((res, rej) => {
    const i = ++id; pend.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method: m, params: q }));
  });

  ws.onmessage = async e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { const q = pend.get(m.id); pend.delete(m.id); m.error ? q.rej(m.error) : q.res(m.result); return; }
    if (m.method === 'Network.responseReceived' && /aweme\/detail/.test(m.params.response.url)) {
      reqMap.set(m.params.requestId, m.params.response.url);
    }
    if (m.method === 'Network.loadingFinished' && reqMap.has(m.params.requestId)) {
      const rid = m.params.requestId; reqMap.delete(rid);
      try {
        const b = await send('Network.getResponseBody', { requestId: rid });
        const raw = b.base64Encoded ? Buffer.from(b.body, 'base64').toString('utf8') : b.body;
        const d = JSON.parse(raw).aweme_detail;
        if (!d) return;
        const v = d.video || {};
        details.push({
          probe: current, id: String(d.aweme_id),
          sec_uid: (d.author || {}).sec_uid,
          nickname: (d.author || {}).nickname,
          create_time: d.create_time,
          desc: (d.desc || '').slice(0, 200),
          duration_ms: v.duration || d.duration,
          width: v.width, height: v.height,
          play_addr: v.play_addr, download_addr: v.download_addr,
          play_addr_h264: v.play_addr_h264, bit_rate: v.bit_rate,
          mix_info: d.mix_info || null,
        });
      } catch (err) { }
    }
  };

  const getLinks = `(()=>Array.from(new Set(Array.from(document.querySelectorAll('a[href*="/video/"]')).map(a=>(a.href.match(/video\\/(\\d+)/)||[])[1]).filter(Boolean))))()`;

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    await send('Runtime.enable');

    const pool = new Set();
    for (const vid of ENTRIES) {
      await send('Page.navigate', { url: `https://www.douyin.com/video/${vid}` });
      await sleep(5000);
      const r = await send('Runtime.evaluate', { expression: getLinks, returnByValue: true });
      (r.result?.value || []).forEach(x => pool.add(x));
      console.log('ENTRY', vid, 'pool', pool.size);
    }

    let todo = [...pool].filter(x => !known.has(x));
    console.log('候选待核验', todo.length);

    const verified = new Set();
    for (let round = 0; round < 3 && todo.length; round++) {
      const batch = todo.slice(0, 24);
      todo = todo.slice(24);
      for (const vid of batch) {
        if (verified.has(vid)) continue;
        verified.add(vid);
        current = vid;
        await send('Page.navigate', { url: `https://www.douyin.com/video/${vid}` });
        await sleep(3600);
      }
      const r = await send('Runtime.evaluate', { expression: getLinks, returnByValue: true });
      const more = (r.result?.value || []).filter(x => !known.has(x) && !verified.has(x));
      if (more.length) { todo.push(...more); console.log('round', round, '新增候选', more.length); }
    }

    const seen = new Map();
    for (const d of details) if (!seen.has(d.id) || JSON.stringify(d).length > JSON.stringify(seen.get(d.id)).length) seen.set(d.id, d);
    const arr = [...seen.values()];
    const mine = arr.filter(d => d.sec_uid === TARGET_SEC);
    fs.writeFileSync(path.join(BASE, 'discovered.json'), JSON.stringify(arr.filter(d => d.sec_uid === TARGET_SEC || true), null, 0));
    console.log('DETAIL_TOTAL', arr.length, 'MINE', mine.length);
    for (const d of mine.sort((a, b) => a.create_time - b.create_time)) {
      const dt = new Date((d.create_time + 8 * 3600) * 1000).toISOString().slice(0, 10);
      console.log(`  MINE ${d.id} ${dt} ${Math.round(d.duration_ms / 60000 * 10) / 10}min ${d.width}x${d.height} play=${(d.play_addr?.data_size / 1e6 || 0).toFixed(0)}MB | ${d.desc.slice(0, 40)}`);
    }
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
