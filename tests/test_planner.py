from __future__ import annotations

import json
import unittest
from pathlib import Path

from capacity_planning_tool.config import load_defaults
from capacity_planning_tool.models import DefaultsConfig, PlanningInput
from capacity_planning_tool.planner import plan_capacity

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_input(name: str) -> PlanningInput:
    with (PROJECT_ROOT / "examples" / name).open("r", encoding="utf-8") as input_file:
        raw_input = json.load(input_file)
    return PlanningInput.from_dict(raw_input, load_defaults())


def _load_raw_example(name: str) -> dict:
    with (PROJECT_ROOT / "examples" / name).open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


class PlannerTests(unittest.TestCase):
    def test_feasible_plan_keeps_all_features_delivered(self) -> None:
        result = plan_capacity(_load_input("feasible_plan.json"), load_defaults())

        self.assertTrue(result["feasibility"])
        self.assertEqual(len(result["delivered_features"]), 3)
        self.assertEqual(result["deferred_features"], [])
        self.assertEqual(result["dropped_features"], [])
        self.assertGreater(result["buffer_dev_days"], 0)
        self.assertTrue(result["selected_plan"]["goal_compliant"])
        self.assertEqual(result["business_goal_assessment"]["missing_must_deliver_feature_ids"], [])

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
        self.assertTrue(result["selected_plan"]["goal_compliant"])
        self.assertEqual(len(result["agentic_iterations"]), 2)
        self.assertGreaterEqual(len(result["evaluated_alternatives"]), 2)

    def test_defaults_are_applied_when_optional_fields_are_missing(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "sprint",
                "start_date": "2026-03-02",
                "end_date": "2026-03-13",
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
        self.assertEqual(result["business_goal_assessment"]["must_deliver_feature_ids"], [])

    def test_invalid_unavailable_days_raise_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 3,
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

    def test_business_goals_protect_must_deliver_features(self) -> None:
        result = plan_capacity(_load_input("goal_driven_plan.json"), load_defaults())

        self.assertTrue(
            {"feature-1", "feature-5", "feature-7", "feature-8"}.issubset(
                {
                    feature["id"]
                    for feature in result["delivered_features"]
                    if "id" in feature
                }
            )
        )
        self.assertEqual(
            [feature["id"] for feature in result["dropped_features"]],
            ["feature-9"],
        )
        self.assertTrue(result["selected_plan"]["acceptable"])

    def test_unknown_must_deliver_feature_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 4,
                    "working_days": 20,
                    "holidays_days": 1,
                    "vacation_days": 1,
                    "sick_days": 1,
                    "team_structure": {
                        "teams": [
                            {
                                "name": "API",
                                "roles": [
                                    {
                                        "role": "Backend Engineer",
                                        "seniority": "Senior",
                                        "count": 2
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {
                        "features": [
                            {
                                "id": "real-feature",
                                "name": "Real Feature",
                                "size": "S",
                                "priority": "High"
                            }
                        ]
                    },
                    "business_goals": {
                        "must_deliver_feature_ids": ["missing-feature"]
                    }
                },
                load_defaults(),
            )

    def test_invalid_planning_mode_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "roadmap_review",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "team_structure": {
                        "teams": [
                            {
                                "name": "API",
                                "roles": [
                                    {
                                        "role": "Backend Engineer",
                                        "seniority": "Senior",
                                        "count": 2
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_quarter_requires_quarter_index(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "quarter",
                    "calendar_year": 2026,
                    "working_days": 60,
                    "holidays_days": 2,
                    "vacation_days": 5,
                    "sick_days": 1,
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

    def test_sprint_rejects_non_sprint_selectors(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "planning_schedule",
                    "planning_horizon": "sprint",
                    "calendar_year": 2026,
                    "start_date": "2026-03-03",
                    "end_date": "2026-03-14",
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
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_sprint_requires_end_date_not_before_start_date(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "planning_schedule",
                    "planning_horizon": "sprint",
                    "start_date": "2026-03-14",
                    "end_date": "2026-03-03",
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
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_parses_and_adapts_into_legacy_teams(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "month",
                "calendar_year": 2026,
                "month_index": 5,
                "working_days": 20,
                "holidays_days": 1,
                "vacation_days": 1,
                "sick_days": 1,
                "rd_org": {
                    "country_profiles": [
                        {
                            "id": "il",
                            "country_code": "IL",
                            "working_day_rules": {"workweek": "sun-thu"},
                            "holiday_calendar_rules": {"calendar": "israeli"},
                            "vacation_days_per_employee": 18,
                            "sick_days_per_employee": 8
                        }
                    ],
                    "teams": [
                        {
                            "name": "Core Product",
                            "members": [
                                {
                                    "id": "eng-1",
                                    "function": "eng",
                                    "seniority": "Senior",
                                    "country_profile": "il"
                                },
                                {
                                    "id": "eng-2",
                                    "function": "eng",
                                    "seniority": "Senior",
                                    "capacity_percent": 0.5,
                                    "country_profile": "il"
                                },
                                {
                                    "id": "qa-1",
                                    "function": "qa",
                                    "seniority": "Mid",
                                    "country_profile": "il"
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

        self.assertIsNotNone(planning_input.rd_org)
        self.assertEqual(len(planning_input.rd_org.teams), 1)
        self.assertEqual(len(planning_input.teams), 1)
        self.assertEqual(planning_input.teams[0].name, "Core Product")
        team_roles = {
            (role.role, role.seniority, len(role.members))
            for role in planning_input.teams[0].roles
        }
        self.assertEqual(
            team_roles,
            {("eng", "Senior", 2), ("qa", "Mid", 1)},
        )
        self.assertEqual(planning_input.teams[0].roles[0].members[0].capacity_percent, 1.0)

        result = plan_capacity(planning_input, load_defaults())
        self.assertIn("capacity_dev_days", result)
        self.assertTrue(result["feasibility"])

    def test_rd_org_duplicate_member_ids_raise_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "shared-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            },
                            {
                                "name": "Infrastructure",
                                "members": [
                                    {
                                        "id": "shared-1",
                                        "function": "devops",
                                        "seniority": "Mid",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_rejects_unsupported_member_function(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "design-1",
                                        "function": "designer",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_and_team_structure_together_raise_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
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

    def test_rd_org_rejects_unknown_country_profile_reference(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_rejects_duplicate_country_profile_ids(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            },
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_rejects_empty_country_profiles(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_rejects_negative_country_profile_allowances(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": -1,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": -1
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_rd_org_rejects_invalid_country_profile_rule_objects(self) -> None:
        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "holiday_calendar_rules": {"calendar": "israeli"},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_v2_capacity_check_example_parses(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_capacity_check.json"),
            load_defaults(),
        )

        self.assertEqual(planning_input.planning_mode, "capacity_check")
        self.assertIsNotNone(planning_input.rd_org)
        self.assertEqual(len(planning_input.rd_org.country_profiles), 1)
        self.assertEqual(len(planning_input.teams), 1)

    def test_v2_planning_schedule_example_parses(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_planning_schedule.json"),
            load_defaults(),
        )

        self.assertEqual(planning_input.planning_mode, "planning_schedule")
        self.assertEqual(planning_input.planning_horizon, "sprint")
        self.assertIsNotNone(planning_input.start_date)
        self.assertIsNotNone(planning_input.end_date)

    def test_planner_rejects_planning_schedule_until_supported(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_planning_schedule.json"),
            load_defaults(),
        )

        with self.assertRaises(ValueError):
            plan_capacity(planning_input, load_defaults())

    def test_rd_org_qa_and_devops_do_not_increase_legacy_eng_capacity(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "month",
                "calendar_year": 2026,
                "month_index": 5,
                "working_days": 20,
                "holidays_days": 0,
                "vacation_days": 0,
                "sick_days": 0,
                "rd_org": {
                    "country_profiles": [
                        {
                            "id": "il",
                            "country_code": "IL",
                            "working_day_rules": {"workweek": "sun-thu"},
                            "holiday_calendar_rules": {"calendar": "israeli"},
                            "vacation_days_per_employee": 18,
                            "sick_days_per_employee": 8
                        }
                    ],
                    "teams": [
                        {
                            "name": "Core Product",
                            "members": [
                                {
                                    "id": "qa-1",
                                    "function": "qa",
                                    "seniority": "Mid",
                                    "country_profile": "il"
                                },
                                {
                                    "id": "ops-1",
                                    "function": "devops",
                                    "seniority": "Senior",
                                    "country_profile": "il"
                                }
                            ]
                        }
                    ]
                },
                "roadmap": {"features": []}
            },
            load_defaults(),
        )

        result = plan_capacity(planning_input, load_defaults())
        self.assertEqual(result["capacity_dev_days"], 0.0)

        with self.assertRaises(ValueError):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 2026,
                    "working_days": 220,
                    "holidays_days": 10,
                    "vacation_days": 20,
                    "sick_days": 5,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": [],
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "teams": [
                            {
                                "name": "Platform",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {"features": []}
                },
                load_defaults(),
            )

    def test_agentic_loop_emits_logging_for_selected_candidates(self) -> None:
        with self.assertLogs("capacity_planning_tool.planner", level="INFO") as captured_logs:
            plan_capacity(_load_input("infeasible_plan.json"), load_defaults())

        combined_output = "\n".join(captured_logs.output)
        self.assertIn("Starting replanning loop", combined_output)
        self.assertIn("Iteration 1 selected removal", combined_output)
        self.assertIn("Completed replanning", combined_output)

    def test_invalid_candidate_limit_in_defaults_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            DefaultsConfig.from_dict(
                {
                    "capacity_percent_default": 1.0,
                    "focus_factor_default": 0.8,
                    "sprint_days_default": 10,
                    "overhead_days_per_sprint_default": 2,
                    "feature_size_multipliers": {
                        "XS": 0.5,
                        "S": 1.0,
                        "M": 2.0,
                        "L": 3.0
                    },
                    "priority_rank": {
                        "Low": 1,
                        "Medium": 2,
                        "High": 3,
                        "Critical": 4
                    },
                    "log_level_default": "INFO",
                    "utilization_target_min": 0.8,
                    "utilization_target_max": 0.9,
                    "buffer_target_ratio": 0.1,
                    "defer_preference_default": ["Low", "Medium", "High", "Critical"],
                    "candidate_sort_order": [
                        "preserved_priority",
                        "defer_preference",
                        "demand_desc",
                        "original_index"
                    ],
                    "plan_score_order": [
                        "acceptable",
                        "goal_compliant",
                        "feasible",
                        "hard_constraint_violations",
                        "utilization_gap",
                        "buffer_gap",
                        "soft_goal_violations",
                        "delivered_priority_value",
                        "removed_feature_count"
                    ],
                    "agentic_max_iterations": 3,
                    "agentic_candidate_limit": 0,
                    "output_precision": 2
                }
            )
