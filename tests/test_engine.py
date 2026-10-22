import unittest
from airops.engine import Flight, TURN, schedule, simulate, recover


class RecoveryTests(unittest.TestCase):
    def test_unperturbed_schedule(self):
        rows = simulate(schedule(), "AO001", 0)
        self.assertEqual(len(rows), 40)
        self.assertEqual(sum(r["delay"] for r in rows), 0)

    def test_delay_propagation_consumes_turnaround_slack(self):
        rows = simulate(schedule(), "AO001", 90)
        self.assertEqual([r["delay"] for r in rows if r["tail"] == "SIM-01"],
                         [90, 75, 60, 45])

    def test_recovery_improves_default_scenario(self):
        result = recover(schedule(), "AO001", 90)
        self.assertGreater(result["metrics"]["saved_minutes"], 0)
        self.assertIsNotNone(result["decision"])
        self.assertEqual({r["id"] for r in result["baseline"]},
                         {r["id"] for r in result["recovered"]})

    def test_recovery_preserves_physical_constraints_across_scenarios(self):
        for flight in ["AO001", "AO014", "AO039"]:
            for delay in [0, 45, 120, 240]:
                result = recover(schedule(), flight, delay)
                self.assertLessEqual(result["metrics"]["recovered_delay"],
                                     result["metrics"]["baseline_delay"])
                state = {}
                for row in sorted(result["recovered"], key=lambda r: (r["departure"], r["id"])):
                    if row["tail"] in state:
                        previous = state[row["tail"]]
                        self.assertEqual(previous["destination"], row["origin"])
                        self.assertGreaterEqual(row["actual"], previous["arrival"] + TURN)
                    self.assertGreaterEqual(row["actual"], row["departure"])
                    state[row["tail"]] = row

    def test_invalid_inputs(self):
        for flight, delay in [("missing", 90), ("AO001", -1), ("AO001", 241)]:
            with self.assertRaises(ValueError):
                simulate(schedule(), flight, delay)

    def test_impossible_aircraft_route_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate([Flight("A", "T", "SAW", "ADB", 360, 75),
                      Flight("B", "T", "ESB", "SAW", 500, 75)], "A", 0)


if __name__ == "__main__":
    unittest.main()
