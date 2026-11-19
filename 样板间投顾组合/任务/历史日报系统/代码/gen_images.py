#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把当日组合预估净值渲染成 4 张 PNG（复刻同组"样板间组合日报"版式）：
  样板间组合业绩概览_YYYYMMDD.png / 10-90策略_.png / 30-70策略_.png / 产业趋势策略_.png
依赖：Pillow + Noto Sans CJK SC。复用 daily_monitor 的计算引擎。
用法：python3 gen_images.py --config config.json --nav nav_history.csv [--asof YYYYMMDD] [--outdir reports]
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont
import daily_monitor as dm

FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SC = 2  # 简体中文字面
def F(sz, bold=False): return ImageFont.truetype(FB if bold else FR, sz, index=SC)

WHITE=(255,255,255); INK=(43,50,64); GREY=(140,150,164)
SLATE=(56,65,79); POS=(196,54,44); NEG=(43,108,204)
HEADBG=(238,241,245); LINE=(236,239,243); DISC=(150,160,174); DISCBG=(250,251,252)
CARDBORDER=(228,232,238)

STRAT = {
 '10/90':   {'members':['10-90基石','10-90'],                 'color':(124,92,217), 'tint':(236,231,248)},
 '30/70':   {'members':['30-70'],                             'color':(232,115,12), 'tint':(252,238,225)},
 '产业趋势': {'members':['产业趋势基石','产业趋势','产业趋势2号'],'color':(45,111,209), 'tint':(230,238,251)},
}
ORDER = ['10/90','30/70','产业趋势']

W = 1180
Lx = 40           # 左边距（文字起点）
Rx = W - 40

def clr(x): return POS if x >= 0 else NEG
def cT(d, xy, t, f, fill, anchor='lm'): d.text(xy, t, font=f, fill=fill, anchor=anchor)

# 列中心 x（总览表）
OV = {'name':Lx, 'date':500, 'fee':620, 'nav':760, 'day':920, 'cum':1080}
# 列中心 x（持仓表）
HD = {'name':Lx, 'w':500, 'day':650, 'cd':800, 'cum':960, 'cc':1100}

def header_bar(d, y, title, asof, bg, sub):
    d.rectangle([0,y,W,y+82], fill=bg)
    cT(d,(Lx,y+41),title,F(34,True),WHITE,'lm')
    cT(d,(Rx,y+41),f"更新日期：{asof[:4]}-{asof[4:6]}-{asof[6:]}",F(20),sub,'rm')
    return y+82

def disclaimer(d, y):
    d.rectangle([0,y,W,y+48], fill=DISCBG)
    cT(d,(Lx,y+24),"数据基于底层基金涨跌幅加权+费率估算，AI推送，仅供预览使用，最终务必以系统数据为准",F(17),DISC,'lm')
    return y+48

def ov_header(d, y):
    d.rectangle([0,y,W,y+52], fill=HEADBG)
    g=F(18); c=(90,100,114)
    cT(d,(OV['name'],y+26),"组合名称",g,c,'lm')
    for k,lab in [('date','上线日期'),('fee','年费率'),('nav','模拟净值'),('day','今日涨跌幅'),('cum','累计涨跌幅')]:
        cT(d,(OV[k],y+26),lab,g,c,'mm')
    return y+52

def ov_row(d, y, pname, r):
    h=58
    cT(d,(OV['name'],y+h/2),dm.disp(pname),F(22,True),INK,'lm')
    cT(d,(OV['date'],y+h/2),f'{r["start"][:4]}-{r["start"][4:6]}-{r["start"][6:]}',F(19),GREY,'mm')
    cT(d,(OV['fee'],y+h/2),dm.wfmt(r['fee']),F(19),GREY,'mm')
    cT(d,(OV['nav'],y+h/2),f'{r["nav"]:.4f}',F(21,True),INK,'mm')
    cT(d,(OV['day'],y+h/2),dm.pct(r['day_ret']),F(21,True),clr(r['day_ret']),'mm')
    cT(d,(OV['cum'],y+h/2),dm.pct(r['cum']),F(21,True),clr(r['cum']),'mm')
    d.line([Lx-16,y+h,Rx+16,y+h],fill=LINE,width=1)
    return y+h

def group_head(d, y, st, label):
    h=46; c=st['color']
    d.rectangle([0,y,W,y+h], fill=st['tint'])
    d.rectangle([0,y,5,y+h], fill=c)
    cT(d,(Lx,y+h/2),f"{label} 策略",F(21,True),c,'lm')
    return y+h

def sec_title(d, y, st, text):
    h=54; c=st['color']
    d.rectangle([Lx-16,y+6,Rx+16,y+h], fill=st['tint'])
    d.rectangle([Lx-16,y+6,Lx-11,y+h], fill=c)
    cT(d,(Lx,y+6+(h-6)/2),text,F(24,True),c,'lm')
    return y+h+6

def hd_subhead(d, y, st, pname, r):
    h=46; c=st['color']
    d.rectangle([Lx-16,y,Rx+16,y+h], fill=st['tint'])
    d.rectangle([Lx-16,y,Lx-11,y+h], fill=c)
    x=Lx
    cT(d,(x,y+h/2),dm.disp(pname),F(20,True),c,'lm'); x+=len(dm.disp(pname))*20+18
    arrow='▲' if r['day_ret']>=0 else '▼'
    cT(d,(x,y+h/2),f"{arrow} {dm.pct(r['day_ret'])}",F(19,True),clr(r['day_ret']),'lm'); x+=170
    cT(d,(x,y+h/2),"／ 累计",F(18),(150,160,175),'lm'); x+=95
    cT(d,(x,y+h/2),dm.pct(r['cum']),F(19,True),clr(r['cum']),'lm')
    return y+h

def hd_header(d, y):
    h=48
    d.rectangle([Lx-16,y,Rx+16,y+h], fill=HEADBG)
    g=F(17); c=(90,100,114)
    cT(d,(HD['name'],y+h/2),"基金名称",g,c,'lm')
    for k,lab in [('w','初始配比'),('day','今日涨跌'),('cd','今日贡献'),('cum','累计涨跌'),('cc','累计贡献')]:
        cT(d,(HD[k],y+h/2),lab,g,c,'mm')
    return y+h

def hd_row(d, y, h_):
    h=50
    cT(d,(HD['name'],y+h/2),h_['name'],F(20),INK,'lm')
    cT(d,(HD['w'],y+h/2),dm.wfmt(h_['w']),F(18),GREY,'mm')
    cT(d,(HD['day'],y+h/2),dm.pct(h_['day']),F(19,True),clr(h_['day']),'mm')
    cT(d,(HD['cd'],y+h/2),dm.pct(h_['cd']),F(18),clr(h_['cd']),'mm')
    cT(d,(HD['cum'],y+h/2),dm.pct(h_['cum']),F(19,True),clr(h_['cum']),'mm')
    cT(d,(HD['cc'],y+h/2),dm.pct(h_['cc']),F(18),clr(h_['cc']),'mm')
    d.line([Lx-16,y+h,Rx+16,y+h],fill=LINE,width=1)
    return y+h

def canvas():
    img=Image.new('RGB',(W,4200),WHITE); return img, ImageDraw.Draw(img)

def finish(img, y, path):
    out=img.crop((0,0,W,y+20))
    # 外边框
    dd=ImageDraw.Draw(out); dd.rectangle([0,0,W-1,y+19],outline=CARDBORDER,width=1)
    out.save(path)
    return path

def gen_overview(res, asof, outdir):
    img,d=canvas(); y=0
    y=header_bar(d,y,"样板间组合业绩概览",asof,SLATE,(195,204,216))
    y=disclaimer(d,y); y=ov_header(d,y)
    for key in ORDER:
        st=STRAT[key]; members=[m for m in st['members'] if m in res]
        if not members: continue
        y=group_head(d,y,st,key)
        for m in members: y=ov_row(d,y,m,res[m])
    p=os.path.join(outdir,"样板间组合业绩概览.png")
    return finish(img,y,p)

def gen_strategy(key, res, asof, outdir):
    st=STRAT[key]; members=[m for m in st['members'] if m in res]
    if not members: return None
    img,d=canvas(); y=0
    y=header_bar(d,y,f"{key} 策略",asof,st['color'],(238,242,247))
    y=disclaimer(d,y)
    y=sec_title(d,y,st,"一、组合总览")
    y=ov_header(d,y)
    for m in members: y=ov_row(d,y,m,res[m])
    y+=6
    y=sec_title(d,y,st,"二、持仓基金表现")
    for m in members:
        y=hd_subhead(d,y,st,m,res[m])
        y=hd_header(d,y)
        for h_ in res[m]['holdings']: y=hd_row(d,y,h_)
        y+=10
    fname=f"{key.replace('/','-')}策略.png"
    return finish(img,y,os.path.join(outdir,fname))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',required=True); ap.add_argument('--nav',required=True)
    ap.add_argument('--asof',default=None); ap.add_argument('--outdir',default='reports')
    a=ap.parse_args()
    os.makedirs(a.outdir,exist_ok=True)
    ports,funds=dm.load_config(a.config); nav=dm.load_nav(a.nav)
    res,asof=dm.compute(ports,nav,funds,a.asof)
    outs=[gen_overview(res,asof,a.outdir)]
    for k in ORDER: outs.append(gen_strategy(k,res,asof,a.outdir))
    for o in outs:
        if o: print('PNG ->',o)

if __name__=='__main__':
    main()
