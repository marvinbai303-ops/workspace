"""重放已保存的 MCP 回执；不联网，不需要密钥，不自动生成市场买卖建议。"""
import json
import re
from pathlib import Path
from indicators import aggregate_stocks, breadth, mcclellan, equity_bond_spread

ROOT = Path(__file__).resolve().parent


def raw(name):
    envelope = json.loads((ROOT/'data'/f'raw_{name}.json').read_text())
    return json.loads(envelope['result']['content'][0]['text'])


def num(s):
    s = s.strip().replace(',', '')
    for suffix, factor in [('万亿', 1e12), ('亿', 1e8), ('万', 1e4), ('家', 1), ('%', 1)]:
        if s.endswith(suffix):
            return float(s[:-len(suffix)]) * factor
    return float(s)


def table(text):
    lines = [line for line in text.splitlines() if line.startswith('|')]
    return [[s.strip() for s in line.strip('|').split('|')] for line in lines[2:]]


def iso(s):
    s = s.replace('(日)', '')
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}' if re.fullmatch(r'\d{8}', s) else s


def run():
    sample_rows = []
    for code, name, date, volume, ret, amount in table(raw('stock_sample')['data']['answer']):
        sample_rows.append(dict(code=code, name=name, date=iso(date), return_pct=num(ret),
                                amount_yuan=num(amount), volume_shares=num(volume)))
    demo_breadth = aggregate_stocks(sample_rows, ['600519.SH', '600036.SH', '300750.SZ'])
    block = raw('mx_breadth_history')['data'][0]
    if any(len(r) != len(block['columns']) for r in block['items']):
        raise ValueError('家数序列长度不齐')
    mapping = {row[0]: row[1:] for row in block['items']}
    history = []
    for i, date in enumerate(block['columns'][1:]):
        history.append(dict(date=iso(date), **breadth(num(mapping['上涨家数'][i]),
                             num(mapping['下跌家数'][i]), num(mapping['平盘家数'][i]))))
    history.sort(key=lambda r: r['date'])
    mcl = mcclellan(history)
    normalized = mcclellan(history, normalized=True)
    zero_seed = mcclellan(history, seed='zero')
    wind_tables = raw('wind_group_amount')['data']['data']
    wind_values = {}
    for t in wind_tables:
        if len(t['columns']) != 1 or len(t['rows']) != 1:
            continue
        col = t['columns'][0]
        unit = col.get('unit')
        factor = {None:1, '亿元':1e8, '万亿元':1e12}.get(unit)
        if factor is None:
            raise ValueError(f'未知 Wind 单位 {unit}')
        wind_values[col['name']] = t['rows'][0][0]*factor
    prefix = '2026年11月13日沪深A股'
    wind_day = breadth(wind_values[prefix+'上涨家数'], wind_values[prefix+'下跌家数'],
                       wind_values[prefix+'平盘家数'], wind_values[prefix+'上涨家数成交额合计'],
                       wind_values[prefix+'下跌家数成交额合计'])
    wind_day.update(date='2026-11-13', source='Wind',
                    flat_amount_yuan=wind_values[prefix+'平盘家数成交额合计'],
                    basis='供应商分组汇总；明细仅返回100条，未以完整逐股数据独立重算')
    pe = {iso(row[2]): num(row[4]) for row in table(raw('index')['data']['answer'])}
    bond_response = raw('bond_sample')['data']
    bond = {iso(row[0]): num(row[1]) for row in table(bond_response['answer'])}
    metadata_end = iso(bond_response['indicator_description'][0]['终止日期'])
    spreads = []
    for date in sorted(pe.keys() & bond.keys()):
        valid = date <= metadata_end
        calculation = equity_bond_spread(pe[date], bond[date])
        formula_valid = calculation.pop('valid')
        spreads.append(dict(date=date, pe_ttm=pe[date], bond_yield_pct=bond[date],
                            metadata_date_valid=valid,
                            formula_valid=formula_valid, research_eligible=valid and formula_valid,
                            **calculation))
    result = dict(
        status='计算验证完成，非生产行情系统/非收益回测',
        source='个股/PE/国债：iFinD；历史涨跌家数：妙想(东方财富)；单日涨跌分组家数和成交额：Wind',
        three_stock_demo_only=demo_breadth,
        market_one_day_wind=wind_day,
        mcl_history_count=len(history), mcl_first_date=history[0]['date'],
        mcl_last_five=mcl[-5:], mcl_normalized_last_five=normalized[-5:],
        last_seed_sensitivity=mcl[-1]['mcl']-zero_seed[-1]['mcl'],
        stock_bond_proxy=spreads,
        caveats=[
            '3只股票仅验证 TRIN 和额价差的计算，不代表全市场。',
            '全市场单日另用 Wind 同次返回的家数和分组成交额计算，金额含展示舍入。',
            '2026-11-13 Wind 平盘65家，妙想57家；上涨744家和下跌4415家一致。未擅自认定差异原因。',
            '251条涨跌家数为供应商返回的板块数据，尚未以逐股明细和交易所日历独立核验完整性。',
            '博主股票池、平盘/停牌等细节未全公开，不能声称原图逐点一致。',
            f'国债元数据终止日期为{metadata_end}，晚于此日的返回值只保存算术结果，不作为有效研究观测。',
            'PE 回执确认 TTM/报表公告日期/剔除规则不调整，未明确确认整体法具体权重。',
            'iFinD 的板块上涨占比和总额、妙想的未分组成交总额不用于补造涨跌分组成交额。'
        ])
    for name, data in [('normalized_stock_sample.json', sample_rows), ('normalized_breadth_history.json', history),
                       ('mcl_series.json', mcl), ('demo_results.json', result)]:
        (ROOT/'data'/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['three_stock_demo_only','mcl_normalized_last_five']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    run()
