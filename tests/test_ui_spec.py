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
        self.assertEqual(spec["spec_version"], "2.1")
        self.assertEqual(spec["delivery_model"]["preferred_ui_builder"], "Claude Code")
        self.assertEqual(spec["source_of_truth"]["product_doc"], "docs/product.md")
        self.assertEqual(
            spec["source_of_truth"]["planner_contract_tests"], "tests/test_server.py"
        )
        self.assertIn("human_web_interface", spec["delivery_model"]["interaction_modes"])
        self.assertEqual(
            spec["delivery_model"]["supported_planning_modes"],
            ["capacity_check", "planning_schedule"],
        )
        self.assertEqual(spec["delivery_model"]["target_scope"], "next_ui_iteration")
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
        self.assertIn("information_architecture", spec)
        self.assertIn("mode_flows", spec)
        self.assertIn("validation_behavior", spec)
        self.assertIn("ui_state_model", spec)
        self.assertIn("field_presentation", spec)
        self.assertIn("claude_implementation_guidance", spec)
        self.assertIn("output_contract", spec)
        self.assertIn("design_preferences", spec)
        self.assertIn(
            "examples/v2_rd_org_capacity_check.json",
            spec["source_of_truth"]["planner_input_examples"],
        )
        self.assertIn(
            "examples/v2_function_estimates_capacity_check.json",
            spec["source_of_truth"]["planner_input_examples"],
        )
        self.assertEqual(
            spec["information_architecture"]["workspace_model"],
            "single_page_dual_workspace",
        )
        self.assertEqual(
            spec["information_architecture"]["regions"][1]["sections"],
            [
                "summary",
                "function_analysis",
                "scope_decision",
                "goal_and_dependency_review",
                "raw_output_json",
            ],
        )
        self.assertEqual(
            spec["mode_flows"][0]["comparison_model"], "baseline_vs_selected"
        )
        self.assertEqual(
            spec["mode_flows"][1]["comparison_model"], "selected_plan_primary"
        )
        self.assertIn(
            "normalize_period_selectors_on_horizon_change",
            spec["ui_surfaces"][0]["panels"][0]["capabilities"],
        )
        self.assertIn(
            "highlight_bottleneck_functions",
            spec["ui_surfaces"][0]["panels"][2]["capabilities"],
        )
        self.assertIn(
            "show_selected_plan_primary_for_planning_schedule",
            spec["ui_surfaces"][0]["panels"][3]["capabilities"],
        )
        self.assertEqual(
            spec["input_contract"]["v2_required_top_level_fields"],
            ["planning_mode", "rd_org", "roadmap"],
        )
        self.assertEqual(
            spec["input_contract"]["structured_editor_sections"][0]["primary_fields"],
            [
                "planning_mode",
                "planning_horizon",
                "calendar_year",
                "half_year_index",
                "quarter_index",
                "month_index",
                "start_date",
                "end_date",
            ],
        )
        self.assertIn(
            "run_disabled_when_input_is_invalid",
            spec["validation_behavior"]["interaction_rules"],
        )
        self.assertEqual(
            spec["ui_state_model"]["states"],
            [
                "pristine",
                "draft_loaded",
                "draft_dirty",
                "input_invalid",
                "ready_to_run",
                "running",
                "result_ready",
                "run_error",
            ],
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
        self.assertIn(
            "selected_plan.function_capacity_fit",
            spec["field_presentation"]["primary_output_fields"],
        )
        self.assertIn(
            "selected_plan.utilization_by_function",
            spec["field_presentation"]["secondary_output_fields"],
        )
        self.assertEqual(
            spec["claude_implementation_guidance"]["implementation_order"][0],
            "establish stable input workspace and editor synchronization",
        )
