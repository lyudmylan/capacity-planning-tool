import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class UiSpecTests(unittest.TestCase):
    def test_ui_handoff_spec_is_valid_json_with_required_contract_keys(self) -> None:
        spec_path = PROJECT_ROOT / "specs" / "ui_handoff_v1.json"
        with spec_path.open("r", encoding="utf-8") as spec_file:
            spec = json.load(spec_file)

        self.assertEqual(spec["spec_id"], "capacity-planning-ui-handoff")
        self.assertEqual(spec["spec_version"], "1.0")
        self.assertEqual(spec["delivery_model"]["preferred_ui_builder"], "Claude Code")
        self.assertIn("human_web_interface", spec["delivery_model"]["interaction_modes"])
        self.assertEqual(
            spec["product_constraints"]["planner_calculations"],
            "deterministic_backend_only",
        )
        self.assertEqual(
            spec["product_constraints"]["frontend_calculation_policy"],
            "must_not_duplicate_planner_logic",
        )
        self.assertIn("preferred_ui_builder", spec["delivery_model"])
        self.assertIn("ui_surfaces", spec)
        self.assertIn("input_contract", spec)
        self.assertIn("output_contract", spec)
        self.assertIn("design_preferences", spec)
        self.assertEqual(
            spec["output_contract"]["required_top_level_fields"],
            [
                "capacity_dev_days",
                "demand_dev_days",
                "utilization",
                "feasibility",
                "buffer_dev_days",
                "delivered_features",
                "deferred_features",
                "dropped_features",
                "risks",
                "suggestions",
                "tradeoff_summary",
                "selected_plan",
                "business_goal_assessment",
                "evaluated_alternatives",
                "agentic_iterations",
            ],
        )
