// 增量发现：只核验 aweme_id 大于已知最新值的候选（抖音 ID 单调递增）
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research';
const videos = JSON.parse(fs.readFileSync(path.join(BASE, 'videos.json'), 'utf8'));
const known = new Set(videos.map(v => String(v.id)));
const MIN_ID = process.env.MIN_ID || known.size ? [...known].sort().pop() : '0';
const TARGET_SEC = 'MS4wLjABAAAAHwe0CgM38CCjWMNxHSvkydtX5zlrG38YoPTtrvkX7bRzlN2xJje0cqecaY-1jSay';
const ENTRIES = videos.slice(-3).map(v => String(v.id));

const isNewer = id => id.length === 19 && id > MIN_ID;

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
          probe: current, id: String(d.aweme_id), sec_uid: (d.author || {}).sec_uid,
          nickname: (d.author || {}).nickname, create_time: d.create_time,
          desc: (d.desc || '').slice(0, 200), duration_ms: v.duration || d.duration,
          width: v.width, height: v.height, play_addr: v.play_addr,
          download_addr: v.download_addr, play_addr_h264: v.play_addr_h264, bit_rate: v.bit_rate,
        });
      } catch (err) { }
    }
  };

  const getLinks = `(()=>Array.from(new Set(Array.from(document.querySelectorAll('a[href*="/video/"]')).map(a=>(a.href.match(/video\\/(\\d+)/)||[])[1]).filter(Boolean))))()`;

  ws.onopen = async () => {
    await send('Network.enable');
    await send('Page.enable');
    await send('Runtime.enable');
    console.log('MIN_ID', MIN_ID, '| 入口', ENTRIES.join(','));

    const pool = new Set();
    for (const vid of ENTRIES) {
      await send('Page.navigate', { url: `https://www.douyin.com/video/${vid}` });
      await sleep(5000);
      const r = await send('Runtime.evaluate', { expression: getLinks, returnByValue: true });
      (r.result?.value || []).forEach(x => pool.add(x));
      console.log('ENTRY', vid, 'pool', pool.size, 'newer', [...pool].filter(isNewer).length);
    }

    let todo = [...pool].filter(x => !known.has(x) && isNewer(x));
    console.log('待核验（>MIN_ID）', todo.length, todo.join(','));

    const verified = new Set();
    for (let round = 0; round < 3 && todo.length; round++) {
      for (const vid of todo.splice(0)) {
        if (verified.has(vid)) continue;
        verified.add(vid);
        current = vid;
        await send('Page.navigate', { url: `https://www.douyin.com/video/${vid}` });
        await sleep(3600);
      }
      const r = await send('Runtime.evaluate', { expression: getLinks, returnByValue: true });
      const more = (r.result?.value || []).filter(x => !known.has(x) && !verified.has(x) && isNewer(x));
      if (more.length) { todo.push(...more); console.log('round', round, '新增候选', more.length, more.join(',')); }
    }

    const seen = new Map();
    for (const d of details) if (!seen.has(d.id)) seen.set(d.id, d);
    const arr = [...seen.values()];
    const mine = arr.filter(d => d.sec_uid === TARGET_SEC && !known.has(d.id));
    fs.writeFileSync(path.join(BASE, 'discovered_latest.json'), JSON.stringify(arr, null, 0));
    console.log('DETAIL_TOTAL', arr.length, 'MINE_NEW', mine.length);
    for (const d of mine.sort((a, b) => a.create_time - b.create_time)) {
      const dt = new Date((d.create_time + 8 * 3600) * 1000).toISOString().slice(0, 10);
      console.log(`  MINE ${d.id} ${dt} ${Math.round(d.duration_ms / 60000 * 10) / 10}min ${d.width}x${d.height} play=${((d.play_addr || {}).data_size / 1e6 || 0).toFixed(0)}MB | ${d.desc.slice(0, 44)}`);
    }
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
