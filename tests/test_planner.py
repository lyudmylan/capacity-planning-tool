from __future__ import annotations

import json
import unittest
from pathlib import Path

from capacity_planning_tool.config import load_defaults
from capacity_planning_tool.models import PlanningInput
from capacity_planning_tool.planner import plan_capacity

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_input(name: str) -> PlanningInput:
    with (PROJECT_ROOT / "examples" / name).open("r", encoding="utf-8") as input_file:
        raw_input = json.load(input_file)
    return PlanningInput.from_dict(raw_input, load_defaults())


class PlannerTests(unittest.TestCase):
    def test_feasible_plan_keeps_all_features_delivered(self) -> None:
        result = plan_capacity(_load_input("feasible_plan.json"), load_defaults())

        self.assertTrue(result["feasibility"])
        self.assertEqual(len(result["delivered_features"]), 3)
        self.assertEqual(result["deferred_features"], [])
        self.assertEqual(result["dropped_features"], [])
        self.assertGreater(result["buffer_dev_days"], 0)

    def test_infeasible_plan_recommends_lowest_priority_largest_first(self) -> None:
        result = plan_capacity(_load_input("infeasible_plan.json"), load_defaults())

        self.assertFalse(result["feasibility"])
        self.assertEqual(
            [feature["name"] for feature in result["dropped_features"]],
            ["Theme Refresh"],
        )
        self.assertEqual(
            [feature["name"] for feature in result["deferred_features"]],
            ["Audit Trail"],
        )
        self.assertEqual(
            [feature["name"] for feature in result["delivered_features"]],
            ["New Billing Engine", "Reporting API"],
        )

    def test_defaults_are_applied_when_optional_fields_are_missing(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_horizon": "sprint",
                "working_days": 10,
                "holidays_days": 0,
                "vacation_days": 0,
                "sick_days": 0,
                "team_structure": {
                    "teams": [
                        {
                            "name": "API",
                            "roles": [
                                {
                                    "role": "Backend Engineer",
                                    "seniority": "Senior",
                                    "count": 1
                                }
                            ]
                        }
                    ]
                },
                "roadmap": {
                    "features": [
                        {
                            "name": "Quick Win",
                            "size": "S",
                            "priority": "High"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        result = plan_capacity(planning_input, load_defaults())
        self.assertEqual(result["capacity_dev_days"], 8.0)
        self.assertEqual(result["demand_dev_days"], 8.0)

    def test_invalid_unavailable_days_raise_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_horizon": "month",
                    "working_days": 5,
                    "holidays_days": 2,
                    "vacation_days": 2,
                    "sick_days": 2,
                    "team_structure": {
                        "teams": [
                            {
                                "name": "API",
                                "roles": [
                                    {
                                        "role": "Backend Engineer",
                                        "seniority": "Senior",
                                        "count": 1
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )
