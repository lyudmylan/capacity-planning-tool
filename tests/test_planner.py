from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from capacity_planning_tool.config import load_defaults
from capacity_planning_tool.models import DefaultsConfig, PlanningInput
from capacity_planning_tool.planner import (
    _capacity_by_function,
    _demand_by_function,
    _dependency_rule_evaluation,
    _feature_demands,
    plan_capacity,
)

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
        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertEqual(result["bottleneck_functions"], [])
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

    def test_calendar_year_above_python_date_range_raises_validation_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "calendar_year must be less than or equal to 9999"):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "year",
                    "calendar_year": 10000,
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
                                        "count": 1,
                                    }
                                ],
                            }
                        ]
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_planning_period_is_derived_for_each_horizon(self) -> None:
        defaults = load_defaults()
        base_payload = {
            "planning_mode": "capacity_check",
            "working_days": 20,
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
                                "count": 1,
                            }
                        ],
                    }
                ]
            },
            "roadmap": {"features": []},
        }
        scenarios = [
            (
                "year",
                {"calendar_year": 2026},
                date(2026, 1, 1),
                date(2026, 12, 31),
                365,
            ),
            (
                "half_year",
                {"calendar_year": 2026, "half_year_index": 2},
                date(2026, 7, 1),
                date(2026, 12, 31),
                184,
            ),
            (
                "quarter",
                {"calendar_year": 2026, "quarter_index": 3},
                date(2026, 7, 1),
                date(2026, 9, 30),
                92,
            ),
            (
                "month",
                {"calendar_year": 2026, "month_index": 2},
                date(2026, 2, 1),
                date(2026, 2, 28),
                28,
            ),
            (
                "sprint",
                {"start_date": "2026-03-02", "end_date": "2026-03-13"},
                date(2026, 3, 2),
                date(2026, 3, 13),
                12,
            ),
        ]

        for planning_horizon, selectors, expected_start, expected_end, expected_days in scenarios:
            with self.subTest(planning_horizon=planning_horizon):
                planning_input = PlanningInput.from_dict(
                    {
                        **base_payload,
                        "planning_horizon": planning_horizon,
                        **selectors,
                    },
                    defaults,
                )

                self.assertEqual(planning_input.planning_period.start_date, expected_start)
                self.assertEqual(planning_input.planning_period.end_date, expected_end)
                self.assertEqual(
                    planning_input.planning_period.total_calendar_days,
                    expected_days,
                )

    def test_rd_org_can_derive_working_and_holiday_days_from_country_profile(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "month",
                "calendar_year": 2026,
                "month_index": 1,
                "vacation_days": 0,
                "sick_days": 0,
                "rd_org": {
                    "country_profiles": [
                        {
                            "id": "us",
                            "country_code": "US",
                            "working_day_rules": {"workweek": "mon-fri"},
                            "holiday_calendar_rules": {
                                "dates": ["2026-01-01", "2026-01-17", "2026-01-19"]
                            },
                            "vacation_days_per_employee": 15,
                            "sick_days_per_employee": 8,
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
                                    "country_profile": "us",
                                }
                            ],
                        }
                    ],
                },
                "roadmap": {"features": []},
            },
            load_defaults(),
        )

        self.assertEqual(planning_input.working_days, 22.0)
        self.assertEqual(planning_input.holidays_days, 2.0)

    def test_rd_org_can_derive_days_for_sprint_window(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "sprint",
                "start_date": "2026-03-01",
                "end_date": "2026-03-07",
                "vacation_days": 0,
                "sick_days": 0,
                "rd_org": {
                    "country_profiles": [
                        {
                            "id": "il",
                            "country_code": "IL",
                            "working_day_rules": {"workweek": "sun-thu"},
                            "holiday_calendar_rules": {"dates": ["2026-03-03", "2026-03-06"]},
                            "vacation_days_per_employee": 18,
                            "sick_days_per_employee": 8,
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
                                    "country_profile": "il",
                                }
                            ],
                        }
                    ],
                },
                "roadmap": {"features": []},
            },
            load_defaults(),
        )

        self.assertEqual(planning_input.working_days, 5.0)
        self.assertEqual(planning_input.holidays_days, 1.0)

    def test_rd_org_derivation_rejects_unsupported_workweek(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported country_profile.working_day_rules.workweek",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 1,
                    "vacation_days": 0,
                    "sick_days": 0,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "uk",
                                "country_code": "GB",
                                "working_day_rules": {"workweek": "mon-thu"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 20,
                                "sick_days_per_employee": 6,
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
                                        "country_profile": "uk",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_rd_org_derivation_rejects_unsupported_named_holiday_calendar(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported country_profile.holiday_calendar_rules.calendar",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "quarter",
                    "calendar_year": 2026,
                    "quarter_index": 2,
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
                                "sick_days_per_employee": 8,
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
                                        "country_profile": "il",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_rd_org_derivation_rejects_mixed_country_day_counts(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "explicit working_days and holidays_days are required",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 1,
                    "vacation_days": 0,
                    "sick_days": 0,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": ["2026-01-19"]},
                                "vacation_days_per_employee": 15,
                                "sick_days_per_employee": 8,
                            },
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8,
                            },
                        ],
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us",
                                    },
                                    {
                                        "id": "eng-2",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il",
                                    },
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_rd_org_derivation_requires_working_and_holiday_days_together_when_manual(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "working_days and holidays_days must be provided together",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 1,
                    "working_days": 22,
                    "vacation_days": 0,
                    "sick_days": 0,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 15,
                                "sick_days_per_employee": 8,
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
                                        "country_profile": "us",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_rd_org_can_prorate_vacation_and_sick_days_by_horizon(self) -> None:
        defaults = load_defaults()
        base_payload = {
            "planning_mode": "capacity_check",
            "rd_org": {
                "country_profiles": [
                    {
                        "id": "us",
                        "country_code": "US",
                        "working_day_rules": {"workweek": "mon-fri"},
                        "holiday_calendar_rules": {"dates": []},
                        "vacation_days_per_employee": 24,
                        "sick_days_per_employee": 12,
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
                                "country_profile": "us",
                            }
                        ],
                    }
                ],
            },
            "roadmap": {"features": []},
        }
        scenarios = [
            ("year", {"calendar_year": 2026}, 1.0),
            ("half_year", {"calendar_year": 2026, "half_year_index": 2}, 184 / 365),
            ("quarter", {"calendar_year": 2026, "quarter_index": 2}, 91 / 365),
            ("month", {"calendar_year": 2026, "month_index": 2}, 28 / 365),
            (
                "sprint",
                {"start_date": "2026-03-01", "end_date": "2026-03-14"},
                14 / 365,
            ),
        ]

        for planning_horizon, selectors, expected_ratio in scenarios:
            with self.subTest(planning_horizon=planning_horizon):
                planning_input = PlanningInput.from_dict(
                    {
                        **base_payload,
                        "planning_horizon": planning_horizon,
                        **selectors,
                    },
                    defaults,
                )

                self.assertAlmostEqual(planning_input.vacation_days, 24 * expected_ratio)
                self.assertAlmostEqual(planning_input.sick_days, 12 * expected_ratio)

    def test_rd_org_leave_proration_rejects_mixed_country_allowances(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "explicit vacation_days and sick_days are required",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 1,
                    "working_days": 22,
                    "holidays_days": 0,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us-a",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 15,
                                "sick_days_per_employee": 8,
                            },
                            {
                                "id": "us-b",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 20,
                                "sick_days_per_employee": 10,
                            },
                        ],
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us-a",
                                    },
                                    {
                                        "id": "eng-2",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us-b",
                                    },
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_rd_org_leave_proration_requires_vacation_and_sick_days_together_when_manual(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "vacation_days and sick_days must be provided together",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 1,
                    "working_days": 22,
                    "holidays_days": 0,
                    "vacation_days": 2,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 15,
                                "sick_days_per_employee": 8,
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
                                        "country_profile": "us",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
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
        self.assertEqual(planning_input.planning_period.start_date, date(2026, 4, 1))
        self.assertEqual(planning_input.planning_period.end_date, date(2026, 6, 30))
        self.assertEqual(planning_input.working_days, 65.0)
        self.assertEqual(planning_input.holidays_days, 3.0)
        self.assertAlmostEqual(planning_input.vacation_days, 18 * (91 / 365))
        self.assertAlmostEqual(planning_input.sick_days, 8 * (91 / 365))
        self.assertEqual(planning_input.features[0].size, "M")
        self.assertIsNotNone(planning_input.features[0].estimates)
        self.assertEqual(planning_input.features[0].estimates.eng, "M")
        self.assertEqual(planning_input.features[0].estimates.qa, "S")
        self.assertEqual(planning_input.features[0].estimates.devops, "XS")

    def test_v2_planning_schedule_example_parses(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_planning_schedule.json"),
            load_defaults(),
        )

        self.assertEqual(planning_input.planning_mode, "planning_schedule")
        self.assertEqual(planning_input.planning_horizon, "sprint")
        self.assertIsNotNone(planning_input.start_date)
        self.assertIsNotNone(planning_input.end_date)
        self.assertEqual(planning_input.planning_period.start_date, date(2026, 3, 2))
        self.assertEqual(planning_input.planning_period.end_date, date(2026, 3, 13))
        self.assertEqual(planning_input.working_days, 9.0)
        self.assertEqual(planning_input.holidays_days, 1.0)
        self.assertAlmostEqual(planning_input.vacation_days, 18 * (12 / 365))
        self.assertAlmostEqual(planning_input.sick_days, 8 * (12 / 365))
        self.assertEqual(planning_input.features[0].size, "S")
        self.assertIsNotNone(planning_input.features[0].estimates)
        self.assertEqual(planning_input.features[0].estimates.eng, "S")
        self.assertEqual(planning_input.features[0].estimates.qa, "S")
        self.assertIsNone(planning_input.features[0].estimates.devops)
        self.assertIsNotNone(planning_input.rd_org)
        self.assertIsNotNone(planning_input.rd_org.org_schedule_policies)
        self.assertIsNotNone(planning_input.rd_org.org_schedule_policies.post_dev_min_ratio)
        self.assertEqual(planning_input.rd_org.org_schedule_policies.post_dev_min_ratio.qa, 0.4)
        self.assertEqual(
            planning_input.rd_org.org_schedule_policies.post_dev_min_ratio.devops,
            0.4,
        )

    def test_capacity_check_rejects_org_schedule_policies(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "rd_org.org_schedule_policies is only supported for planning_schedule",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "quarter",
                    "calendar_year": 2026,
                    "quarter_index": 2,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8,
                            }
                        ],
                        "org_schedule_policies": {
                            "post_dev_min_ratio": {"qa": 0.4}
                        },
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_capacity_check_rejects_null_org_schedule_policies(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "rd_org.org_schedule_policies is only supported for planning_schedule",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "quarter",
                    "calendar_year": 2026,
                    "quarter_index": 2,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8,
                            }
                        ],
                        "org_schedule_policies": None,
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "us",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_planning_schedule_rejects_invalid_post_dev_min_ratio_bounds(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "org_schedule_policies.post_dev_min_ratio.qa must be between 0 and 1",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "planning_schedule",
                    "planning_horizon": "sprint",
                    "start_date": "2026-03-02",
                    "end_date": "2026-03-13",
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"dates": ["2026-03-10"]},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8,
                            }
                        ],
                        "org_schedule_policies": {
                            "post_dev_min_ratio": {"qa": 1.2}
                        },
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_planning_schedule_rejects_unsupported_org_schedule_policy_keys(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "org_schedule_policies contains unsupported keys: staffing_strategy",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "planning_schedule",
                    "planning_horizon": "sprint",
                    "start_date": "2026-03-02",
                    "end_date": "2026-03-13",
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"dates": ["2026-03-10"]},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8,
                            }
                        ],
                        "org_schedule_policies": {
                            "staffing_strategy": "follow-the-sun"
                        },
                        "teams": [
                            {
                                "name": "Core Product",
                                "members": [
                                    {
                                        "id": "eng-1",
                                        "function": "eng",
                                        "seniority": "Senior",
                                        "country_profile": "il",
                                    }
                                ],
                            }
                        ],
                    },
                    "roadmap": {"features": []},
                },
                load_defaults(),
            )

    def test_dependency_rule_evaluation_passes_when_blocked_work_fits(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_planning_schedule.json"),
            load_defaults(),
        )

        evaluation = _dependency_rule_evaluation(
            planning_input,
            {"eng": 8.0, "qa": 8.0, "devops": 0.0},
            {"eng": 16.0, "qa": 16.0, "devops": 8.0},
            precision=2,
        )

        self.assertEqual(evaluation.eng_utilization, 0.5)
        self.assertEqual(
            evaluation.blocked_demand_by_function,
            {"qa": 3.2, "devops": 0.0},
        )
        self.assertEqual(
            evaluation.blocked_utilization_by_function,
            {"qa": 0.2, "devops": 0.0},
        )
        self.assertTrue(evaluation.dependency_rules_pass)
        self.assertEqual(evaluation.dependency_violations, ())

    def test_dependency_rule_evaluation_records_blocked_downstream_failures(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_planning_schedule.json"),
            load_defaults(),
        )

        evaluation = _dependency_rule_evaluation(
            planning_input,
            {"eng": 12.0, "qa": 10.0, "devops": 8.0},
            {"eng": 16.0, "qa": 8.0, "devops": 4.0},
            precision=2,
        )

        self.assertEqual(evaluation.eng_utilization, 0.75)
        self.assertEqual(
            evaluation.blocked_demand_by_function,
            {"qa": 4.0, "devops": 3.2},
        )
        self.assertEqual(
            evaluation.blocked_utilization_by_function,
            {"qa": 0.5, "devops": 0.8},
        )
        self.assertFalse(evaluation.dependency_rules_pass)
        self.assertEqual(len(evaluation.dependency_violations), 2)
        self.assertIn("qa dependency rule failed", evaluation.dependency_violations[0])
        self.assertIn("devops dependency rule failed", evaluation.dependency_violations[1])

    def test_dependency_rule_evaluation_ignores_schedule_policies_outside_planning_schedule(
        self,
    ) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_capacity_check.json"),
            load_defaults(),
        )

        evaluation = _dependency_rule_evaluation(
            planning_input,
            {"eng": 16.0, "qa": 8.0, "devops": 4.0},
            {"eng": 20.0, "qa": 20.0, "devops": 10.0},
            precision=2,
        )

        self.assertEqual(evaluation.eng_utilization, 0.0)
        self.assertEqual(
            evaluation.blocked_demand_by_function,
            {"qa": 0.0, "devops": 0.0},
        )
        self.assertEqual(
            evaluation.blocked_utilization_by_function,
            {"qa": 0.0, "devops": 0.0},
        )
        self.assertTrue(evaluation.dependency_rules_pass)
        self.assertEqual(evaluation.dependency_violations, ())

    def test_v2_function_estimates_capacity_check_example_parses(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_function_estimates_capacity_check.json"),
            load_defaults(),
        )

        self.assertEqual(planning_input.planning_mode, "capacity_check")
        self.assertEqual(planning_input.planning_horizon, "quarter")
        self.assertEqual(len(planning_input.features), 2)

        first_feature = planning_input.features[0]
        second_feature = planning_input.features[1]

        self.assertIsNotNone(first_feature.estimates)
        self.assertEqual(first_feature.estimates.eng, "L")
        self.assertEqual(first_feature.estimates.qa, "M")
        self.assertEqual(first_feature.estimates.devops, "S")

        self.assertIsNotNone(second_feature.estimates)
        self.assertEqual(second_feature.estimates.eng, "S")
        self.assertIsNone(second_feature.estimates.qa)
        self.assertIsNone(second_feature.estimates.devops)

        totals = _demand_by_function(_feature_demands(planning_input, load_defaults()), precision=2)
        self.assertEqual(totals, {"eng": 32.0, "qa": 16.0, "devops": 8.0})

    def test_feature_estimates_parse_with_legacy_eng_size(self) -> None:
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
                            "name": "Function Estimated Feature",
                            "estimates": {
                                "eng": "L",
                                "qa": "M",
                                "devops": "S"
                            },
                            "priority": "High"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        feature = planning_input.features[0]
        self.assertEqual(feature.size, "L")
        self.assertIsNotNone(feature.estimates)
        self.assertEqual(feature.estimates.eng, "L")
        self.assertEqual(feature.estimates.qa, "M")
        self.assertEqual(feature.estimates.devops, "S")

    def test_feature_demands_include_per_function_values(self) -> None:
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
                            "name": "Function Estimated Feature",
                            "estimates": {
                                "eng": "L",
                                "qa": "M",
                                "devops": "S"
                            },
                            "priority": "High"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        feature_demand = _feature_demands(planning_input, load_defaults())[0]
        self.assertEqual(feature_demand.demand_dev_days, 24.0)
        self.assertEqual(
            feature_demand.demand_by_function,
            {"eng": 24.0, "qa": 16.0, "devops": 8.0},
        )

    def test_feature_estimates_omitted_functions_are_treated_as_zero_demand(self) -> None:
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
                            "name": "Only QA Follow-up",
                            "estimates": {
                                "qa": "M"
                            },
                            "priority": "Medium"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        feature = planning_input.features[0]
        self.assertIsNone(feature.size)
        self.assertIsNotNone(feature.estimates)
        self.assertIsNone(feature.estimates.eng)
        self.assertEqual(feature.estimates.qa, "M")
        self.assertIsNone(feature.estimates.devops)

        feature_demand = _feature_demands(planning_input, load_defaults())[0]
        self.assertEqual(feature_demand.demand_dev_days, 0.0)
        self.assertEqual(
            feature_demand.demand_by_function,
            {"eng": 0.0, "qa": 16.0, "devops": 0.0},
        )

    def test_feature_estimates_reject_unsupported_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "feature.estimates contains unsupported keys"):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 5,
                    "working_days": 20,
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
                                "name": "Bad Estimate Keys",
                                "estimates": {
                                    "security": "S"
                                },
                                "priority": "Medium"
                            }
                        ]
                    }
                },
                load_defaults(),
            )

    def test_feature_estimates_reject_invalid_size_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "feature.estimates.qa must be one of"):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 5,
                    "working_days": 20,
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
                                "name": "Bad Estimate Size",
                                "estimates": {
                                    "eng": "S",
                                    "qa": "XL"
                                },
                                "priority": "Medium"
                            }
                        ]
                    }
                },
                load_defaults(),
            )

    def test_feature_size_and_estimates_eng_must_match(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "feature.size must match feature.estimates.eng",
        ):
            PlanningInput.from_dict(
                {
                    "planning_mode": "capacity_check",
                    "planning_horizon": "month",
                    "calendar_year": 2026,
                    "month_index": 5,
                    "working_days": 20,
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
                                "name": "Mismatched Legacy Size",
                                "size": "M",
                                "estimates": {
                                    "eng": "L"
                                },
                                "priority": "High"
                            }
                        ]
                    }
                },
                load_defaults(),
            )

    def test_legacy_feature_size_maps_to_eng_only_demand(self) -> None:
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
                            "name": "Legacy Feature",
                            "size": "M",
                            "priority": "Medium"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        feature_demand = _feature_demands(planning_input, load_defaults())[0]
        self.assertEqual(feature_demand.demand_dev_days, 16.0)
        self.assertEqual(
            feature_demand.demand_by_function,
            {"eng": 16.0, "qa": 0.0, "devops": 0.0},
        )

    def test_legacy_feature_size_falls_back_for_missing_estimates_eng(self) -> None:
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
                            "name": "Mixed Legacy And QA",
                            "size": "M",
                            "estimates": {
                                "qa": "S"
                            },
                            "priority": "Medium"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        feature_demand = _feature_demands(planning_input, load_defaults())[0]
        self.assertEqual(feature_demand.demand_dev_days, 16.0)
        self.assertEqual(
            feature_demand.demand_by_function,
            {"eng": 16.0, "qa": 8.0, "devops": 0.0},
        )

    def test_total_demand_is_calculated_by_function(self) -> None:
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
                            "name": "Feature A",
                            "estimates": {
                                "eng": "M",
                                "qa": "S"
                            },
                            "priority": "High"
                        },
                        {
                            "name": "Feature B",
                            "estimates": {
                                "qa": "M",
                                "devops": "XS"
                            },
                            "priority": "Medium"
                        }
                    ]
                }
            },
            load_defaults(),
        )

        totals = _demand_by_function(_feature_demands(planning_input, load_defaults()), precision=2)
        self.assertEqual(totals, {"eng": 16.0, "qa": 24.0, "devops": 4.0})

    def test_rd_org_capacity_is_aggregated_by_function_across_teams(self) -> None:
        planning_input = PlanningInput.from_dict(
            {
                "planning_mode": "capacity_check",
                "planning_horizon": "month",
                "calendar_year": 2026,
                "month_index": 5,
                "working_days": 20,
                "holidays_days": 1,
                "vacation_days": 2,
                "sick_days": 1,
                "focus_factor": 0.75,
                "rd_org": {
                    "country_profiles": [
                        {
                            "id": "us",
                            "country_code": "US",
                            "working_day_rules": {"workweek": "mon-fri"},
                            "holiday_calendar_rules": {"dates": []},
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
                                    "country_profile": "us"
                                },
                                {
                                    "id": "qa-1",
                                    "function": "qa",
                                    "seniority": "Mid",
                                    "capacity_percent": 0.5,
                                    "country_profile": "us"
                                }
                            ]
                        },
                        {
                            "name": "Platform",
                            "members": [
                                {
                                    "id": "eng-2",
                                    "function": "eng",
                                    "seniority": "Mid",
                                    "capacity_percent": 0.5,
                                    "country_profile": "us"
                                },
                                {
                                    "id": "ops-1",
                                    "function": "devops",
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

        capacities = _capacity_by_function(planning_input, load_defaults(), precision=2)
        self.assertEqual(capacities, {"eng": 18.0, "qa": 6.0, "devops": 12.0})

    def test_rd_org_capacity_by_function_uses_derived_availability(self) -> None:
        planning_input = PlanningInput.from_dict(
            _load_raw_example("v2_rd_org_capacity_check.json"),
            load_defaults(),
        )

        capacities = _capacity_by_function(planning_input, load_defaults(), precision=2)
        self.assertEqual(capacities, {"eng": 44.41, "qa": 44.41, "devops": 22.21})

    def test_capacity_check_feasibility_requires_all_functions_to_fit(self) -> None:
        result = plan_capacity(
            PlanningInput.from_dict(
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
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
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
                                        "country_profile": "us"
                                    },
                                    {
                                        "id": "qa-1",
                                        "function": "qa",
                                        "seniority": "Mid",
                                        "capacity_percent": 0.25,
                                        "country_profile": "us"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {
                        "features": [
                            {
                                "id": "must-ship",
                                "name": "QA Bottleneck Feature",
                                "estimates": {
                                    "eng": "M",
                                    "qa": "M"
                                },
                                "priority": "High"
                            }
                        ]
                    },
                    "business_goals": {
                        "must_deliver_feature_ids": ["must-ship"]
                    }
                },
                load_defaults(),
            ),
            load_defaults(),
        )

        self.assertFalse(result["feasibility"])
        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": False, "devops": True},
        )
        self.assertEqual(result["bottleneck_functions"], ["qa"])
        self.assertFalse(result["selected_plan"]["feasibility"])
        self.assertEqual(
            result["selected_plan"]["function_capacity_fit"],
            {"eng": True, "qa": False, "devops": True},
        )
        self.assertEqual(result["selected_plan"]["bottleneck_functions"], ["qa"])

    def test_replanning_uses_function_capacity_fit_to_select_feasible_plan(self) -> None:
        result = plan_capacity(
            PlanningInput.from_dict(
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
                                "id": "us",
                                "country_code": "US",
                                "working_day_rules": {"workweek": "mon-fri"},
                                "holiday_calendar_rules": {"dates": []},
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
                                        "country_profile": "us"
                                    },
                                    {
                                        "id": "qa-1",
                                        "function": "qa",
                                        "seniority": "Mid",
                                        "capacity_percent": 0.25,
                                        "country_profile": "us"
                                    }
                                ]
                            }
                        ]
                    },
                    "roadmap": {
                        "features": [
                            {
                                "id": "feature-a",
                                "name": "Keep Me",
                                "estimates": {
                                    "eng": "S"
                                },
                                "priority": "High"
                            },
                            {
                                "id": "feature-b",
                                "name": "QA Heavy",
                                "estimates": {
                                    "qa": "M"
                                },
                                "priority": "Low"
                            }
                        ]
                    }
                },
                load_defaults(),
            ),
            load_defaults(),
        )

        self.assertFalse(result["feasibility"])
        self.assertEqual(result["bottleneck_functions"], ["qa"])
        self.assertTrue(result["selected_plan"]["feasibility"])
        self.assertEqual(
            result["selected_plan"]["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertEqual(result["selected_plan"]["bottleneck_functions"], [])
        self.assertEqual(
            [feature["name"] for feature in result["deferred_features"]],
            [],
        )
        self.assertEqual(
            [feature["name"] for feature in result["dropped_features"]],
            ["QA Heavy"],
        )

    def test_planning_schedule_returns_baseline_feasibility_without_replanning(self) -> None:
        result = plan_capacity(
            PlanningInput.from_dict(
                _load_raw_example("v2_rd_org_planning_schedule.json"),
                load_defaults(),
            ),
            load_defaults(),
        )

        self.assertFalse(result["feasibility"])
        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": False, "devops": True},
        )
        self.assertEqual(result["bottleneck_functions"], ["qa"])
        self.assertFalse(result["dependency_rules_pass"])
        self.assertEqual(len(result["dependency_violations"]), 1)
        self.assertIn("qa dependency rule failed", result["dependency_violations"][0])
        self.assertEqual(result["deferred_features"], [])
        self.assertEqual(result["dropped_features"], [])
        self.assertEqual(result["evaluated_alternatives"], [])
        self.assertEqual(result["agentic_iterations"], [])
        self.assertEqual(result["selected_plan"]["feasibility"], result["feasibility"])
        self.assertEqual(
            result["selected_plan"]["dependency_rules_pass"],
            result["dependency_rules_pass"],
        )
        self.assertEqual(
            result["selected_plan"]["dependency_violations"],
            result["dependency_violations"],
        )

    def test_planning_schedule_can_fail_due_to_dependency_pressure_only(self) -> None:
        result = plan_capacity(
            PlanningInput.from_dict(
                {
                    "planning_mode": "planning_schedule",
                    "planning_horizon": "sprint",
                    "start_date": "2026-03-02",
                    "end_date": "2026-03-13",
                    "working_days": 10,
                    "holidays_days": 0,
                    "vacation_days": 0,
                    "sick_days": 0,
                    "focus_factor": 1.0,
                    "rd_org": {
                        "country_profiles": [
                            {
                                "id": "il",
                                "country_code": "IL",
                                "working_day_rules": {"workweek": "sun-thu"},
                                "holiday_calendar_rules": {"dates": []},
                                "vacation_days_per_employee": 18,
                                "sick_days_per_employee": 8
                            }
                        ],
                        "org_schedule_policies": {
                            "post_dev_min_ratio": {
                                "qa": 0.4
                            }
                        },
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
                                        "seniority": "Mid",
                                        "country_profile": "il"
                                    },
                                    {
                                        "id": "eng-3",
                                        "function": "eng",
                                        "seniority": "Mid",
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
                                "id": "feature-1",
                                "name": "Dependency Pressure",
                                "estimates": {
                                    "eng": "L",
                                    "qa": "S"
                                },
                                "priority": "High"
                            }
                        ]
                    }
                },
                load_defaults(),
            ),
            load_defaults(),
        )

        self.assertEqual(
            result["function_capacity_fit"],
            {"eng": True, "qa": True, "devops": True},
        )
        self.assertFalse(result["dependency_rules_pass"])
        self.assertEqual(result["bottleneck_functions"], [])
        self.assertFalse(result["feasibility"])
        self.assertIn("qa dependency rule failed", result["dependency_violations"][0])

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
