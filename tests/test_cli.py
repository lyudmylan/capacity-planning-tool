from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from capacity_planning_tool.config import load_defaults

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_cli_writes_json_to_stdout(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "feasible_plan.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "capacity_planning_tool", "--input", str(input_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(completed.stderr, "")
        self.assertIn("capacity_dev_days", result)
        self.assertEqual(result["deferred_features"], [])
        self.assertIn("selected_plan", result)
        self.assertIn("business_goal_assessment", result)

    def test_cli_accepts_v2_rd_org_capacity_check_example(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "v2_rd_org_capacity_check.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "capacity_planning_tool", "--input", str(input_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(completed.stderr, "")
        self.assertIn("capacity_dev_days", result)
        self.assertIn("function_capacity_fit", result)
        self.assertIn("bottleneck_functions", result)
        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertEqual(result["bottleneck_functions"], [])

    def test_cli_accepts_v2_function_estimates_capacity_check_example(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "v2_function_estimates_capacity_check.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "capacity_planning_tool", "--input", str(input_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(completed.stderr, "")
        self.assertIn("capacity_dev_days", result)
        self.assertIn("selected_plan", result)
        self.assertIn("function_capacity_fit", result)
        self.assertEqual(set(result["function_capacity_fit"]), {"eng", "qa", "devops"})

    def test_cli_accepts_v2_rd_org_month_auto_capacity_check_example(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "v2_rd_org_month_auto_capacity_check.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "capacity_planning_tool", "--input", str(input_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(completed.stderr, "")
        self.assertIn("capacity_dev_days", result)

    def test_cli_can_write_output_file(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "infeasible_plan.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "result.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "capacity_planning_tool",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["selected_plan"]["goal_compliant"], True)
            self.assertIn("tradeoff_summary", result)
            self.assertIn("agentic_iterations", result)
            self.assertEqual(
                [feature["name"] for feature in result["dropped_features"]],
                ["Theme Refresh"],
            )

    def test_cli_can_enable_info_logging(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "feasible_plan.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "capacity_planning_tool",
                "--input",
                str(input_path),
                "--log-level",
                "INFO",
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertIn("INFO capacity_planning_tool.cli:", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIn("capacity_dev_days", result)

    def test_cli_quiet_flag_suppresses_info_logging(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "infeasible_plan.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "capacity_planning_tool",
                "--input",
                str(input_path),
                "--quiet",
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertFalse(result["feasibility"])

    def test_cli_reports_output_write_errors_cleanly(self) -> None:
        input_path = PROJECT_ROOT / "examples" / "feasible_plan.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        missing_parent = PROJECT_ROOT / "missing-output-dir" / "result.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "capacity_planning_tool",
                "--input",
                str(input_path),
                "--output",
                str(missing_parent),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Could not write output:", completed.stderr)

    def test_defaults_include_logging_and_policy_settings(self) -> None:
        defaults = load_defaults()

        self.assertEqual(defaults.log_level_default, "WARNING")
        self.assertIn("acceptable", defaults.plan_score_order)
        self.assertIn("defer_preference", defaults.candidate_sort_order)
