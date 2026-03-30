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
        self.assertEqual(spec["spec_version"], "2.0")
        self.assertEqual(spec["delivery_model"]["preferred_ui_builder"], "Claude Code")
        self.assertEqual(spec["source_of_truth"]["product_doc"], "docs/product.md")
        self.assertIn("human_web_interface", spec["delivery_model"]["interaction_modes"])
        self.assertEqual(
            spec["delivery_model"]["supported_planning_modes"],
            ["capacity_check", "planning_schedule"],
        )
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
        self.assertIn(
            "examples/v2_rd_org_capacity_check.json",
            spec["source_of_truth"]["planner_input_examples"],
        )
        self.assertIn(
            "normalize_period_selectors_on_horizon_change",
            spec["ui_surfaces"][0]["panels"][0]["capabilities"],
        )
        self.assertIn(
            "show_plan_comparison_for_capacity_check",
            spec["ui_surfaces"][0]["panels"][2]["capabilities"],
        )
        self.assertEqual(
            spec["input_contract"]["v2_required_top_level_fields"],
            ["planning_mode", "rd_org", "roadmap"],
        )
        self.assertEqual(
            spec["output_contract"]["capacity_check_top_level_fields"],
            [
                "planning_mode",
                "capacity_dev_days",
                "capacity_by_function",
                "baseline_plan",
                "selected_plan",
                "evaluated_alternatives",
                "agentic_iterations",
                "risks",
                "suggestions",
                "tradeoff_summary",
            ],
        )
        self.assertEqual(
            spec["output_contract"]["evaluated_plan_schedule_only_fields"],
            ["dependency_rules_pass", "dependency_violations"],
        )
