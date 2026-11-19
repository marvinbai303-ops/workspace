# 样板间组合日报 20260723

- 状态：FAILED
- 数据日期：20260723
- 完成时间：2026-07-23T23:28:49.454749+08:00
- 运行次数：1

## 失败/阻塞原因
- iFinD 底层净值重算未完成：Traceback (most recent call last):
  File "/Users/yangguang/Documents/Codex/workspace/样板间组合每日预估净值/ifind_recalc_excel.py", line 688, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/yangguang/Documents/Codex/workspace/样板间组合每日预估净值/ifind_recalc_excel.py", line 613, in main
    navs, parsed_dates, raw_result = fetch_ifind_navs(codes, target_date, outdir, args.batch_size, args.delay_ms)
                                     ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yangguang/Documents/Codex/workspace/样板间组合每日预估净值/ifind_recalc_excel.py", line 225, in fetch_ifind_navs
    raise RuntimeError(f'iFinD 查询失败：{proc.stderr.strip() or proc.stdout.strip()}')
RuntimeError: iFinD 查询失败：Error: Request timeout after 60s
    at ClientRequest.<anonymous> (/Users/yangguang/.codex/skills/ifind-finance-data/call-node.js:73:20)
    at ClientRequest.emit (node:events:509:28)
    at TLSSocket.emitRequestTimeout (node:_http_client:948:9)
    at Object.onceWrapper (node:events:630:28)
    at TLSSocket.emit (node:events:521:24)
    at Socket._onTimeout (node:net:610:8)
    at listOnTimeout (node:internal/timers:605:17)
    at process.processTimers (node:internal/timers:541:7)

## 附件
- portfolio_overview.png
- strategy_10_90.png
- strategy_30_70.png
- strategy_industry_trend.png

本邮件由 Codex 自动任务生成。数据仅供预览使用，最终务必以系统数据为准。