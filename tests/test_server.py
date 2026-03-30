"""Tests for the Flask web server API."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from capacity_planning_tool.server import DEFAULT_SERVER_PORT, build_parser, create_app


class ServerApiTests(unittest.TestCase):
    """Tests for /api/plan and /api/examples endpoints."""

    CAPACITY_CHECK_OUTPUT_KEYS = {
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
    }

    EVALUATED_PLAN_OUTPUT_KEYS = {
        "capacity_dev_days",
        "demand_dev_days",
        "utilization",
        "capacity_by_function",
        "demand_by_function",
        "utilization_by_function",
        "buffer_by_function",
        "planning_mode",
        "function_capacity_fit",
        "bottleneck_functions",
        "feasibility",
        "buffer_dev_days",
        "acceptable",
        "goal_compliant",
        "delivered_features",
        "deferred_features",
        "dropped_features",
        "business_goal_assessment",
    }

    PLANNING_SCHEDULE_OUTPUT_KEYS = {
        "capacity_dev_days",
        "demand_dev_days",
        "utilization",
        "capacity_by_function",
        "demand_by_function",
        "utilization_by_function",
        "buffer_by_function",
        "planning_mode",
        "function_capacity_fit",
        "bottleneck_functions",
        "feasibility",
        "buffer_dev_days",
        "delivered_features",
        "deferred_features",
        "dropped_features",
        "selected_plan",
        "business_goal_assessment",
        "evaluated_alternatives",
        "agentic_iterations",
        "risks",
        "suggestions",
        "tradeoff_summary",
        "dependency_rules_pass",
        "dependency_violations",
    }

    PLANNING_SCHEDULE_PLAN_OUTPUT_KEYS = EVALUATED_PLAN_OUTPUT_KEYS | {
        "dependency_rules_pass",
        "dependency_violations",
    }

    def setUp(self) -> None:
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _load_example(self, name: str) -> dict:
        examples_dir = Path(__file__).resolve().parents[1] / "examples"
        with (examples_dir / name).open("r", encoding="utf-8") as f:
            return json.load(f)

    def _assert_capacity_check_contract(self, result: dict) -> None:
        self.assertEqual(result["planning_mode"], "capacity_check")
        self.assertEqual(set(result), self.CAPACITY_CHECK_OUTPUT_KEYS)
        self.assertEqual(set(result["baseline_plan"]), self.EVALUATED_PLAN_OUTPUT_KEYS)
        self.assertEqual(set(result["selected_plan"]), self.EVALUATED_PLAN_OUTPUT_KEYS)
        self.assertEqual(result["baseline_plan"]["planning_mode"], "capacity_check")
        self.assertEqual(result["selected_plan"]["planning_mode"], "capacity_check")

    def _assert_planning_schedule_contract(self, result: dict) -> None:
        self.assertEqual(set(result), self.PLANNING_SCHEDULE_OUTPUT_KEYS)
        self.assertEqual(result["planning_mode"], "planning_schedule")
        self.assertEqual(
            set(result["selected_plan"]), self.PLANNING_SCHEDULE_PLAN_OUTPUT_KEYS
        )
        self.assertEqual(result["selected_plan"]["planning_mode"], "planning_schedule")

    def test_index_returns_html(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Capacity Planner", resp.data)
        resp.close()

    def test_ui_asset_is_served(self) -> None:
        resp = self.client.get("/assets/app.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"getUtilizationStatus", resp.data)
        resp.close()

    def test_server_parser_defaults_to_port_8000(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.port, DEFAULT_SERVER_PORT)
        self.assertEqual(args.port, 8000)

    def test_plan_feasible_input(self) -> None:
        data = self._load_example("feasible_plan.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_capacity_check_contract(result)
        self.assertTrue(result["baseline_plan"]["feasibility"])
        self.assertTrue(result["selected_plan"]["feasibility"])

    def test_plan_infeasible_input(self) -> None:
        data = self._load_example("infeasible_plan.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_capacity_check_contract(result)
        self.assertFalse(result["baseline_plan"]["feasibility"])
        self.assertTrue(result["selected_plan"]["goal_compliant"])

    def test_plan_goal_driven_input(self) -> None:
        data = self._load_example("goal_driven_plan.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_capacity_check_contract(result)
        self.assertIn("business_goal_assessment", result["selected_plan"])

    def test_plan_v2_capacity_check_input(self) -> None:
        data = self._load_example("v2_rd_org_capacity_check.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_capacity_check_contract(result)
        self.assertEqual(
            result["baseline_plan"]["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertEqual(result["baseline_plan"]["bottleneck_functions"], [])
        self.assertEqual(
            result["selected_plan"]["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertEqual(result["selected_plan"]["bottleneck_functions"], [])

    def test_plan_v2_capacity_check_example_with_function_estimates(self) -> None:
        data = self._load_example("v2_function_estimates_capacity_check.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_capacity_check_contract(result)
        self.assertEqual(
            set(result["baseline_plan"]["function_capacity_fit"]),
            {"eng", "qa", "devops"},
        )

    def test_plan_planning_schedule_returns_schedule_feasibility_payload(self) -> None:
        data = self._load_example("v2_rd_org_planning_schedule.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_planning_schedule_contract(result)
        self.assertEqual(result["planning_mode"], "planning_schedule")
        self.assertIn("function_capacity_fit", result)
        self.assertIn("capacity_by_function", result)
        self.assertIn("demand_by_function", result)
        self.assertIn("utilization_by_function", result)
        self.assertIn("buffer_by_function", result)
        self.assertIn("bottleneck_functions", result)
        self.assertIn("dependency_rules_pass", result)
        self.assertIn("dependency_violations", result)
        self.assertIn("selected_plan", result)

    def test_plan_planning_schedule_dependency_only_example(self) -> None:
        data = self._load_example("v2_rd_org_planning_schedule_dependency_only.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self._assert_planning_schedule_contract(result)
        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertFalse(result["dependency_rules_pass"])
        self.assertIn("qa dependency rule failed", result["dependency_violations"][0])

    def test_plan_invalid_json_body(self) -> None:
        resp = self.client.post(
            "/api/plan",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertIn("error", result)

    def test_plan_missing_required_fields(self) -> None:
        resp = self.client.post(
            "/api/plan",
            data=json.dumps({"planning_horizon": "quarter"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 422)
        result = resp.get_json()
        self.assertIn("error", result)

    def test_examples_endpoint(self) -> None:
        resp = self.client.get("/api/examples")
        self.assertEqual(resp.status_code, 200)
        examples = resp.get_json()
        self.assertIsInstance(examples, list)
        self.assertGreater(len(examples), 0)
        for ex in examples:
            self.assertIn("name", ex)
            self.assertIn("data", ex)
            self.assertIsInstance(ex["data"], dict)

    def test_examples_endpoint_includes_v2_output_contract_examples(self) -> None:
        resp = self.client.get("/api/examples")
        self.assertEqual(resp.status_code, 200)
        examples = resp.get_json()
        example_names = {example["name"] for example in examples}

        self.assertIn("v2_function_estimates_capacity_check", example_names)
        self.assertIn("v2_rd_org_planning_schedule_dependency_only", example_names)

    def test_plan_output_matches_cli_output_schema(self) -> None:
        """Ensure the API returns the same fields the CLI produces."""
        data = self._load_example("feasible_plan.json")
        resp = self.client.post(
            "/api/plan",
            data=json.dumps(data),
            content_type="application/json",
        )
        result = resp.get_json()
        self._assert_capacity_check_contract(result)


if __name__ == "__main__":
    unittest.main()
