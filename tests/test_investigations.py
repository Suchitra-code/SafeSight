import unittest
from app.db import execute_query
from app.agents import runner, risk


class TestInvestigations(unittest.TestCase):
    def test_risk_computation(self):
        # Base Low
        score, level = risk.compute_risk("helmet", "LOW", similar_count_7d=0)
        self.assertEqual(level, "LOW")
        self.assertEqual(score, 1)

        # High with similars & open finding
        score, level = risk.compute_risk("helmet", "HIGH", similar_count_7d=4, has_open_finding=True, mandatory_rule=True)
        self.assertEqual(level, "CRITICAL")
        self.assertGreaterEqual(score, 6)

    def test_investigation_run_lifecycle(self):
        # Get an existing violation id
        rows = execute_query("SELECT id FROM violations LIMIT 1", fetch=True)
        if not rows:
            self.skipTest("No violations in database")
        v_id = rows[0]["id"]

        # 1. Start investigation
        res = runner.start_investigation_run(v_id)
        self.assertIn("run_id", res)
        run_id = res["run_id"]

        # 2. Check status (should be waiting_approval at human review interrupt)
        status_data = runner.get_run_status(run_id)
        self.assertIsNotNone(status_data)
        self.assertEqual(status_data["run_id"], run_id)
        self.assertIn(status_data["status"], ["waiting_approval", "completed", "running"])

        # 3. Resume with supervisor approval
        resume_res = runner.resume_investigation_run(run_id, decision="approved", notes="Test signoff")
        self.assertEqual(resume_res["status"], "completed")

        # 4. Check status again
        updated_status = runner.get_run_status(run_id)
        self.assertEqual(updated_status["status"], "completed")
        self.assertEqual(updated_status["approval_status"], "approved")


if __name__ == "__main__":
    unittest.main()
