import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import os from "node:os";
import {createHash} from "node:crypto";
import { MODEL_VERSION, snapshotChanges, observationChanges } from "./rate_model_changes.mjs";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const MODEL_DIR = path.join(ROOT, "君君美债利率模型_自动刷新");
const DATA_DIR = path.join(MODEL_DIR, "data");
const RAW_DIR = path.join(DATA_DIR, "raw");
const PROCESSED_DIR = path.join(DATA_DIR, "processed");
const OUTPUT_DIR = path.join(MODEL_DIR, "output");
const ARCHIVE_DIR = path.join(OUTPUT_DIR, "archive");
const LOG_DIR = path.join(MODEL_DIR, "logs");
const LOCK_FILE = path.join(MODEL_DIR, "refresh.lock");
const LATEST_FILE = path.join(PROCESSED_DIR, "latest.json");
const HISTORY_FILE = path.join(PROCESSED_DIR, "history.jsonl");
const PYTHON = process.env.RATE_MODEL_PYTHON ?? "/Users/yangguang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const SOFFICE = process.env.RATE_MODEL_SOFFICE ?? "/Users/yangguang/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice";
const REPLAY_DIR = process.env.RATE_MODEL_REPLAY_DIR;

const runDate = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai" }).format(new Date());
const runYear = Number(runDate.slice(0, 4));
const startDate = `${runYear - 6}-01-01`;
const rawRunDir = path.join(RAW_DIR, runDate);
const logLines = [`开始刷新：${new Date().toISOString()}`, `运行日期：${runDate}`];
const warnings = [];
let lockAcquired = false;
let priorSnapshots = [];
const sourceStatus = {};

async function ensureDirs() {
  for (const dir of [MODEL_DIR, rawRunDir, PROCESSED_DIR, OUTPUT_DIR, ARCHIVE_DIR, LOG_DIR]) {
    await fs.mkdir(dir, { recursive: true });
  }
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await fs.readFile(file, "utf8"));
  } catch {
    return fallback;
  }
}

async function readPriorMetrics() {
  const latestData = await readJson(LATEST_FILE, { metrics: {} });
  const snapshots = [];
  try {
    const history = await fs.readFile(HISTORY_FILE, "utf8");
    for (const line of history.split(/\r?\n/).filter(Boolean)) {
      try {
        const snapshot = JSON.parse(line);
        if (snapshot?.metrics) snapshots.push(snapshot);
      } catch {
        // Ignore malformed history rows and continue with the remaining snapshots.
      }
    }
  } catch {
    // The latest snapshot below remains usable when no history file exists.
  }
  if (latestData?.metrics) snapshots.push(latestData);
  priorSnapshots = snapshots;

  const metrics = {};
  for (const snapshot of snapshots) {
    for (const [key, metric] of Object.entries(snapshot.metrics)) {
      if (!metric || metric.stale || !metric.date || !Number.isFinite(metric.current)) continue;
      // Old page extraction accepted a non-series value of 1%. Never carry it forward.
      if (key === "16" && metric.definitionId !== "wgt-overall-3ma-v2") continue;
      if (!metrics[key] || metric.date >= metrics[key].date) metrics[key] = metric;
    }
  }
  return { ...latestData, metrics };
}

function command(file, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(file, args, { timeout: 150000, ...options, stdio: ["ignore", "pipe", "pipe"] });
    const stdout = [];
    const stderr = [];
    child.stdout.on("data", (chunk) => stdout.push(chunk));
    child.stderr.on("data", (chunk) => stderr.push(chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      const result = {
        code,
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      };
      if (code === 0) resolve(result);
      else reject(Object.assign(new Error(`${file} exited with code ${code}: ${result.stderr.trim()}`), result));
    });
  });
}

function csvLine(line) {
  const cells = [];
  let value = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        value += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      cells.push(value);
      value = "";
    } else {
      value += ch;
    }
  }
  cells.push(value);
  return cells;
}

function parseFredCsv(text, seriesId) {
  const lines = text.replace(/^\uFEFF/, "").replace(/\r/g, "").trim().split("\n");
  if (!lines.length || !(lines[0].startsWith("DATE") || lines[0].startsWith("observation_date"))) throw new Error(`FRED ${seriesId} returned an unexpected response`);
  const header = csvLine(lines[0]);
  const dateIndex = header.findIndex((x) => x === "DATE" || x === "observation_date");
  const valueIndex = header.findIndex((x) => x === seriesId);
  if (dateIndex < 0 || valueIndex < 0) throw new Error(`FRED ${seriesId} columns not found`);
  return lines.slice(1).map((line) => csvLine(line)).map((cells) => ({
    date: cells[dateIndex],
    value: cells[valueIndex]?.trim() && cells[valueIndex] !== "." ? Number(cells[valueIndex]) : NaN,
  })).filter((row) => /^\d{4}-\d{2}-\d{2}$/.test(row.date) && Number.isFinite(row.value));
}

async function fetchFred(seriesId) {
  const url = `https://fred.stlouisfed.org/graph/fredgraph.csv?id=${encodeURIComponent(seriesId)}&cosd=${startDate}`;
  const file = path.join(rawRunDir, `fred_${seriesId}.csv`);
  let bytes;
  if (REPLAY_DIR) bytes=await replayBytes(path.basename(file));
  else for (let attempt=1;attempt<=2;attempt++) {
    try {
      const response=await fetch(url,{headers:{"User-Agent":"junjun-rate-model/1.0"},signal:AbortSignal.timeout(20000)});
      if (!response.ok) throw new Error(`HTTP ${response.status} for ${seriesId}`);
      bytes=new Uint8Array(await response.arrayBuffer());
      break;
    } catch(error) {
      logLines.push(`FRED ${seriesId} 第${attempt}次失败: ${error.message} ${error.cause?.code ?? ""}`);
      if (attempt===2) throw error;
    }
  }
  await fs.writeFile(file, bytes);
  const text = new TextDecoder().decode(bytes);
  return { seriesId, url, file, observations: parseFredCsv(text, seriesId) };
}

async function replayBytes(name) {
  const manifest=await readJson(path.join(REPLAY_DIR,"fetch_manifest.json"),{});
  if (manifest.runDate!==runDate || !manifest.files?.[name]) throw new Error("仅允许重算本日已校验快照");
  const bytes=await fs.readFile(path.join(REPLAY_DIR,name));
  if (createHash("sha256").update(bytes).digest("hex")!==manifest.files[name].sha256) throw new Error(`快照校验失败: ${name}`);
  logLines.push(`复用本日已校验官方文件: ${name}`);
  return bytes;
}

function latest(series) {
  return series.at(-1);
}

function values(series) {
  return series.filter((x) => Number.isFinite(x.value));
}

function stats(series) {
  const cutoff = `${runYear - 5}-01-01`;
  const sample = values(series).filter((x) => x.date >= cutoff).map((x) => x.value);
  if (!sample.length) return { mean: null, std: null };
  const mean = sample.reduce((a, b) => a + b, 0) / sample.length;
  const variance = sample.length > 1 ? sample.reduce((a, b) => a + (b - mean) ** 2, 0) / (sample.length - 1) : 0;
  return { mean, std: Math.sqrt(variance) || 0.000001 };
}

function lagDiff(series, lag) {
  const clean = values(series);
  return clean.slice(lag).map((row, index) => ({ date: row.date, value: row.value - clean[index].value }));
}

function pctChange(series, lag) {
  const clean = values(series);
  return clean.slice(lag).map((row, index) => ({
    date: row.date,
    value: clean[index].value === 0 ? NaN : ((row.value / clean[index].value) - 1) * 100,
  })).filter((row) => Number.isFinite(row.value));
}

function yoyChange(series, lag = 12) {
  return pctChange(series, lag);
}

function rollingMean(series, window) {
  const clean = values(series);
  return clean.slice(window - 1).map((row, index) => ({
    date: row.date,
    value: clean.slice(index, index + window).reduce((sum, item) => sum + item.value, 0) / window,
  }));
}

function alignSubtract(left, right) {
  const rightByDate = new Map(right.map((x) => [x.date, x.value]));
  return left.filter((x) => rightByDate.has(x.date)).map((x) => ({ date: x.date, value: x.value - rightByDate.get(x.date) }));
}

function modelMetric(series, meta = {}) {
  const clean = values(series).filter(x => x.date <= runDate).sort((a,b) => a.date.localeCompare(b.date));
  const last = latest(clean);
  const distribution = stats(clean);
  if (!last || distribution.mean === null || distribution.std === null) return null;
  return {
    current: last.value,
    mean: distribution.mean,
    std: distribution.std,
    date: last.date,
    availability: meta.availability ?? 5,
    accuracy: meta.accuracy ?? 4,
    note: meta.note,
    source: meta.source,
    frequency: meta.frequency ?? "日",
    observationComparisons: observationChanges(clean, meta.frequency ?? "日"),
  };
}

async function downloadOfficial(source, url, file) {
  const started = Date.now();
  try {
    if (REPLAY_DIR) {
      const bytes=await replayBytes(path.basename(file));
      await fs.writeFile(file,bytes);
      sourceStatus[source]={ok:true,url,bytes:bytes.length,transport:"本日成功下载后的校验重算"};
      return {zip:bytes[0]===0x50 && bytes[1]===0x4b};
    }
    const result = await command("/usr/bin/curl", ["--fail", "--location", "--silent", "--show-error",
      "--connect-timeout", "15", "--max-time", "120", "--retry", "1", "--retry-delay", "1",
      "--output", `${file}.part`, "--write-out", "%{http_code} %{size_download} %{time_total} %{url_effective}", url],{timeout:270000});
    const bytes = await fs.readFile(`${file}.part`);
    const zip = bytes[0] === 0x50 && bytes[1] === 0x4b;
    const ole = bytes.subarray(0,4).equals(Buffer.from([0xd0,0xcf,0x11,0xe0]));
    if (bytes.length < 1024 || !(zip || ole)) throw new Error("下载内容不是 Excel 文件");
    await fs.rename(`${file}.part`, file);
    sourceStatus[source] = {ok:true,url,bytes:bytes.length,elapsedMs:Date.now()-started,response:result.stdout.trim()};
    logLines.push(`${source} 下载成功: ${result.stdout.trim()}`);
    return {zip};
  } catch (error) {
    sourceStatus[source] = {ok:false,url,elapsedMs:Date.now()-started,error:error.message};
    throw error;
  } finally {
    await fs.rm(`${file}.part`,{force:true});
  }
}

function mergeWithPrevious(current, row, previous, sourceLabel) {
  if (current) return current;
  const prior = previous?.metrics?.[String(row)];
  if (prior) {
    warnings.push(`指标 ${row} 本次未更新，沿用 ${prior.date} 的有效值`);
    return { ...prior, stale: true, note: `${prior.note ?? ""}；本次来源未更新，沿用上一有效值`, source: sourceLabel ?? prior.source };
  }
  warnings.push(`指标 ${row} 没有可用的新值，也没有历史缓存`);
  return null;
}

async function tryAcmeTermPremium(previous) {
  const url = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls";
  const xlsFile = path.join(rawRunDir, "ACMTermPremium.xls");
  const {zip} = await downloadOfficial("NY Fed ACM",url,xlsFile);
  const convertedDir = path.join(rawRunDir, "acm_converted");
  await fs.mkdir(convertedDir, { recursive: true });
  const xlsxFile = path.join(convertedDir, "ACMTermPremium.xlsx");
  if (zip) await fs.copyFile(xlsFile,xlsxFile);
  else {
    const profile = await fs.mkdtemp(path.join(os.tmpdir(),"rate-acm-lo-"));
    try {
      await fs.rm(xlsxFile,{force:true});
      await command(SOFFICE, [`-env:UserInstallation=${new URL(`file://${profile}`).href}`,"--headless", "--convert-to", "xlsx", "--outdir", convertedDir, xlsFile]);
    } finally { await fs.rm(profile,{recursive:true,force:true}); }
  }
  const parsed = await command(PYTHON, [path.join(ROOT, "parse_acm_xlsx.py"), xlsxFile]);
  const observations = JSON.parse(parsed.stdout);
  const tp = observations.map((x) => ({ date: x.date, value: Number(x.ACMTP10) })).filter((x) => Number.isFinite(x.value));
  if (!tp.length) throw new Error("NY Fed ACMTP10 column is empty");
  return {
    level: modelMetric(tp, { availability: 5, accuracy: 3, note: "模型估计值；存在模型风险", source: "NY Fed ACMTP10" }),
    change: modelMetric(lagDiff(tp, 20), { availability: 5, accuracy: 3, note: "判断长端上行是否来自期限溢价边际扩张", source: "NY Fed ACMTP10" }),
    latestDate: latest(tp).date,
  };
}

async function tryWageGrowthTracker(previous) {
  const url = "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/wage-growth-tracker/wage-growth-data.xlsx";
  const file = path.join(rawRunDir, "atlanta_fed_wage_growth_data.xlsx");
  await downloadOfficial("Atlanta Fed WGT",url,file);
  const parsed = await command(PYTHON, [path.join(ROOT, "parse_wgt_xlsx.py"), file]);
  const observations = JSON.parse(parsed.stdout).map((x) => ({ date: x.date, value: Number(x.value) })).filter((x) => Number.isFinite(x.value));
  if (!observations.length) throw new Error("Atlanta Fed WGT data_overall sheet is empty");
  return {...modelMetric(observations, { frequency:"月", availability: 5, accuracy: 4, note: "data_overall / Overall，未加权三个月移动平均；2026年10月官方无配对样本，不发布；缺月不补零", source: url }),definitionId:"wgt-overall-3ma-v2"};
}

async function main() {
  await ensureDirs();
  try {
    await fs.writeFile(LOCK_FILE, JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }), { flag: "wx" });
    lockAcquired = true;
  } catch {
    throw new Error("已有刷新任务正在运行，已退出以避免并发覆盖");
  }

  const previous = await readPriorMetrics();
  const seriesIds = [
    "DGS2", "DFF", "T5YIE", "T5YIFR", "CES0500000003", "UNRATE", "JTSJOL", "ICSA", "PPIACO", "DCOILWTICO",
    "DFII10", "BAMLH0A0HYM2", "BAMLC0A0CM", "VIXCLS", "DTWEXBGS", "NFCI",
  ];
  const series = {};
  for (const id of seriesIds) {
    try {
      series[id] = (await fetchFred(id)).observations;
      logLines.push(`FRED ${id}: ${latest(series[id])?.date ?? "无数据"}`);
    } catch (error) {
      warnings.push(`FRED ${id} 下载失败：${error.message}`);
    }
  }

  const metrics = {};
  const add = (row, value) => {
    const merged = mergeWithPrevious(value, row, previous);
    if (merged) metrics[String(row)] = merged;
  };
  const dgs2 = series.DGS2;
  const dff = series.DFF;
  const t5yie = series.T5YIE;
  const t5yifr = series.T5YIFR;
  if (dgs2 && dff) add(5, modelMetric(alignSubtract(dgs2, dff), { availability: 5, accuracy: 4, note: "2Y与有效联邦基金利率之差，包含2Y期限溢价", source: "FRED: DGS2-DFF" }));
  if (dgs2) add(6, modelMetric(lagDiff(dgs2, 20), { availability: 5, accuracy: 4, note: "捕捉政策路径重定价", source: "FRED: DGS2" }));
  if (dff) add(7, modelMetric(lagDiff(dff, 20), { availability: 5, accuracy: 5, note: "实际政策动作，离散且滞后于市场定价", source: "FRED: DFF" }));
  if (t5yie) {
    add(10, modelMetric(t5yie, { availability: 5, accuracy: 3, note: "含通胀风险与TIPS流动性溢价，不是纯预期", source: "FRED: T5YIE" }));
    add(11, modelMetric(lagDiff(t5yie, 20), { availability: 5, accuracy: 3, note: "适合看边际再定价", source: "FRED: T5YIE" }));
  }
  if (t5yifr) add(12, modelMetric(t5yifr, { availability: 5, accuracy: 3, note: "长期通胀锚，含风险与流动性成分", source: "FRED: T5YIFR" }));
  if (series.CES0500000003) add(15, modelMetric(yoyChange(series.CES0500000003, 12), { frequency: "月", availability: 5, accuracy: 3, note: "平均时薪同比；CES会月度及年度修订", source: "BLS/FRED: CES0500000003" }));
  try {
    add(16, await tryWageGrowthTracker(previous));
  } catch (error) {
    warnings.push(`Atlanta Fed WGT 未更新：${error.message}`);
    add(16, null);
  }
  if (series.UNRATE) add(17, modelMetric(series.UNRATE, { frequency: "月", availability: 5, accuracy: 4, note: "家庭调查月频；单月变化需谨慎", source: "BLS/FRED: UNRATE" }));
  if (series.JTSJOL) add(18, modelMetric(series.JTSJOL, { frequency: "月", availability: 5, accuracy: 3, note: "约1个月滞后，月度与年度修订较大", source: "BLS/FRED: JTSJOL" }));
  if (series.ICSA) add(19, modelMetric(rollingMean(series.ICSA, 4), { frequency: "周", availability: 5, accuracy: 4, note: "周频四周均值；受季调、假期与州级申报扰动", source: "DOL/FRED: ICSA" }));
  if (series.PPIACO) add(22, modelMetric(pctChange(series.PPIACO, 3), { frequency: "月", availability: 5, accuracy: 4, note: "广谱上游价格三个月变化，不等于最终消费价格", source: "BLS/FRED: PPIACO" }));
  if (series.DCOILWTICO) add(23, modelMetric(pctChange(series.DCOILWTICO, 60), { availability: 5, accuracy: 5, note: "高频能源价格变化，不能代表核心服务通胀", source: "EIA/FRED: DCOILWTICO" }));

  try {
    const acm = await tryAcmeTermPremium(previous);
    add(28, acm.level);
    add(29, acm.change);
    logLines.push(`NY Fed ACM: ${acm.latestDate}`);
  } catch (error) {
    warnings.push(`NY Fed ACM 未更新：${error.message}`);
    add(28, null);
    add(29, null);
  }
  if (series.DFII10) add(32, modelMetric(lagDiff(series.DFII10, 20), { availability: 5, accuracy: 4, note: "长久期估值的直接折现率通道", source: "FRED: DFII10" }));
  if (series.BAMLH0A0HYM2) add(33, modelMetric(lagDiff(series.BAMLH0A0HYM2, 20), { availability: 5, accuracy: 5, note: "信用风险与融资条件核心确认指标", source: "FRED: BAMLH0A0HYM2" }));
  if (series.BAMLC0A0CM) add(34, modelMetric(lagDiff(series.BAMLC0A0CM, 20), { availability: 5, accuracy: 5, note: "投资级信用条件确认指标", source: "FRED: BAMLC0A0CM" }));
  if (series.VIXCLS) add(35, modelMetric(series.VIXCLS, { availability: 5, accuracy: 5, note: "股票隐含波动；事件冲击快、均值回归也快", source: "CBOE/FRED: VIXCLS" }));
  if (series.DTWEXBGS) add(36, modelMetric(pctChange(series.DTWEXBGS, 20), { availability: 5, accuracy: 4, note: "全球美元流动性与风险偏好代理", source: "Fed/FRED: DTWEXBGS" }));
  if (series.NFCI) add(37, modelMetric(series.NFCI, { frequency: "周", availability: 5, accuracy: 4, note: "周频综合金融条件；负值代表相对宽松", source: "Chicago Fed/FRED: NFCI" }));

  for (const row of [5, 6, 7, 10, 11, 12, 15, 16, 17, 18, 19, 22, 23, 28, 29, 32, 33, 34, 35, 36, 37]) {
    if (!metrics[String(row)]) add(row, null);
  }

  // Removing missing FRED observations changes observation-count transforms.
  for (const row of [6,7,11,23,32,33,34,36]) if (metrics[row] && !metrics[row].stale) metrics[row].definitionId = "valid-observations-v2";
  const changes = snapshotChanges(metrics,priorSnapshots,runDate);

  const dates = Object.values(metrics).map((x) => x.date).filter(Boolean).sort();
  const snapshotDate = dates.at(-1) ?? runDate;
  const latestData = {
    generatedAt: new Date().toISOString(),
    runDate,
    snapshotDate,
    sourcePolicy: "官方源/FRED取数；保留原始文件与每次运行快照；失败时沿用上一有效值并标记 stale",
    metrics,
    modelVersion:MODEL_VERSION,
    changes,
    sourceStatus,
    reprocessedFrom:REPLAY_DIR ? "本日成功下载的官方原始文件，SHA256校验后重算" : null,
  };
  await fs.writeFile(LATEST_FILE, JSON.stringify(latestData, null, 2), "utf8");

  const outputFile = "君君美债利率模型_最新.xlsx";
  try {
    await command(process.execPath, [path.join(ROOT, "build_rate_model.mjs")], {
      cwd: ROOT,
      env: {
        ...process.env,
        RATE_MODEL_DATA: LATEST_FILE,
        RATE_MODEL_ASOF: snapshotDate,
        RATE_MODEL_OUTPUT_DIR: OUTPUT_DIR,
        RATE_MODEL_OUTPUT_FILE: outputFile,
      },
    });
    await fs.copyFile(path.join(OUTPUT_DIR, outputFile), path.join(ARCHIVE_DIR, `${runDate}.xlsx`));
    const summary = await readJson(path.join(OUTPUT_DIR,"model_summary.json"),{});
    latestData.scores = summary.scores;
    latestData.regime = summary.regime;
    logLines.push(`Excel已生成：${path.join(OUTPUT_DIR, outputFile)}`);
  } catch (error) {
    warnings.push(`Excel重算失败：${error.message}`);
    process.exitCode = 1;
  }

  await fs.writeFile(LATEST_FILE, JSON.stringify(latestData,null,2),"utf8");
  await fs.appendFile(HISTORY_FILE, `${JSON.stringify(latestData)}\n`, "utf8");

  if (warnings.length) logLines.push("警告：", ...warnings.map((x) => `- ${x}`));
  else logLines.push("完成：所有配置来源均成功更新");
  await fs.writeFile(path.join(LOG_DIR, `${runDate}.log`), `${logLines.join("\n")}\n`, "utf8");
  console.log(JSON.stringify({ runDate, snapshotDate, latestFile: LATEST_FILE, output: path.join(OUTPUT_DIR, outputFile), scores:latestData.scores,regime:latestData.regime,sourceStatus,warnings }, null, 2));
}

try {
  await main();
} finally {
  if (lockAcquired) await fs.rm(LOCK_FILE, { force: true });
}
