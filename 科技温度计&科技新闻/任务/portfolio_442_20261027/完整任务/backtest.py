from pathlib import Path
import pandas as pd
import numpy as np
import json

P = Path(__file__).parent
def series(*files):
    x = pd.concat([pd.read_csv(P/f, parse_dates=['date']) for f in files])
    assert not x.date.duplicated().any()
    return x.sort_values('date').set_index('date').close
s1000 = series('csi1000_prelaunch.csv','csi1000_daily.csv')
s300 = series('csi300_early.csv','csi300_daily.csv')
prices = pd.concat([s1000.rename('csi1000'),s300.rename('csi300')],axis=1)
assert prices.notna().all().all()
assert all(prices.index.dayofweek < 5)
assert (prices > 0).all().all()
prices.to_csv(P/'daily_prices.csv',float_format='%.2f')
dates = prices.index
v = prices.values
rows=[]
for i,start in enumerate(dates):
    nominal_end = start + pd.DateOffset(months=36)
    if nominal_end > dates[-1]: break
    obs=dates.searchsorted(pd.DatetimeIndex([start+pd.DateOffset(months=m) for m in range(1,37)]))
    rel=v[obs,0]/v[i,0]
    paid=0; ko=False; holding=36
    for m,r in enumerate(rel,1):
        if r>=.75: paid+=1
        barrier=.62 if m==36 else 1.01-.003*(m-3)
        if m>=3 and r>=barrier:
            ko=True; holding=m; break
    finish=obs[holding-1]
    principal=1. if ko else rel[-1]
    h=principal-1+.0069*paid
    end=obs[-1]
    e300=v[end,1]/v[i,1]-1
    e1000=v[end,0]/v[i,0]-1
    fee=.017+.0004*(dates[finish]-start).days/365.25
    d={'start':str(start.date()),'end':str(dates[end].date()),'h_end':str(dates[finish].date()),'months':holding,'paid_months':paid,'ko':ko,'h_principal':principal,'h_return_gross':h,'h_fee_approx':fee,'h_return_fee_stress':h-fee,'csi1000_3yr':e1000,'csi300_3yr':e300,'initial1000':v[i,0],'terminal1000':v[end,0],'initial300':v[i,1],'terminal300':v[end,1]}
    for equity,e in [('300',e300),('1000',e1000)]:
        for label,b in [('b0',0),('b4',1.04**3-1),('bminus10',-.1),('bminus20',-.2)]:
            d[f'portfolio_{equity}_{label}_gross']=.4*h+.4*b+.2*e
            d[f'portfolio_{equity}_{label}_fee_stress']=.4*(h-fee)+.4*b+.2*e
    rows.append(d)
out=pd.DataFrame(rows)
out.to_csv(P/'rolling_3yr_results.csv',index=False)
summary={'source':'Eastmoney 妙想 FinQuery; iFinD priority query was truncated, spot checks separately','data_start':str(dates[0].date()),'data_end':str(dates[-1].date()),'n_daily_prices':len(prices),'completed_3yr_windows':len(out),'last_start':out.start.iloc[-1],'method':'Daily starts; monthly anniversary observed on next trading date; coupon 0.69% if >=75%; KO months3-35 101%-0.3pp*(m-3), month36 62%; cash distributions held without reinvestment; after KO proceeds held in zero-interest cash to the original 36-month horizon. Stocks price indices, no dividends; no rebalancing. Bond returns are scenarios, not fund history. Main model is gross hypothetical payoff, not fund NAV. Approx fee stress deducts 1.7% once plus .04%*holding years from original notional; it is not exact actual NAV accounting.'}
for label,df in [('all',out),('post_launch',out[out.start>='2014-10-17']),('since_2020',out[out.start>='2020-01-01'])]:
    x={'n':len(df),'principal_loss_windows':int((~df.ko).sum())}
    for eq in ['300','1000']:
        col=f'portfolio_{eq}_b0_gross'
        w=df.loc[df[col].idxmin()].to_dict()
        x['worst_'+eq]=w
    summary[label]=x

# Historical linear-equity stress proxy. It deliberately does NOT value an OTC note.
# Every eligible initial purchase date, min wealth and peak-to-trough drawdown within 3 years.
linear=[]
for i,start in enumerate(dates):
    end=dates.searchsorted(start+pd.DateOffset(months=36),side='right')
    sl=v[i:end]/v[i]
    for eq,j in [('300',1),('1000',0)]:
        wealth=.4+.4*sl[:,0]+.2*sl[:,j]
        k=int(np.argmin(wealth)); peak=np.maximum.accumulate(wealth); dd=wealth/peak-1
        kd=int(np.argmin(dd)); kp=int(np.argmax(wealth[:kd+1]))
        linear.append({'start':str(start.date()),'equity':eq,'min_total_return':wealth[k]-1,'min_date':str(dates[i+k].date()),'csi1000_return_at_low':sl[k,0]-1,'equity_return_at_low':sl[k,j]-1,'max_drawdown':float(dd[kd]),'peak_date':str(dates[i+kp].date()),'trough_date':str(dates[i+kd].date())})
lin=pd.DataFrame(linear)
lin.to_csv(P/'linear_equity_stress_NOT_note_NAV.csv',index=False)
for eq in ['300','1000']:
    x=lin[lin.equity==eq]
    summary['linear_proxy_'+eq]={'worst_loss':x.loc[x.min_total_return.idxmin()].to_dict(),'worst_drawdown':x.loc[x.max_drawdown.idxmin()].to_dict()}

# Auditable monthly observation ledger for each distinct worst terminal window.
for start in set(summary[s]['worst_'+e]['start'] for s in ['all','post_launch','since_2020'] for e in ['300','1000']):
    t=pd.Timestamp(start); i=dates.get_loc(t); ledger=[]
    for m in range(1,37):
        k=dates.searchsorted(t+pd.DateOffset(months=m)); r=v[k,0]/v[i,0]
        barrier=(.62 if m==36 else 1.01-.003*(m-3)) if m>=3 else None
        ledger.append({'month':m,'date':str(dates[k].date()),'csi1000':v[k,0],'ratio':r,'coupon_paid':r>=.75,'ko_barrier':barrier,'ko':m>=3 and r>=barrier})
    pd.DataFrame(ledger).to_csv(P/f'observations_{start}.csv',index=False)

(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
