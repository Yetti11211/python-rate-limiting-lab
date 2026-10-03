import unittest
from model import Config, QueueLab, CASES, run_case


class ModelTests(unittest.TestCase):
    def test_arrivals(self):
        self.assertEqual(run_case(CASES[1])[-1]['generated'], 900)

    def test_normal_response(self):
        result = run_case(CASES[0])[-1]
        self.assertEqual(result['p95_ms'], 200)
        self.assertEqual(result['queued'], 0)

    def test_overload_backlog(self):
        self.assertGreater(run_case(CASES[1])[-1]['queued'], 290)

    def test_bounded_queue(self):
        trace = run_case(CASES[2])
        self.assertLessEqual(max(r['queued'] for r in trace), 10)
        self.assertGreater(trace[-1]['rejected'], 250)

    def test_limiter_keeps_queue_empty(self):
        trace = run_case(CASES[3])
        self.assertEqual(max(r['queued'] for r in trace), 0)
        self.assertGreater(trace[-1]['rejected'], 0)

    def test_deadline(self):
        cfg = Config('DEADLINE', workers=1, service_ticks=100, deadline_ticks=10)
        self.assertGreater(run_case(cfg, 2)[-1]['expired'], 0)

    def test_conservation_all_steps(self):
        for cfg in CASES:
            lab = QueueLab(cfg)
            for _ in range(3000):
                lab.step()
                lab.assert_accounting()

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            Config('BAD', workers=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
