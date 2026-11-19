import json, pathlib, datetime, math, statistics, csv
ROOT=pathlib.Path(__file__).parent
D=ROOT/'data'
def read(id):return json.loads((D/(id+'.json')).read_text())
def text(id):return read(id)['content'][0]['text']
def rows(s):
    return [[x.strip() for x in l.strip('|').split('|')] for l in s.splitlines() if l.startswith('|')]
def tables(s):
    out=[];cur=[]
    for l in (s+'\n').splitlines():
        if l.startswith('|'):cur.append([x.strip() for x in l.strip('|').split('|')])
        elif cur:out.append(cur);cur=[]
    if cur:out.append(cur)
    return out
def norm(s):return s.split('.')[0].zfill(5)+'.HK' if s.endswith('.HK') else s
fundcodes=['009993','013841','016371','017489','017612','017745','162214']
names=['嘉实前沿创新','银华集成电路C','信澳业绩驱动C','嘉实信息产业C','宏利复兴C','嘉实绿色主题C','宏利领先中小盘']
stockpos={}
for id in ['q3_1','q3_2']:
    ts=tables(json.loads(text(id))['data']['answer'])
    for t in ts:
        inds=[i for i,h in enumerate(t[0]) if h.startswith('股票市值占基金资产净值比')]
        if inds:
            for row in t[2:]:stockpos[row[0][:6]]=float(row[inds[0]])/100
q3=json.loads(text('mx_q3'))['data'][1:]
funds=[]; holdings=[]; allstocks={}; h1raw=[]
for c,name in zip(fundcodes,names):
    tab=next(t for t in q3 if c+'.OF' in t['sheetName']); dic={r[0]:r[1:] for r in tab['items']}
    top=[{'code':code,'name':tab['columns'][i+1],'weight':float(dic['占净值比(%)'][i])/100,'period':'2026-09-30','role':'三季报披露'} for i,code in enumerate(dic['股票代码'])]
    topcodes={r['code'] for r in top}; sumtop=sum(r['weight'] for r in top)
    half=[]
    for row in rows(text('wind_h1_'+c)):
        if not row[0].isdigit():continue
        x={'code':norm(row[1]),'name':row[2],'weight':float(row[6])/100,'period':'2026-06-30','role':'半年报尾部候选'}
        h1raw.append({'fund':c,**x,'included':x['weight']>=.001 and x['code'] not in topcodes})
        if x['weight']>=.001 and x['code'] not in topcodes:half.append(x)
    den=sum(r['weight'] for r in half); remain=stockpos[c]-sumtop
    assert remain>=0 and den>0,(c,remain,den)
    for x in top:
        holdings.append({'fund':c,**x,'simple_weight':x['weight']*stockpos[c]/sumtop,'composite_weight':x['weight']})
        allstocks[x['code']]=x['name']
    for x in half:
        holdings.append({'fund':c,**x,'simple_weight':0,'composite_weight':remain*x['weight']/den})
        allstocks[x['code']]=x['name']
    funds.append({'code':c,'name':name,'stockpos':stockpos[c],'top_weight':sumtop,'tail_weight':remain,'half_tail_sum':den,'q3_count':len(top),'tail_count':len(half),'disclosure':'2026-10-26' if c=='013841' else '2026-10-27'})
prices={}; price_sources={}; conflicts=[]
for p in sorted(list(D.glob('price_*.json'))+list(D.glob('extra_price_*.json'))):
    raw=json.loads(p.read_text())['content'][0]['text']
    try: s=json.loads(raw)['data']['answer']
    except Exception: print('BAD PRICE',p.name,raw[:100]);continue
    for t in tables(s):
        if not any('收盘价' in h for h in t[0]):continue
        pi=next(i for i,h in enumerate(t[0]) if '收盘价' in h); di=next(i for i,h in enumerate(t[0]) if h=='日期')
        for row in t[2:]:
            try:code=norm(row[0]);date=row[di].replace('-','');v=float(row[pi])
            except Exception:continue
            if (code,date) in prices and abs(prices[code,date]-v)>1e-8:conflicts.append([code,date,prices[code,date],v])
            prices[code,date]=v;price_sources[code,date]=p.stem
dates=['20260930']+[(datetime.date(2026,10,8)+datetime.timedelta(days=i)).strftime('%Y%m%d') for i in range(37) if (datetime.date(2026,10,8)+datetime.timedelta(days=i)).weekday()<5]
dates=[d for d in dates if d<='20261113']
missing=[(c,d) for c in allstocks for d in dates if (c,d) not in prices]
nav={}
for id in ['nav_a1','nav_a2','nav_a3','nav_b']:
    for t in tables(json.loads(text(id))['data']['answer']):
        for r in t[2:]:nav[r[0][:6],r[2]]=float(r[3])
missingnav=[(c,d) for c in fundcodes for d in dates if (c,d) not in nav]
fx={r[0].replace('-',''):float(r[1]) for r in rows(json.loads(text('fx'))['data']['answer'])[2:]}
print(json.dumps({'funds':funds,'stock_count':len(allstocks),'date_count':len(dates),'missing_prices':missing,'missing_nav':missingnav,'conflicts':conflicts},ensure_ascii=False))
if missing or missingnav or conflicts:raise SystemExit(2)
stocklist=sorted(allstocks)
price_data=[{'code':c,'name':allstocks[c],'hk':c.endswith('.HK'),'prices':[prices[c,d] for d in dates],'sources':[price_sources[c,d] for d in dates]} for c in stocklist]
metrics=[]; daily=[]
for fund in funds:
    c=fund['code']; hs=[h for h in holdings if h['fund']==c]; es=[]; records=[]; sc=cc=1
    for i,d in enumerate(dates[1:],1):
        ret={x:prices[x,d]/prices[x,dates[i-1]]*(fx[d]/fx[dates[i-1]] if x.endswith('.HK') else 1)-1 for x in stocklist}
        actual=nav[c,d]/nav[c,dates[i-1]]-1
        simple=sum(h['simple_weight']*ret[h['code']] for h in hs)
        filled=sum(h['composite_weight']*ret[h['code']] for h in hs)
        correction=max(-.003,min(.003,.5*statistics.mean(es[-5:]))) if len(es)>=5 else 0
        comp=filled+correction; es.append(actual-filled); sc*=1+simple; cc*=1+comp
        r={'fund':c,'date':d,'actual':actual,'simple':simple,'filled':filled,'correction':correction,'composite':comp,'simple_error':simple-actual,'composite_error':comp-actual,'simple_curve':sc,'composite_curve':cc,'actual_curve':nav[c,d]/nav[c,dates[0]],'anchored_nav':nav[c,dates[i-1]]*(1+comp),'eligible':d>fund['disclosure'].replace('-','')};records.append(r);daily.append(r)
    for scope in ['全期事后模拟','披露后评估']:
        rr=records if scope=='全期事后模拟' else [r for r in records if r['eligible']]
        m={'fund':c,'scope':scope,'n':len(rr)}
        for model in ['simple','composite']:
            e=[r[model+'_error'] for r in rr];m[model+'_mae']=statistics.mean(abs(x) for x in e);m[model+'_rmse']=math.sqrt(statistics.mean(x*x for x in e));m[model+'_bias']=statistics.mean(e);m[model+'_max']=max(abs(x) for x in e);m[model+'_direction']=statistics.mean((r[model]>0)==(r['actual']>0) for r in rr)
        m['improvement']=1-m['composite_mae']/m['simple_mae'];metrics.append(m)
out={'funds':funds,'holdings':holdings,'h1raw':h1raw,'stocks':price_data,'dates':dates,'fx':[fx[d] for d in dates],'nav':{c:[nav[c,d] for d in dates] for c in fundcodes},'daily':daily,'metrics':metrics}
(ROOT/'model.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'metrics':metrics},ensure_ascii=False))
for fname,data in [('每日预估与实际对照.csv',daily),('误差统计.csv',metrics)]:
    with (ROOT/fname).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=data[0].keys());w.writeheader();w.writerows(data)
