from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hydrographs import SCENARIOS, inverse_effective_volume_years, water_ledger


class HydrographTests(unittest.TestCase):
    def test_legacy_large_boundary_condition(self):
        ledger = water_ledger("constant", 180 / 365.25, 160_000, 0, 1, 1, 0.60)
        self.assertAlmostEqual(ledger["raw_m3"] / 1e9, 2488.32, places=6)
        self.assertAlmostEqual(ledger["effective_m3"] / 1e9, 1492.992, places=6)
        self.assertAlmostEqual(ledger["loss_m3"] / 1e9, 995.328, places=6)

    def test_low_scenario_does_not_fill_source_basin(self):
        scenario = SCENARIOS["low"]
        fill = inverse_effective_volume_years(
            134.53242e9,
            scenario.process,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
            scenario.retention,
        )
        self.assertIsNone(fill)

    def test_medium_fill_time(self):
        scenario = SCENARIOS["medium"]
        fill = inverse_effective_volume_years(
            134.53242e9,
            scenario.process,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
            scenario.retention,
        )
        self.assertAlmostEqual(fill, 2.6602274326, places=8)


if __name__ == "__main__":
    unittest.main()

