from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "data"
sys.path.insert(0, str(ROOT / "src"))

from two_d_diffusive_wave import DiffusiveWave2D, quantize_depth


class OriginalModelRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = np.load(DATA_ROOT / "conservative-model.npz")

    def test_one_day_q25000_reproduces_original_grid(self):
        model = DiffusiveWave2D(
            self.data["z400"], self.data["basin"], self.data["inlet"]
        )
        model.advance_constant(25_000.0, 86_400.0)
        expected = self.data["q25_d001"]
        actual = quantize_depth(model.h)
        self.assertTrue(np.array_equal(actual, expected))
        expected_stats = self.data["s25_d001"]
        balance = model.balance()
        self.assertAlmostEqual(balance.stored_m3, expected_stats[0], delta=1.0)
        self.assertAlmostEqual(balance.boundary_outflow_m3, expected_stats[1], delta=1.0)
        self.assertLess(abs(balance.relative_error), 1e-6)

    def test_two_days_continue_same_state(self):
        model = DiffusiveWave2D(
            self.data["z400"], self.data["basin"], self.data["inlet"]
        )
        model.advance_constant(25_000.0, 2 * 86_400.0)
        self.assertTrue(
            np.array_equal(quantize_depth(model.h), self.data["q25_d002"])
        )

    def test_total_flow_is_distributed_once(self):
        model = DiffusiveWave2D(
            self.data["z400"], self.data["basin"], self.data["inlet"]
        )
        model.step(1_000.0)
        self.assertAlmostEqual(model.supplied_m3, 600_000.0, delta=0.1)
        self.assertAlmostEqual(float(model.weights.sum()), 1.0, places=6)

    def test_dynamic_crop_is_pixel_identical_after_two_days(self):
        model = DiffusiveWave2D(
            self.data["z400"],
            self.data["basin"],
            self.data["inlet"],
            dynamic_crop=True,
        )
        model.advance_constant(25_000.0, 2 * 86_400.0)
        self.assertTrue(
            np.array_equal(quantize_depth(model.h), self.data["q25_d002"])
        )
        expected_stats = self.data["s25_d002"]
        balance = model.balance()
        self.assertAlmostEqual(balance.stored_m3, expected_stats[0], delta=1.0)
        self.assertAlmostEqual(balance.boundary_outflow_m3, expected_stats[1], delta=1.0)


if __name__ == "__main__":
    unittest.main()
