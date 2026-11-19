// 诊断未登录态下用户主页与合集页的可达性及 DOM 中的作品链接
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const list = await fetch('http://127.0.0.1:9222/json/list').then(r => r.json());
  const page = list.find(t => t.type === 'page') || list[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pend = new Map();
  const send = (m, q = {}) => new Promise((res, rej) => {
    const i = ++id; pend.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method: m, params: q }));
  });
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { const q = pend.get(m.id); pend.delete(m.id); m.error ? q.rej(m.error) : q.res(m.result); }
  };

  const targets = [
    ['USER', 'https://www.douyin.com/user/MS4wLjABAAAAHwe0CgM38CCjWMNxHSvkydtX5zlrG38YoPTtrvkX7bRzlN2xJje0cqecaY-1jSay'],
    ['MIX_金融宝藏', 'https://www.douyin.com/collection/7686278450684004352'],
    ['MIX_研判', 'https://www.douyin.com/collection/7686145209003935770'],
  ];

  ws.onopen = async () => {
    await send('Page.enable');
    await send('Runtime.enable');
    for (const [tag, url] of targets) {
      await send('Page.navigate', { url });
      await sleep(9000);
      const expr = `(()=>{
        const ids=Array.from(new Set(Array.from(document.querySelectorAll('a[href*="/video/"]')).map(a=>(a.href.match(/video\\/(\\d+)/)||[])[1]).filter(Boolean)));
        const h=document.documentElement.innerHTML;
        return {url:location.href, title:document.title, links:ids.length, ids:ids.slice(0,60),
          hasLogin:/登录|扫码登录/.test(document.body.innerText||''),
          htmlLen:h.length, hasAweme:h.includes('aweme_id'), hasPlayAddr:h.includes('play_addr')};
      })()`;
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
      const v = r.result?.value || {};
      console.log(tag, JSON.stringify({ url: (v.url || '').slice(0, 80), title: v.title, links: v.links, hasAweme: v.hasAweme, hasPlayAddr: v.hasPlayAddr, htmlLen: v.htmlLen }));
      if (v.ids && v.ids.length) console.log('   IDs:', v.ids.slice(0, 20).join(','));
    }
    ws.close();
  };
  ws.onerror = e => console.log('WS_ERR', e.message || e);
}
main().catch(e => console.log('FATAL', e.message));
