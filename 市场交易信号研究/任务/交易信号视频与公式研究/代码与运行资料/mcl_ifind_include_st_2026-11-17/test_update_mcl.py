import unittest

from update_mcl import SOURCE, SCOPE, calculate, merge_rows, validate_rows


def row(date, a=100, d=80):
    return dict(date=date, A=a, D=d, U=5, source_id=SOURCE, scope_id=SCOPE)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.calendar = ["2026-11-12", "2026-11-13", "2026-11-16"]
        self.rows = [row(self.calendar[0]), row(self.calendar[1], 50, 90), row(self.calendar[2], 75, 40)]

    def test_daily_append_matches_batch_and_state_recursion(self):
        initial = merge_rows([], self.rows[:2], self.calendar)
        updated = merge_rows(initial, self.rows[2:], self.calendar)
        self.assertEqual(calculate(updated), calculate(self.rows))
        old, new = calculate(initial)[-1], calculate(updated)[-1]
        self.assertAlmostEqual(new['ema19'], .1*35+.9*old['ema19'])
        self.assertAlmostEqual(new['ema39'], .05*35+.95*old['ema39'])

    def test_same_date_retry_is_idempotent(self):
        self.assertEqual(merge_rows(self.rows, self.rows[2:], self.calendar), self.rows)

    def test_missing_trading_day_rejected(self):
        with self.assertRaisesRegex(ValueError, '缺口'):
            merge_rows([], [self.rows[0], self.rows[2]], self.calendar)

    def test_wrong_scope_rejected(self):
        other = {**self.rows[2], 'scope_id': 'SHSZ_EX_ST'}
        with self.assertRaisesRegex(ValueError, '口|股票池'):
            merge_rows(self.rows[:2], [other], self.calendar)

    def test_conflict_requires_explicit_correction(self):
        corrected = {**self.rows[1], 'A': 60}
        with self.assertRaisesRegex(ValueError, '冲突'):
            merge_rows(self.rows, [corrected], self.calendar)
        fixed = merge_rows(self.rows, [corrected], self.calendar, True)
        self.assertNotEqual(calculate(fixed)[-1]['mcl'], calculate(self.rows)[-1]['mcl'])

    def test_invalid_inputs_not_converted_to_zero(self):
        for value in ('', -1, '1.1', True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rows([{**self.rows[0], 'A': value}])
        with self.assertRaisesRegex(ValueError, '重复'):
            validate_rows(self.rows+self.rows[:1])


if __name__ == '__main__':
    unittest.main()
