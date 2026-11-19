export const MODEL_VERSION = "2026-11-18-source-v2";
export const FACTOR_ROWS = [5,6,7,10,11,12,15,16,17,18,19,22,23,28,29,32,33,34,35,36,37];
const MONTHLY = new Set([15,16,17,18,22]);

export function shiftDate(date, horizon) {
  const d = new Date(`${date}T00:00:00Z`);
  if (horizon === "month") {
    const day = d.getUTCDate();
    d.setUTCDate(1);
    d.setUTCMonth(d.getUTCMonth() - 1);
    const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(day, last));
  } else d.setUTCDate(d.getUTCDate() - (horizon === "week" ? 7 : 1));
  return d.toISOString().slice(0,10);
}

export function observationChanges(series, frequency = "日") {
  const last = series.at(-1);
  return Object.fromEntries(["day","week","month"].map(horizon => {
    const targetDate = shiftDate(last.date, horizon);
    if (horizon === "day" && frequency !== "日" || horizon === "week" && frequency === "月") {
      return [horizon, {targetDate, status: `${frequency}频不提供该间隔变化`}];
    }
    const prior = [...series].reverse().find(x => x.date <= targetDate);
    return [horizon, {targetDate, date: prior?.date, value: prior?.value ?? null,
      status: prior ? "当前修订版观测序列" : "历史观测不足"}];
  }));
}

export function snapshotChanges(metrics, snapshots, runDate) {
  const byDate = new Map();
  for (const snap of snapshots) if (snap.runDate && snap.runDate < runDate) byDate.set(snap.runDate, snap);
  const history = [...byDate.values()].sort((a,b) => a.runDate.localeCompare(b.runDate));
  const output = {};
  for (const row of FACTOR_ROWS) {
    const current = metrics[row];
    output[row] = {};
    for (const horizon of ["day","week","month"]) {
      const targetDate = shiftDate(runDate,horizon);
      const snap = history.findLast(s => s.runDate <= targetDate);
      const prior = snap?.metrics?.[row];
      let status = "可比";
      const age = snap ? (Date.parse(targetDate)-Date.parse(snap.runDate))/86400000 : Infinity;
      if (!snap || age > 4) status = "无邻近历史运行快照";
      else if (!prior || !Number.isFinite(prior.current)) status = "历史输入缺失";
      else if (prior.stale || current?.stale) status = "来源抓取失败，缓存不可作变化依据";
      else if (prior.definitionId !== current?.definitionId) status = "取数口径已修正，历史不可比";
      if (status === "可比" && MONTHLY.has(row) && prior.date === current.date && prior.current === current.current) status = "可比，本期尚无新发布";
      output[row][horizon] = {targetDate,snapshotDate:snap?.runDate,date:prior?.date,
        value:status.startsWith("可比") ? prior.current : null,status};
    }
  }
  const scoreComparisons = {};
  for (const horizon of ["day","week","month"]) {
    const targetDate = shiftDate(runDate,horizon);
    const snap = history.findLast(s => s.runDate <= targetDate);
    const valid = snap?.modelVersion === MODEL_VERSION && snap.scores &&
      (Date.parse(targetDate)-Date.parse(snap.runDate))/86400000 <= 4 &&
      FACTOR_ROWS.every(row => !snap.metrics?.[row]?.stale && !metrics[row]?.stale);
    scoreComparisons[horizon] = {targetDate,snapshotDate:snap?.runDate,
      values: valid ? snap.scores : null,
      status:valid ? "同口径快照" : "同口径评分历史不足或来源未更新"};
  }
  return {indicators:output,scores:scoreComparisons};
}
