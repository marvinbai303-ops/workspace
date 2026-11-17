import unittest
from indicators import breadth, aggregate_stocks, mcclellan, equity_bond_spread, prior_window_stats, vw_macd


class FormulaChecks(unittest.TestCase):
    def test_video54_snapshot(self):
        # 画面量额份额只有两位小数；由已公开份额反算，不假造实际成交总额。
        r = breadth(4381, 1035, 159, 83.31, 16.69, 80.15, 19.85)
        self.assertAlmostEqual(r['advance_share_pct'], 80.8899556869)
        self.assertEqual(round(r['trin_amount'], 3), .848)
        self.assertEqual(round(r['trin_volume'], 3), 1.048)
        self.assertEqual(round(r['amount_gap_pp'], 2), 2.42)
        self.assertEqual(round(r['volume_gap_pp'], 2), -.74)

    def test_trin_algebra_and_scale_invariance(self):
        for a, d, ep, em in [(20,80,60,40),(80,20,60,40),(5,95,15,85)]:
            r = breadth(a,d,0,ep,em)
            p = a/(a+d)
            q = p/(p+r['trin_amount']*(1-p))
            self.assertAlmostEqual(q, ep/(ep+em))
            self.assertEqual(r['trin_amount'] < 1, r['amount_gap_pp'] > 0)
            self.assertEqual(r['trin_amount'], breadth(a,d,0,ep*1e8,em*1e8)['trin_amount'])

    def test_degenerate_groups(self):
        self.assertIsNone(breadth(0,3,0,0,100)['trin_amount'])
        self.assertIsNone(breadth(0,0,3,0,0)['amount_gap_pp'])

    def test_missing_and_duplicate_stock_rejected(self):
        rows = [dict(date='2026-11-13',code='X',return_pct=1,amount_yuan=100)]
        with self.assertRaises(ValueError): aggregate_stocks(rows,['X','Y'])
        with self.assertRaises(ValueError): aggregate_stocks(rows*2,['X'])

    def test_flat_stock_not_in_gap_denominator(self):
        rows = [dict(date='2026-11-13',code=c,return_pct=r,amount_yuan=e)
                for c,r,e in [('X',1,60),('Y',-1,40),('Z',0,900)]]
        r=aggregate_stocks(rows,['X','Y','Z'])[0]
        self.assertEqual(r['advance_share_pct'],50)
        self.assertEqual(r['up_amount_share_pct'],60)
        self.assertEqual(r['U'],1)

    def test_mcl_impulse_and_constant(self):
        # 常数净上涨序列的两条 EMA 相等；单次冲击的首步差应为 (0.1-0.05)*100=5。
        rows = [dict(date=f'2026-01-{d:02}',A=100,D=100) for d in range(1,4)]
        self.assertTrue(all(r['mcl']==0 for r in mcclellan(rows)))
        rows[-1]['A']=200
        self.assertAlmostEqual(mcclellan(rows)[-1]['mcl'],5)
        self.assertFalse(mcclellan(rows)[-1]['warmed'])

    def test_pe_and_unit(self):
        self.assertEqual(equity_bond_spread(20,2)['spread_pp'],3)
        self.assertFalse(equity_bond_spread(-10,2)['valid'])

    def test_band_no_future_or_current_leakage(self):
        r=prior_window_stats([1,2,3,100],3,2)[-1]
        self.assertEqual(r['mean'],2)
        self.assertEqual(r['std'],1)
        self.assertEqual(r['percentile'],100)

    def test_vw_price_constant(self):
        out=vw_macd([10]*40,list(range(1,41)))
        self.assertTrue(all(r is None or r['histogram']==0 for r in out))


if __name__ == '__main__': unittest.main()
