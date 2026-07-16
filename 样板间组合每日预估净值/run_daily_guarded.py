#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样板间组合日报守门脚本。

职责：
  1. 从 21:30 开始每 30 分钟检查一次 Excel 底层净值是否刷新，直到 23:00。
  2. 执行底层基金/组合涨跌异常检测。
  3. 通过检查后调用 excel_daily_report.py 生成报表。
  4. 写入每日摘要和 JSONL 运行日志；当天已成功时默认跳过，避免重复运作。
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from openpyxl import load_workbook

import excel_daily_report as report

EXCEL_FILE = '样板间投顾组合监控模板-202600710调仓.xlsx'
OUTDIR = 'reports'
LOGDIR = 'reports/run_logs'
RUN_LOG = 'reports/run_logs/daily_run_log.jsonl'
EXPECTED_FUND_COUNT = 24
MONEY_CODES = {'000917.OF'}
PORTFOLIO_ORDER = ['产业趋势', '产业趋势基石', '产业趋势2号', '10-90', '10-90基石', '30-70']
REPORT_IMAGE_FILES = ['portfolio_overview.png', 'strategy_10_90.png', 'strategy_30_70.png', 'strategy_industry_trend.png']
SLACK_CHANNEL_ID = 'C0BHVGDAHN0'


def now_cn():
    return dt.datetime.now().astimezone()


def parse_date(text):
    return dt.datetime.strptime(text, '%Y%m%d').date()


def as_ymd(value):
    return value.strftime('%Y%m%d')


def parse_hhmm(text):
    hour, minute = text.split(':', 1)
    return int(hour), int(minute)


def today_target():
    return now_cn().date()


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def summary_path(target_date):
    return Path(LOGDIR) / f'summary_{as_ymd(target_date)}.json'


def email_digest_path(target_date):
    return Path(LOGDIR) / f'email_digest_{as_ymd(target_date)}.md'


def email_payload_path(target_date):
    return Path(LOGDIR) / f'email_payload_{as_ymd(target_date)}.json'


def slack_payload_path(target_date):
    return Path(LOGDIR) / f'slack_payload_{as_ymd(target_date)}.json'


def required_outputs(outdir):
    return [Path(outdir) / name for name in REPORT_IMAGE_FILES] + [Path(outdir) / 'daily_report_from_excel.json']


def load_existing_summary(target_date):
    path = summary_path(target_date)
    if not path.exists():
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def already_successful(target_date, outdir):
    existing = load_existing_summary(target_date)
    if not existing or existing.get('status') not in ('SUCCESS', 'WARN'):
        return False, existing
    outputs = required_outputs(outdir)
    return all(path.exists() for path in outputs), existing


def next_attempt_time(current, interval_minutes):
    base = current.replace(second=0, microsecond=0)
    minute = (base.minute // interval_minutes + 1) * interval_minutes
    if minute >= 60:
        return (base.replace(minute=0) + dt.timedelta(hours=1))
    return base.replace(minute=minute)


def read_fund_snapshot(wb):
    names, navs = report.read_fund_navs(wb)
    dates = sorted(navs)
    latest = dates[-1] if dates else None
    previous = dates[-2] if len(dates) >= 2 else None
    latest_navs = navs.get(latest, {}) if latest else {}
    previous_navs = navs.get(previous, {}) if previous else {}
    return {
        'names': names,
        'navs': navs,
        'dates': dates,
        'latest': latest,
        'previous': previous,
        'latest_navs': latest_navs,
        'previous_navs': previous_navs,
    }


def inspect_excel(excel_path, target_date, fund_warn_threshold, fund_fail_threshold,
                  portfolio_warn_threshold, portfolio_fail_threshold,
                  stale_equal_limit):
    wb = load_workbook(excel_path, data_only=True, read_only=True)
    fund = read_fund_snapshot(wb)
    blocking = []
    warnings = []
    info = {
        'target_date': as_ymd(target_date),
        'fund_latest_date': as_ymd(fund['latest']) if fund['latest'] else None,
        'fund_previous_date': as_ymd(fund['previous']) if fund['previous'] else None,
        'fund_count': len(fund['latest_navs']),
        'stale_equal_codes': [],
        'fund_return_warnings': [],
        'fund_return_failures': [],
        'portfolio_return_warnings': [],
        'portfolio_return_failures': [],
    }

    if fund['latest'] != target_date:
        blocking.append(f'底层基金最新净值日期为 {info["fund_latest_date"] or "无"}，未到目标日期 {as_ymd(target_date)}')
    if len(fund['latest_navs']) < EXPECTED_FUND_COUNT:
        blocking.append(f'底层基金净值数量不足：{len(fund["latest_navs"])}/{EXPECTED_FUND_COUNT}')

    if fund['latest'] == target_date and fund['previous']:
        for code, latest_nav in sorted(fund['latest_navs'].items()):
            if code in MONEY_CODES:
                continue
            previous_nav = fund['previous_navs'].get(code)
            if not previous_nav:
                continue
            daily_ret = latest_nav / previous_nav - 1.0
            if abs(latest_nav - previous_nav) <= 1e-12:
                info['stale_equal_codes'].append(code)
            if abs(daily_ret) >= fund_fail_threshold:
                info['fund_return_failures'].append({
                    'code': code,
                    'name': fund['names'].get(code, code),
                    'daily_return': daily_ret,
                })
            elif abs(daily_ret) >= fund_warn_threshold:
                info['fund_return_warnings'].append({
                    'code': code,
                    'name': fund['names'].get(code, code),
                    'daily_return': daily_ret,
                })

        if len(info['stale_equal_codes']) >= stale_equal_limit:
            blocking.append(
                f'{len(info["stale_equal_codes"])} 只非货币基金净值与上一日期完全相同，疑似 Excel 未完整刷新'
            )
        elif info['stale_equal_codes']:
            warnings.append(
                f'{len(info["stale_equal_codes"])} 只非货币基金净值与上一日期相同，建议人工确认'
            )

    if info['fund_return_failures']:
        blocking.append(f'{len(info["fund_return_failures"])} 只基金日涨跌幅超过 {fund_fail_threshold:.0%}')
    if info['fund_return_warnings']:
        warnings.append(f'{len(info["fund_return_warnings"])} 只基金日涨跌幅超过 {fund_warn_threshold:.0%}')

    try:
        res, asof = report.build_report(excel_path)
        info['portfolio_asof'] = asof
        info['portfolios'] = {}
        if parse_date(asof) != target_date:
            blocking.append(f'组合净值最新日期为 {asof}，未到目标日期 {as_ymd(target_date)}')
        for name in PORTFOLIO_ORDER:
            item = res.get(name)
            if not item:
                blocking.append(f'缺少组合结果：{name}')
                continue
            day_ret = item['day_ret']
            info['portfolios'][name] = {
                'nav': item['nav'],
                'day_ret': day_ret,
                'cum': item['cum'],
            }
            if abs(day_ret) >= portfolio_fail_threshold:
                info['portfolio_return_failures'].append({'name': name, 'daily_return': day_ret})
            elif portfolio_warn_threshold and abs(day_ret) >= portfolio_warn_threshold:
                info['portfolio_return_warnings'].append({'name': name, 'daily_return': day_ret})
    except Exception as exc:
        blocking.append(f'组合报表读取失败：{exc}')

    if info['portfolio_return_failures']:
        blocking.append(f'{len(info["portfolio_return_failures"])} 个组合日涨跌幅超过 {portfolio_fail_threshold:.0%}')
    if info['portfolio_return_warnings']:
        warnings.append(f'{len(info["portfolio_return_warnings"])} 个组合日涨跌幅超过 {portfolio_warn_threshold:.0%}')

    info['blocking'] = blocking
    info['warnings'] = warnings
    info['ready'] = not blocking
    return info


def run_report(excel_path, outdir):
    cmd = [sys.executable, 'excel_daily_report.py', '--excel', excel_path, '--outdir', outdir]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        'command': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }


def run_ifind_recalc(excel_path, target_date, stale_equal_limit, nav_json=None):
    cmd = [
        sys.executable,
        'ifind_recalc_excel.py',
        '--excel',
        excel_path,
        '--target-date',
        as_ymd(target_date),
        '--outdir',
        LOGDIR,
        '--stale-equal-limit',
        str(stale_equal_limit),
    ]
    if nav_json:
        cmd.extend(['--nav-json', nav_json])
    proc = subprocess.run(cmd, text=True, capture_output=True)
    log_path = Path(LOGDIR) / f'ifind_recalc_{as_ymd(target_date)}.json'
    detail = None
    if log_path.exists():
        try:
            with open(log_path, encoding='utf-8') as f:
                detail = json.load(f)
        except Exception:
            detail = None
    return {
        'command': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'log_path': str(log_path),
        'detail': detail,
    }


def build_summary(status, target_date, started_at, attempts, final_check=None,
                  report_run=None, skipped=False, reason=None):
    summary = {
        'status': status,
        'target_date': as_ymd(target_date),
        'started_at': started_at.isoformat(),
        'finished_at': now_cn().isoformat(),
        'skipped': skipped,
        'reason': reason,
        'attempt_count': len(attempts),
        'attempts': attempts,
        'final_check': final_check,
        'report_run': report_run,
    }
    return summary


def pct(value):
    return f'{value:.2%}'


def write_email_payload(summary, target_date, outdir, recipient):
    final = summary.get('final_check') or {}
    status = summary.get('status')
    subject_date = summary.get('target_date', as_ymd(target_date))
    subject = f'样板间组合日报 {subject_date} [{status}]'
    lines = [
        f'# 样板间组合日报 {subject_date}',
        '',
        f'- 状态：{status}',
        f'- 数据日期：{final.get("portfolio_asof") or final.get("target_date") or subject_date}',
        f'- 完成时间：{summary.get("finished_at")}',
        f'- 运行次数：{summary.get("attempt_count")}',
    ]
    if summary.get('reason'):
        lines.append(f'- 说明：{summary["reason"]}')
    lines.append('')

    portfolios = final.get('portfolios') or {}
    if portfolios:
        lines.extend([
            '| 组合 | 模拟净值 | 今日涨跌 | 累计涨跌 |',
            '|---|---:|---:|---:|',
        ])
        for name in PORTFOLIO_ORDER:
            item = portfolios.get(name)
            if not item:
                continue
            lines.append(f'| {name} | {item["nav"]:.4f} | {pct(item["day_ret"])} | {pct(item["cum"])} |')
        lines.append('')

    warnings = final.get('warnings') or []
    blocking = final.get('blocking') or []
    if warnings:
        lines.append('## 警告')
        lines.extend(f'- {msg}' for msg in warnings)
        lines.append('')
    if blocking:
        lines.append('## 失败/阻塞原因')
        lines.extend(f'- {msg}' for msg in blocking)
        lines.append('')

    lines.extend([
        '## 附件',
        '- portfolio_overview.png',
        '- strategy_10_90.png',
        '- strategy_30_70.png',
        '- strategy_industry_trend.png',
        '',
        '本邮件由 Codex 自动任务生成。数据仅供预览使用，最终务必以系统数据为准。',
    ])

    digest = '\n'.join(lines)
    digest_path = email_digest_path(target_date)
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(digest, encoding='utf-8')

    attachments = [str((Path(outdir) / name).resolve()) for name in REPORT_IMAGE_FILES if (Path(outdir) / name).exists()]
    payload = {
        'to': recipient,
        'subject': subject,
        'body': digest,
        'body_file': str(digest_path.resolve()),
        'content_type': 'text/markdown',
        'attachment_files': [],
        'optional_attachment_files': attachments,
        'summary_path': str(summary_path(target_date).resolve()),
        'status': status,
        'target_date': subject_date,
    }
    atomic_write_json(email_payload_path(target_date), payload)
    return payload


def write_slack_payload(summary, target_date, outdir, channel_id):
    final = summary.get('final_check') or {}
    status = summary.get('status')
    subject_date = summary.get('target_date', as_ymd(target_date))
    lines = [
        f'*样板间组合日报 {subject_date} [{status}]*',
        '',
    ]
    if summary.get('reason'):
        lines.append(f'说明：{summary["reason"]}')
        lines.append('')

    portfolios = final.get('portfolios') or {}
    if portfolios:
        lines.extend([
            '| 组合 | 模拟净值 | 今日涨跌 | 累计涨跌 |',
            '|---|---:|---:|---:|',
        ])
        for name in PORTFOLIO_ORDER:
            item = portfolios.get(name)
            if not item:
                continue
            lines.append(f'| {name} | {item["nav"]:.4f} | {pct(item["day_ret"])} | {pct(item["cum"])} |')
        lines.append('')

    warnings = final.get('warnings') or []
    blocking = final.get('blocking') or []
    if warnings:
        lines.append('*警告*')
        lines.extend(f'- {msg}' for msg in warnings)
        lines.append('')
    if blocking:
        lines.append('*失败/阻塞原因*')
        lines.extend(f'- {msg}' for msg in blocking)
        lines.append('')

    attachments = [str((Path(outdir) / name).resolve()) for name in REPORT_IMAGE_FILES if (Path(outdir) / name).exists()]
    payload = {
        'channel_id': channel_id,
        'message': '\n'.join(lines),
        'attachment_files': attachments,
        'status': status,
        'target_date': subject_date,
    }
    atomic_write_json(slack_payload_path(target_date), payload)
    return payload


def print_summary(summary):
    print(f'状态：{summary["status"]}')
    print(f'目标日期：{summary["target_date"]}')
    final = summary.get('final_check') or {}
    if final.get('portfolios'):
        print('组合结果：')
        for name in PORTFOLIO_ORDER:
            item = final['portfolios'].get(name)
            if not item:
                continue
            print(f'  {name}: 净值 {item["nav"]:.4f}, 今日 {item["day_ret"]:.2%}, 累计 {item["cum"]:.2%}')
    if final.get('warnings'):
        print('警告：')
        for msg in final['warnings']:
            print(f'  - {msg}')
    if final.get('blocking'):
        print('失败原因：')
        for msg in final['blocking']:
            print(f'  - {msg}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--excel', default=EXCEL_FILE)
    ap.add_argument('--outdir', default=OUTDIR)
    ap.add_argument('--target-date', default=None, help='YYYYMMDD，默认当天')
    ap.add_argument('--start-time', default='21:30')
    ap.add_argument('--deadline', default='23:00')
    ap.add_argument('--interval-minutes', type=int, default=30)
    ap.add_argument('--fund-warn-threshold', type=float, default=0.10)
    ap.add_argument('--fund-fail-threshold', type=float, default=0.20)
    ap.add_argument('--portfolio-warn-threshold', type=float, default=0.0,
                    help='组合日涨跌警告阈值；0 表示不启用组合 WARN')
    ap.add_argument('--portfolio-fail-threshold', type=float, default=0.10)
    ap.add_argument('--stale-equal-limit', type=int, default=3)
    ap.add_argument('--force', action='store_true', help='忽略当天成功日志，重新检查并生成')
    ap.add_argument('--once', action='store_true', help='只检查一次，不等待；用于人工验证')
    ap.add_argument('--skip-ifind-recalc', action='store_true',
                    help='跳过 iFinD 底层净值重算，直接检查 Excel 现有缓存')
    ap.add_argument('--ifind-nav-json', default=None,
                    help='备用：使用已经取好的底层基金净值 JSON 重算，不再调用本地 iFinD HTTP')
    ap.add_argument('--email-to', default='me', help='写入邮件 payload 的收件人；me 表示当前已连接 Gmail 本人')
    ap.add_argument('--slack-channel-id', default=SLACK_CHANNEL_ID, help='写入 Slack payload 的频道 ID')
    args = ap.parse_args()

    target_date = parse_date(args.target_date) if args.target_date else today_target()
    started_at = now_cn()
    ok, existing = already_successful(target_date, args.outdir)
    if ok and not args.force:
        summary = build_summary(
            'SKIPPED',
            target_date,
            started_at,
            [],
            final_check=existing.get('final_check'),
            skipped=True,
            reason='当天已有 SUCCESS/WARN 摘要且输出文件存在，跳过重复运作',
        )
        write_email_payload(summary, target_date, args.outdir, args.email_to)
        write_slack_payload(summary, target_date, args.outdir, args.slack_channel_id)
        append_jsonl(RUN_LOG, summary)
        print_summary(summary)
        return 0

    start_hour, start_minute = parse_hhmm(args.start_time)
    deadline_hour, deadline_minute = parse_hhmm(args.deadline)
    start_dt = dt.datetime.combine(started_at.date(), dt.time(start_hour, start_minute)).astimezone()
    deadline_dt = dt.datetime.combine(started_at.date(), dt.time(deadline_hour, deadline_minute)).astimezone()
    attempts = []
    final_check = None

    while True:
        current = now_cn()
        ifind_run = None
        if not args.skip_ifind_recalc:
            ifind_run = run_ifind_recalc(args.excel, target_date, args.stale_equal_limit, args.ifind_nav_json)
            if ifind_run['returncode'] != 0:
                detail = ifind_run.get('detail') or {}
                reason = detail.get('reason') or ifind_run.get('stderr') or ifind_run.get('stdout') or 'iFinD 重算失败'
                check = {
                    'target_date': as_ymd(target_date),
                    'ready': False,
                    'blocking': [f'iFinD 底层净值重算未完成：{reason.strip()}'],
                    'warnings': [],
                    'ifind_recalc': ifind_run,
                }
            else:
                check = inspect_excel(
                    args.excel,
                    target_date,
                    args.fund_warn_threshold,
                    args.fund_fail_threshold,
                    args.portfolio_warn_threshold,
                    args.portfolio_fail_threshold,
                    args.stale_equal_limit,
                )
                check['ifind_recalc'] = ifind_run
        else:
            check = inspect_excel(
                args.excel,
                target_date,
                args.fund_warn_threshold,
                args.fund_fail_threshold,
                args.portfolio_warn_threshold,
                args.portfolio_fail_threshold,
                args.stale_equal_limit,
            )
        attempt = {
            'checked_at': current.isoformat(),
            'ready': check['ready'],
            'fund_latest_date': check.get('fund_latest_date'),
            'portfolio_asof': check.get('portfolio_asof'),
            'blocking': check.get('blocking', []),
            'warnings': check.get('warnings', []),
            'ifind_recalc': {
                'returncode': ifind_run.get('returncode'),
                'log_path': ifind_run.get('log_path'),
            } if ifind_run else None,
        }
        attempts.append(attempt)
        final_check = check

        if check['ready']:
            report_run = run_report(args.excel, args.outdir)
            status = 'SUCCESS' if not check['warnings'] else 'WARN'
            if report_run['returncode'] != 0:
                status = 'FAILED'
                check['blocking'].append('报表生成脚本失败')
            summary = build_summary(status, target_date, started_at, attempts, check, report_run)
            write_email_payload(summary, target_date, args.outdir, args.email_to)
            write_slack_payload(summary, target_date, args.outdir, args.slack_channel_id)
            atomic_write_json(summary_path(target_date), summary)
            append_jsonl(RUN_LOG, summary)
            print(report_run.get('stdout', ''), end='')
            if report_run.get('stderr'):
                print(report_run['stderr'], file=sys.stderr, end='')
            print_summary(summary)
            return 0 if status in ('SUCCESS', 'WARN') else 1

        if args.once or current >= deadline_dt:
            summary = build_summary('FAILED', target_date, started_at, attempts, check)
            write_email_payload(summary, target_date, args.outdir, args.email_to)
            write_slack_payload(summary, target_date, args.outdir, args.slack_channel_id)
            atomic_write_json(summary_path(target_date), summary)
            append_jsonl(RUN_LOG, summary)
            print_summary(summary)
            return 1

        next_time = next_attempt_time(max(current, start_dt), args.interval_minutes)
        if next_time > deadline_dt:
            next_time = deadline_dt
        sleep_seconds = max(0, (next_time - now_cn()).total_seconds())
        print(f'数据未就绪，下一次检查：{next_time.strftime("%H:%M")}')
        time.sleep(sleep_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
