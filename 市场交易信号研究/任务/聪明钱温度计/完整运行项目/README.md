# 聪明钱温度计

私有在线看板：https://smart-money-thermometer-yg-20261117.partedpatio16.chatgpt.site

本地打开 `聪明钱温度计.html`。包含总览、逐项点评、历史走势、公式与用法、来源和口径。

每天北京时间12:00和17:00在当前Codex对话运行，非交易日跳过；查看 data/schedule.json。日程创建不等同于每次取数成功，以运行日志和看板日期为准。

数据及更新操作见 UPDATE_GUIDE.md。从已验收文件重新生成：`python3 -B assemble.py`。只更新数据无需重发网站，使用已连接的 update_thermometer 后 get_thermometer 读回核对。
