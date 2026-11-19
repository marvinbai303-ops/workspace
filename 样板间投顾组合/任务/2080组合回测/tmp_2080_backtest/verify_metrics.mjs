import fs from "node:fs/promises";

const rows = JSON.parse(await fs.readFile("yellow_input_snapshot.json", "utf8"));
const p = {
  initial: [0.10, 0.10, 0.75, 0.05],
  target: 0.20,
  lower: 0.15,
  upper: 0.25,
  minDays: 7,
  annualFee: 0.005,
  tradingDays: 250,
  rf: 0,
  feeDayBasis: 365,
};

const asDate = (serial) => new Date(Date.UTC(1899, 11, 30) + serial * 86400000);
const year = (serial) => asDate(serial).getUTCFullYear();
const month = (serial) => asDate(serial).getUTCMonth() + 1;

let holdings = [...p.initial];
let lastRebalanceSerial = rows[0].date_serial;
let lastMonthEndNav = holdings.reduce((a, b) => a + b, 0);
let runningPeak = lastMonthEndNav;
let yearPeak = lastMonthEndNav;
let currentYear = year(rows[0].date_serial);
const navs = [];
const dailyReturns = [];
const drawdowns = [];
const monthReturns = [];
const yearDrawdowns = new Map();
const actions = new Map();

for (let i = 0; i < rows.length; i += 1) {
  const row = rows[i];
  const currentDate = row.date_serial;
  const currentYearValue = year(currentDate);
  const currentMonthValue = month(currentDate);
  const assetNavs = [row.industry_nav, row.index_nav, row.bond_nav, row.gold_nav];

  if (i > 0) {
    const prior = rows[i - 1];
    const priorNavs = [prior.industry_nav, prior.index_nav, prior.bond_nav, prior.gold_nav];
    holdings = holdings.map((value, j) => value * (assetNavs[j] / priorNavs[j]));
  }

  const preTotal = holdings.reduce((a, b) => a + b, 0);
  const equityWeight = (holdings[0] + holdings[1]) / preTotal;
  const next = rows[i + 1];
  const annual = Boolean(next) && currentMonthValue === 12 && currentYearValue !== year(next.date_serial);
  const quarterly = Boolean(next) && currentMonthValue % 3 === 0 && currentMonthValue !== month(next.date_serial);
  const dynamic = equityWeight > p.upper || equityWeight < p.lower;
  let action = i === 0 ? "初始配置" : "不调";

  if (i > 0 && (annual || quarterly || dynamic)) {
    if (currentDate - lastRebalanceSerial <= p.minDays) {
      action = "间隔规则跳过";
    } else if (annual) {
      action = "年末+季度";
    } else if (quarterly && dynamic) {
      action = "季度+动态";
    } else if (quarterly) {
      action = "季度";
    } else {
      action = "动态";
    }
  }

  const outer = action === "年末+季度" || action === "季度+动态" || action === "动态";
  const equalEquity = action === "年末+季度" || action === "季度+动态" || action === "季度";
  if (outer || equalEquity) {
    const equityTotal = outer ? preTotal * p.target : holdings[0] + holdings[1];
    if (equalEquity) {
      holdings[0] = equityTotal / 2;
      holdings[1] = equityTotal / 2;
    } else {
      const currentEquityTotal = holdings[0] + holdings[1];
      holdings[0] = equityTotal * (currentEquityTotal === 0 ? 0.5 : holdings[0] / currentEquityTotal);
      holdings[1] = equityTotal * (currentEquityTotal === 0 ? 0.5 : holdings[1] / currentEquityTotal);
    }
    if (outer) {
      const incomeTotal = holdings[2] + holdings[3];
      const targetIncomeTotal = preTotal * (1 - p.target);
      if (incomeTotal === 0) {
        holdings[2] = targetIncomeTotal * p.initial[2] / (p.initial[2] + p.initial[3]);
        holdings[3] = targetIncomeTotal * p.initial[3] / (p.initial[2] + p.initial[3]);
      } else {
        holdings[2] = targetIncomeTotal * holdings[2] / incomeTotal;
        holdings[3] = targetIncomeTotal * holdings[3] / incomeTotal;
      }
    }
  }

  if (["年末+季度", "季度+动态", "季度", "动态"].includes(action)) {
    lastRebalanceSerial = currentDate;
  }
  actions.set(action, (actions.get(action) ?? 0) + 1);

  const feeFactor = i === 0 ? 1 : Math.pow(1 - p.annualFee, (currentDate - rows[i - 1].date_serial) / p.feeDayBasis);
  holdings = holdings.map((value) => value * feeFactor);
  const nav = holdings.reduce((a, b) => a + b, 0);
  navs.push(nav);
  if (i > 0) dailyReturns.push(nav / navs[i - 1] - 1);
  runningPeak = Math.max(runningPeak, nav);
  drawdowns.push(nav / runningPeak - 1);

  if (currentYearValue !== currentYear) {
    currentYear = currentYearValue;
    yearPeak = nav;
  } else {
    yearPeak = Math.max(yearPeak, nav);
  }
  const yearDrawdown = nav / yearPeak - 1;
  yearDrawdowns.set(currentYearValue, Math.min(yearDrawdowns.get(currentYearValue) ?? 0, yearDrawdown));

  const monthEnd = !next || currentMonthValue !== month(next.date_serial);
  if (monthEnd) {
    monthReturns.push({ year: currentYearValue, month: currentMonthValue, value: nav / lastMonthEndNav - 1 });
    lastMonthEndNav = nav;
  }
}

const average = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
const variance = dailyReturns.reduce((sum, value) => sum + Math.pow(value - average, 2), 0) / (dailyReturns.length - 1);
const annualized = average * p.tradingDays;
const volatility = Math.sqrt(variance) * Math.sqrt(p.tradingDays);
const maxDrawdown = Math.min(...drawdowns);
const cumulative = navs.at(-1) / navs[0] - 1;
const cagr = Math.pow(navs.at(-1) / navs[0], p.feeDayBasis / (rows.at(-1).date_serial - rows[0].date_serial)) - 1;

console.log(JSON.stringify({
  cumulative,
  arithmeticAnnualizedReturn: annualized,
  annualizedVolatility: volatility,
  maxDrawdown,
  sharpe: (annualized - p.rf) / volatility,
  calmar: cagr / Math.abs(maxDrawdown),
  endingNav: navs.at(-1),
  endingEquityWeight: (holdings[0] + holdings[1]) / navs.at(-1),
  actions: Object.fromEntries(actions),
  monthWinRate: monthReturns.filter((item) => item.value > 0).length / monthReturns.length,
  months: monthReturns.length,
  yearDrawdowns: Object.fromEntries(yearDrawdowns),
}, null, 2));
