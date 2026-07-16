#!/usr/bin/env node
const { call } = require('/Users/yangguang/.codex/skills/ifind-finance-data/call-node.js');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function chunks(items, size) {
  const out = [];
  for (let i = 0; i < items.length; i += size) {
    out.push(items.slice(i, i + size));
  }
  return out;
}

async function main() {
  const raw = process.argv[2];
  if (!raw) {
    throw new Error('usage: node ifind_nav_query.js \'{"target_date":"YYYYMMDD","codes":["000216.OF"]}\'');
  }
  const input = JSON.parse(raw);
  const codes = input.codes || [];
  const targetDate = input.target_date || '';
  const batchSize = input.batch_size || 6;
  const delayMs = input.delay_ms || 1300;

  const batches = [];
  for (const group of chunks(codes, batchSize)) {
    const query = [
      `查询以下基金的最新复权单位净值，只返回基金代码、证券简称、复权单位净值三列表格：`,
      group.join('、'),
      targetDate ? `目标日报日期 ${targetDate}，如果当日净值未发布请返回当前最新可得净值。` : '',
    ].join('');
    const result = await call('fund', 'get_fund_market_performance', { query });
    batches.push({ query, result });
    if (delayMs > 0) {
      await sleep(delayMs);
    }
  }
  console.log(JSON.stringify({ ok: true, target_date: targetDate, batches }, null, 2));
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
