"""Validated models for planning input and output."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Any


class InputValidationError(ValueError):
    """Raised when the incoming JSON payload is invalid."""


SUPPORTED_PLANNING_HORIZONS = {"year", "half_year", "quarter", "month", "sprint"}
SUPPORTED_PLANNING_MODES = {"capacity_check", "planning_schedule"}
SUPPORTED_MEMBER_FUNCTIONS = {"eng", "qa", "devops"}
SUPPORTED_FEATURE_SIZES = {"XS", "S", "M", "L"}
SUPPORTED_PRIORITIES = {"Critical", "High", "Medium", "Low"}
SUPPORTED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
SUPPORTED_CANDIDATE_SORT_KEYS = {
    "preserved_priority",
    "defer_preference",
    "demand_desc",
    "original_index",
}
SUPPORTED_PLAN_SCORE_KEYS = {
    "acceptable",
    "goal_compliant",
    "feasible",
    "hard_constraint_violations",
    "utilization_gap",
    "buffer_gap",
    "soft_goal_violations",
    "delivered_priority_value",
    "removed_feature_count",
}


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputValidationError(f"{field_name} must be a JSON object.")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputValidationError(f"{field_name} must be a JSON array.")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{field_name} must be a non-empty string.")
    return value


def _require_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InputValidationError(f"{field_name} must be a number.")
    return float(value)


def _require_non_negative_number(value: Any, field_name: str) -> float:
    parsed_value = _require_number(value, field_name)
    if parsed_value < 0:
        raise InputValidationError(f"{field_name} must be greater than or equal to 0.")
    return parsed_value


def _require_fraction(value: Any, field_name: str) -> float:
    parsed_value = _require_number(value, field_name)
    if parsed_value < 0 or parsed_value > 1:
        raise InputValidationError(f"{field_name} must be between 0 and 1.")
    return parsed_value


def _require_positive_integer(value: Any, field_name: str) -> int:
    parsed_number = _require_non_negative_number(value, field_name)
    parsed_value = int(parsed_number)
    if parsed_value != parsed_number:
        raise InputValidationError(f"{field_name} must be an integer.")
    if parsed_value < 1:
        raise InputValidationError(f"{field_name} must be at least 1.")
    return parsed_value


def _require_iso_date(value: Any, field_name: str) -> date:
    raw_value = _require_string(value, field_name)
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise InputValidationError(f"{field_name} must be a valid ISO date.") from exc


@dataclass(frozen=True, slots=True)
class PeriodSelectors:
    calendar_year: int | None
    half_year_index: int | None
    quarter_index: int | None
    month_index: int | None
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True, slots=True)
class PlanningPeriod:
    start_date: date
    end_date: date
    total_calendar_days: int


def _planning_period_from_dates(start_date: date, end_date: date) -> PlanningPeriod:
    return PlanningPeriod(
        start_date=start_date,
        end_date=end_date,
        total_calendar_days=(end_date - start_date).days + 1,
    )


def _parse_period_selectors(
    data: dict[str, Any], planning_horizon: str
) -> PeriodSelectors:
    selector_fields = {
        "calendar_year",
        "half_year_index",
        "quarter_index",
        "month_index",
        "start_date",
        "end_date",
    }
    present_selector_fields = {
        field_name for field_name in selector_fields if data.get(field_name) is not None
    }
    required_fields_by_horizon = {
        "year": {"calendar_year"},
        "half_year": {"calendar_year", "half_year_index"},
        "quarter": {"calendar_year", "quarter_index"},
        "month": {"calendar_year", "month_index"},
        "sprint": {"start_date", "end_date"},
    }
    required_fields = required_fields_by_horizon[planning_horizon]
    missing_fields = sorted(required_fields - present_selector_fields)
    if missing_fields:
        raise InputValidationError(
            f"{planning_horizon} planning requires: " + ", ".join(missing_fields) + "."
        )
    unexpected_fields = sorted(present_selector_fields - required_fields)
    if unexpected_fields:
        raise InputValidationError(
            f"{planning_horizon} planning does not support: "
            + ", ".join(unexpected_fields)
            + "."
        )

    calendar_year = (
        _require_positive_integer(data.get("calendar_year"), "calendar_year")
        if "calendar_year" in required_fields
        else None
    )
    half_year_index = (
        _require_positive_integer(data.get("half_year_index"), "half_year_index")
        if "half_year_index" in required_fields
        else None
    )
    quarter_index = (
        _require_positive_integer(data.get("quarter_index"), "quarter_index")
        if "quarter_index" in required_fields
        else None
    )
    month_index = (
        _require_positive_integer(data.get("month_index"), "month_index")
        if "month_index" in required_fields
        else None
    )
    start_date = (
        _require_iso_date(data.get("start_date"), "start_date")
        if "start_date" in required_fields
        else None
    )
    end_date = (
        _require_iso_date(data.get("end_date"), "end_date")
        if "end_date" in required_fields
        else None
    )

    if half_year_index is not None and half_year_index not in {1, 2}:
        raise InputValidationError("half_year_index must be 1 or 2.")
    if quarter_index is not None and quarter_index not in {1, 2, 3, 4}:
        raise InputValidationError("quarter_index must be 1, 2, 3, or 4.")
    if month_index is not None and month_index not in set(range(1, 13)):
        raise InputValidationError("month_index must be between 1 and 12.")
    if start_date is not None and end_date is not None and end_date < start_date:
        raise InputValidationError("end_date must be greater than or equal to start_date.")

    return PeriodSelectors(
        calendar_year=calendar_year,
        half_year_index=half_year_index,
        quarter_index=quarter_index,
        month_index=month_index,
        start_date=start_date,
        end_date=end_date,
    )


def _derive_planning_period(
    planning_horizon: str, period_selectors: PeriodSelectors
) -> PlanningPeriod:
    if planning_horizon == "year":
        assert period_selectors.calendar_year is not None
        return _planning_period_from_dates(
            date(period_selectors.calendar_year, 1, 1),
            date(period_selectors.calendar_year, 12, 31),
        )

    if planning_horizon == "half_year":
        assert period_selectors.calendar_year is not None
        assert period_selectors.half_year_index is not None
        start_month = 1 if period_selectors.half_year_index == 1 else 7
        end_month = start_month + 5
        return _planning_period_from_dates(
            date(period_selectors.calendar_year, start_month, 1),
            date(
                period_selectors.calendar_year,
                end_month,
                monthrange(period_selectors.calendar_year, end_month)[1],
            ),
        )

    if planning_horizon == "quarter":
        assert period_selectors.calendar_year is not None
        assert period_selectors.quarter_index is not None
        start_month = ((period_selectors.quarter_index - 1) * 3) + 1
        end_month = start_month + 2
        return _planning_period_from_dates(
            date(period_selectors.calendar_year, start_month, 1),
            date(
                period_selectors.calendar_year,
                end_month,
                monthrange(period_selectors.calendar_year, end_month)[1],
            ),
        )

    if planning_horizon == "month":
        assert period_selectors.calendar_year is not None
        assert period_selectors.month_index is not None
        return _planning_period_from_dates(
            date(period_selectors.calendar_year, period_selectors.month_index, 1),
            date(
                period_selectors.calendar_year,
                period_selectors.month_index,
                monthrange(
                    period_selectors.calendar_year, period_selectors.month_index
                )[1],
            ),
        )

    assert period_selectors.start_date is not None
    assert period_selectors.end_date is not None
    return _planning_period_from_dates(
        period_selectors.start_date,
        period_selectors.end_date,
    )


@dataclass(frozen=True, slots=True)
class DefaultsConfig:
    capacity_percent_default: float
    focus_factor_default: float
    sprint_days_default: float
    overhead_days_per_sprint_default: float
    feature_size_multipliers: dict[str, float]
    priority_rank: dict[str, int]
    log_level_default: str
    utilization_target_min: float
    utilization_target_max: float
    buffer_target_ratio: float
    defer_preference_default: tuple[str, ...]
    candidate_sort_order: tuple[str, ...]
    plan_score_order: tuple[str, ...]
    agentic_max_iterations: int
    agentic_candidate_limit: int
    output_precision: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DefaultsConfig:
        required_keys = {
            "capacity_percent_default",
            "focus_factor_default",
            "sprint_days_default",
            "overhead_days_per_sprint_default",
            "feature_size_multipliers",
            "priority_rank",
            "log_level_default",
            "utilization_target_min",
            "utilization_target_max",
            "buffer_target_ratio",
            "defer_preference_default",
            "candidate_sort_order",
            "plan_score_order",
            "agentic_max_iterations",
            "agentic_candidate_limit",
            "output_precision",
        }
        missing_keys = sorted(required_keys - set(data))
        if missing_keys:
            raise InputValidationError(
                "defaults config is missing required keys: " + ", ".join(missing_keys)
            )

        size_multipliers = _require_mapping(
            data["feature_size_multipliers"], "feature_size_multipliers"
        )
        priority_rank = _require_mapping(data["priority_rank"], "priority_rank")
        defer_preference = tuple(
            _require_string(priority_name, "defer_preference_default item")
            for priority_name in _require_list(
                data["defer_preference_default"], "defer_preference_default"
            )
        )
        candidate_sort_order = tuple(
            _require_string(item, "candidate_sort_order item")
            for item in _require_list(data["candidate_sort_order"], "candidate_sort_order")
        )
        plan_score_order = tuple(
            _require_string(item, "plan_score_order item")
            for item in _require_list(data["plan_score_order"], "plan_score_order")
        )
        if set(defer_preference) != SUPPORTED_PRIORITIES:
            raise InputValidationError(
                "defer_preference_default must define Critical, High, Medium, and Low."
            )
        if tuple(dict.fromkeys(candidate_sort_order)) != candidate_sort_order:
            raise InputValidationError("candidate_sort_order must not contain duplicates.")
        if set(candidate_sort_order) != SUPPORTED_CANDIDATE_SORT_KEYS:
            raise InputValidationError(
                "candidate_sort_order must contain preserved_priority, defer_preference, "
                "demand_desc, and original_index."
            )
        if tuple(dict.fromkeys(plan_score_order)) != plan_score_order:
            raise InputValidationError("plan_score_order must not contain duplicates.")
        if set(plan_score_order) != SUPPORTED_PLAN_SCORE_KEYS:
            raise InputValidationError(
                "plan_score_order must define all supported score components."
            )
        agentic_max_iterations = int(
            _require_non_negative_number(
                data["agentic_max_iterations"], "agentic_max_iterations"
            )
        )
        agentic_candidate_limit = int(
            _require_non_negative_number(
                data["agentic_candidate_limit"], "agentic_candidate_limit"
            )
        )
        if agentic_candidate_limit < 1:
            raise InputValidationError("agentic_candidate_limit must be at least 1.")
        log_level_default = _require_string(data["log_level_default"], "log_level_default").upper()
        if log_level_default not in SUPPORTED_LOG_LEVELS:
            raise InputValidationError(
                f"log_level_default must be one of {sorted(SUPPORTED_LOG_LEVELS)}."
            )

        parsed_size_multipliers = {
            _require_string(size_name, "feature_size_multipliers key"): (
                _require_non_negative_number(
                    multiplier, f"feature_size_multipliers.{size_name}"
                )
            )
            for size_name, multiplier in size_multipliers.items()
        }
        if set(parsed_size_multipliers) != SUPPORTED_FEATURE_SIZES:
            raise InputValidationError("feature_size_multipliers must define XS, S, M, and L.")

        parsed_priority_rank = {
            _require_string(priority_name, "priority_rank key"): int(
                _require_non_negative_number(rank, f"priority_rank.{priority_name}")
            )
            for priority_name, rank in priority_rank.items()
        }
        if set(parsed_priority_rank) != SUPPORTED_PRIORITIES:
            raise InputValidationError("priority_rank must define Critical, High, Medium, and Low.")

        return cls(
            capacity_percent_default=_require_fraction(
                data["capacity_percent_default"], "capacity_percent_default"
            ),
            focus_factor_default=_require_fraction(
                data["focus_factor_default"], "focus_factor_default"
            ),
            sprint_days_default=_require_non_negative_number(
                data["sprint_days_default"], "sprint_days_default"
            ),
            overhead_days_per_sprint_default=_require_non_negative_number(
                data["overhead_days_per_sprint_default"], "overhead_days_per_sprint_default"
            ),
            feature_size_multipliers=parsed_size_multipliers,
            priority_rank=parsed_priority_rank,
            log_level_default=log_level_default,
            utilization_target_min=_require_fraction(
                data["utilization_target_min"], "utilization_target_min"
            ),
            utilization_target_max=_require_fraction(
                data["utilization_target_max"], "utilization_target_max"
            ),
            buffer_target_ratio=_require_fraction(
                data["buffer_target_ratio"], "buffer_target_ratio"
            ),
            defer_preference_default=defer_preference,
            candidate_sort_order=candidate_sort_order,
            plan_score_order=plan_score_order,
            agentic_max_iterations=agentic_max_iterations,
            agentic_candidate_limit=agentic_candidate_limit,
            output_precision=int(
                _require_non_negative_number(data["output_precision"], "output_precision")
            ),
        )


@dataclass(frozen=True, slots=True)
class TeamMember:
    name: str
    capacity_percent: float

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        role_group_capacity_percent: float | None,
        defaults: DefaultsConfig,
    ) -> TeamMember:
        capacity_percent = data.get(
            "capacity_percent",
            role_group_capacity_percent
            if role_group_capacity_percent is not None
            else defaults.capacity_percent_default,
        )
        return cls(
            name=_require_string(data.get("name"), "member.name"),
            capacity_percent=_require_fraction(capacity_percent, "member.capacity_percent"),
        )


@dataclass(frozen=True, slots=True)
class RoleGroup:
    role: str
    seniority: str
    count: int | None
    capacity_percent: float | None
    members: tuple[TeamMember, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> RoleGroup:
        role = _require_string(data.get("role"), "role")
        seniority = _require_string(data.get("seniority"), "seniority")
        count_value = data.get("count")
        members_value = data.get("members")
        capacity_percent_value = data.get("capacity_percent")

        if count_value is None and members_value is None:
            raise InputValidationError(
                f"role group '{role}' must define either count or members."
            )
        if count_value is not None and members_value is not None:
            raise InputValidationError(
                f"role group '{role}' must not define both count and members."
            )

        capacity_percent = (
            None
            if capacity_percent_value is None
            else _require_fraction(capacity_percent_value, "role.capacity_percent")
        )

        members: tuple[TeamMember, ...]
        count: int | None
        if members_value is not None:
            raw_members = _require_list(members_value, "members")
            members = tuple(
                TeamMember.from_dict(
                    _require_mapping(member, "member"),
                    role_group_capacity_percent=capacity_percent,
                    defaults=defaults,
                )
                for member in raw_members
            )
            count = None
        else:
            count = int(_require_non_negative_number(count_value, "count"))
            members = ()

        return cls(
            role=role,
            seniority=seniority,
            count=count,
            capacity_percent=capacity_percent,
            members=members,
        )


@dataclass(frozen=True, slots=True)
class Team:
    name: str
    roles: tuple[RoleGroup, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> Team:
        roles = tuple(
            RoleGroup.from_dict(_require_mapping(role, "role"), defaults)
            for role in _require_list(data.get("roles"), "roles")
        )
        return cls(
            name=_require_string(data.get("name"), "team.name"),
            roles=roles,
        )


@dataclass(frozen=True, slots=True)
class RdOrgMember:
    id: str
    function: str
    seniority: str
    capacity_percent: float
    country_profile: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> RdOrgMember:
        function = _require_string(data.get("function"), "member.function")
        if function not in SUPPORTED_MEMBER_FUNCTIONS:
            raise InputValidationError(
                f"member.function must be one of {sorted(SUPPORTED_MEMBER_FUNCTIONS)}."
            )
        capacity_percent = _require_fraction(
            data.get("capacity_percent", defaults.capacity_percent_default),
            "member.capacity_percent",
        )
        return cls(
            id=_require_string(data.get("id"), "member.id"),
            function=function,
            seniority=_require_string(data.get("seniority"), "member.seniority"),
            capacity_percent=capacity_percent,
            country_profile=_require_string(data.get("country_profile"), "member.country_profile"),
        )


@dataclass(frozen=True, slots=True)
class CountryProfile:
    id: str
    country_code: str
    working_day_rules: dict[str, Any]
    holiday_calendar_rules: dict[str, Any]
    vacation_days_per_employee: float
    sick_days_per_employee: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CountryProfile:
        return cls(
            id=_require_string(data.get("id"), "country_profile.id"),
            country_code=_require_string(data.get("country_code"), "country_profile.country_code"),
            working_day_rules=_require_mapping(
                data.get("working_day_rules"), "country_profile.working_day_rules"
            ),
            holiday_calendar_rules=_require_mapping(
                data.get("holiday_calendar_rules"),
                "country_profile.holiday_calendar_rules",
            ),
            vacation_days_per_employee=_require_non_negative_number(
                data.get("vacation_days_per_employee"),
                "country_profile.vacation_days_per_employee",
            ),
            sick_days_per_employee=_require_non_negative_number(
                data.get("sick_days_per_employee"),
                "country_profile.sick_days_per_employee",
            ),
        )


@dataclass(frozen=True, slots=True)
class RdOrgTeam:
    name: str
    members: tuple[RdOrgMember, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> RdOrgTeam:
        members = tuple(
            RdOrgMember.from_dict(_require_mapping(member, "member"), defaults)
            for member in _require_list(data.get("members"), "team.members")
        )
        if not members:
            raise InputValidationError("team.members must contain at least one member.")
        return cls(
            name=_require_string(data.get("name"), "team.name"),
            members=members,
        )

    def to_team(self) -> Team:
        grouped_members: dict[tuple[str, str], list[TeamMember]] = {}
        for member in self.members:
            grouped_members.setdefault((member.function, member.seniority), []).append(
                TeamMember(name=member.id, capacity_percent=member.capacity_percent)
            )

        roles = tuple(
            RoleGroup(
                role=function,
                seniority=seniority,
                count=None,
                capacity_percent=None,
                members=tuple(members),
            )
            for function, seniority in sorted(grouped_members)
            for members in [grouped_members[(function, seniority)]]
        )
        return Team(name=self.name, roles=roles)


@dataclass(frozen=True, slots=True)
class RdOrg:
    country_profiles: tuple[CountryProfile, ...]
    teams: tuple[RdOrgTeam, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> RdOrg:
        country_profiles = tuple(
            CountryProfile.from_dict(_require_mapping(profile, "country_profile"))
            for profile in _require_list(data.get("country_profiles"), "rd_org.country_profiles")
        )
        if not country_profiles:
            raise InputValidationError(
                "rd_org.country_profiles must contain at least one country profile."
            )

        country_profile_ids = [profile.id for profile in country_profiles]
        duplicate_country_profile_ids = sorted(
            profile_id
            for profile_id in set(country_profile_ids)
            if country_profile_ids.count(profile_id) > 1
        )
        if duplicate_country_profile_ids:
            raise InputValidationError(
                "rd_org country profile ids must be unique: "
                + ", ".join(duplicate_country_profile_ids)
            )

        teams = tuple(
            RdOrgTeam.from_dict(_require_mapping(team, "team"), defaults)
            for team in _require_list(data.get("teams"), "rd_org.teams")
        )
        if not teams:
            raise InputValidationError("rd_org.teams must contain at least one team.")

        member_ids = [member.id for team in teams for member in team.members]
        duplicate_member_ids = sorted(
            member_id for member_id in set(member_ids) if member_ids.count(member_id) > 1
        )
        if duplicate_member_ids:
            raise InputValidationError(
                "rd_org member ids must be unique: " + ", ".join(duplicate_member_ids)
            )

        unknown_country_profiles = sorted(
            {
                member.country_profile
                for team in teams
                for member in team.members
                if member.country_profile not in set(country_profile_ids)
            }
        )
        if unknown_country_profiles:
            raise InputValidationError(
                "rd_org members reference unknown country profiles: "
                + ", ".join(unknown_country_profiles)
            )

        return cls(country_profiles=country_profiles, teams=teams)

    def to_teams(self) -> tuple[Team, ...]:
        return tuple(team.to_team() for team in self.teams)


@dataclass(frozen=True, slots=True)
class Feature:
    id: str | None
    name: str
    size: str
    priority: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Feature:
        size = _require_string(data.get("size"), "feature.size")
        priority = _require_string(data.get("priority"), "feature.priority")
        if size not in SUPPORTED_FEATURE_SIZES:
            raise InputValidationError(
                f"feature.size must be one of {sorted(SUPPORTED_FEATURE_SIZES)}."
            )
        if priority not in SUPPORTED_PRIORITIES:
            raise InputValidationError(
                f"feature.priority must be one of {sorted(SUPPORTED_PRIORITIES)}."
            )
        return cls(
            id=(
                None
                if data.get("id") is None
                else _require_string(data.get("id"), "feature.id")
            ),
            name=_require_string(data.get("name"), "feature.name"),
            size=size,
            priority=priority,
        )

    @property
    def reference(self) -> str:
        return self.id if self.id is not None else self.name


@dataclass(frozen=True, slots=True)
class BusinessGoals:
    must_deliver_feature_ids: tuple[str, ...]
    preserve_priorities: tuple[str, ...]
    max_utilization: float
    min_buffer_ratio: float
    defer_preference: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> BusinessGoals:
        must_deliver_feature_ids = tuple(
            _require_string(feature_id, "business_goals.must_deliver_feature_ids item")
            for feature_id in _require_list(
                data.get("must_deliver_feature_ids", []),
                "business_goals.must_deliver_feature_ids",
            )
        )
        preserve_priorities = tuple(
            _require_string(priority, "business_goals.preserve_priorities item")
            for priority in _require_list(
                data.get("preserve_priorities", []),
                "business_goals.preserve_priorities",
            )
        )
        defer_preference = tuple(
            _require_string(priority, "business_goals.defer_preference item")
            for priority in _require_list(
                data.get("defer_preference", list(defaults.defer_preference_default)),
                "business_goals.defer_preference",
            )
        )
        for priority in preserve_priorities + defer_preference:
            if priority not in SUPPORTED_PRIORITIES:
                raise InputValidationError(
                    f"business goal priority values must be one of {sorted(SUPPORTED_PRIORITIES)}."
                )
        if set(defer_preference) != SUPPORTED_PRIORITIES:
            raise InputValidationError(
                "business_goals.defer_preference must contain each priority exactly once."
            )
        return cls(
            must_deliver_feature_ids=must_deliver_feature_ids,
            preserve_priorities=preserve_priorities,
            max_utilization=_require_fraction(
                data.get("max_utilization", defaults.utilization_target_max),
                "business_goals.max_utilization",
            ),
            min_buffer_ratio=_require_fraction(
                data.get("min_buffer_ratio", defaults.buffer_target_ratio),
                "business_goals.min_buffer_ratio",
            ),
            defer_preference=defer_preference,
        )


@dataclass(frozen=True, slots=True)
class PlanningInput:
    planning_mode: str
    planning_horizon: str
    calendar_year: int | None
    half_year_index: int | None
    quarter_index: int | None
    month_index: int | None
    start_date: date | None
    end_date: date | None
    planning_period: PlanningPeriod
    working_days: float
    holidays_days: float
    vacation_days: float
    sick_days: float
    focus_factor: float
    sprint_days: float
    overhead_days_per_sprint: float
    rd_org: RdOrg | None
    teams: tuple[Team, ...]
    features: tuple[Feature, ...]
    business_goals: BusinessGoals

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> PlanningInput:
        planning_mode = _require_string(data.get("planning_mode"), "planning_mode")
        if planning_mode not in SUPPORTED_PLANNING_MODES:
            raise InputValidationError(
                f"planning_mode must be one of {sorted(SUPPORTED_PLANNING_MODES)}."
            )
        planning_horizon = _require_string(data.get("planning_horizon"), "planning_horizon")
        if planning_horizon not in SUPPORTED_PLANNING_HORIZONS:
            raise InputValidationError(
                f"planning_horizon must be one of {sorted(SUPPORTED_PLANNING_HORIZONS)}."
            )
        period_selectors = _parse_period_selectors(data, planning_horizon)
        planning_period = _derive_planning_period(planning_horizon, period_selectors)

        focus_factor = _require_fraction(
            data.get("focus_factor", defaults.focus_factor_default), "focus_factor"
        )
        sprint_days = _require_non_negative_number(
            data.get("sprint_days", defaults.sprint_days_default), "sprint_days"
        )
        overhead_days_per_sprint = _require_non_negative_number(
            data.get("overhead_days_per_sprint", defaults.overhead_days_per_sprint_default),
            "overhead_days_per_sprint",
        )
        if overhead_days_per_sprint > sprint_days:
            raise InputValidationError("overhead_days_per_sprint must not exceed sprint_days.")

        roadmap = _require_mapping(data.get("roadmap"), "roadmap")
        rd_org_value = data.get("rd_org")
        team_structure_value = data.get("team_structure")
        if rd_org_value is not None and team_structure_value is not None:
            raise InputValidationError("Provide either rd_org or team_structure, not both.")
        if rd_org_value is None and team_structure_value is None:
            raise InputValidationError("One of rd_org or team_structure is required.")

        if rd_org_value is not None:
            rd_org = RdOrg.from_dict(_require_mapping(rd_org_value, "rd_org"), defaults)
            teams = rd_org.to_teams()
        else:
            rd_org = None
            team_structure = _require_mapping(team_structure_value, "team_structure")
            teams = tuple(
                Team.from_dict(_require_mapping(team, "team"), defaults)
                for team in _require_list(team_structure.get("teams"), "team_structure.teams")
            )
        features = tuple(
            Feature.from_dict(_require_mapping(feature, "feature"))
            for feature in _require_list(roadmap.get("features"), "roadmap.features")
        )
        feature_references = [feature.reference for feature in features]
        if len(feature_references) != len(set(feature_references)):
            raise InputValidationError(
                "feature ids or names must be unique so business goals can reference them safely."
            )

        working_days = _require_non_negative_number(data.get("working_days"), "working_days")
        holidays_days = _require_non_negative_number(data.get("holidays_days"), "holidays_days")
        vacation_days = _require_non_negative_number(data.get("vacation_days"), "vacation_days")
        sick_days = _require_non_negative_number(data.get("sick_days"), "sick_days")

        unavailable_days = holidays_days + vacation_days + sick_days
        if unavailable_days > working_days:
            raise InputValidationError(
                "holidays_days + vacation_days + sick_days must not exceed working_days."
            )

        business_goals = BusinessGoals.from_dict(
            _require_mapping(data.get("business_goals", {}), "business_goals"),
            defaults,
        )
        missing_must_deliver = sorted(
            set(business_goals.must_deliver_feature_ids) - set(feature_references)
        )
        if missing_must_deliver:
            raise InputValidationError(
                "business_goals.must_deliver_feature_ids contains unknown features: "
                + ", ".join(missing_must_deliver)
            )

        return cls(
            planning_mode=planning_mode,
            planning_horizon=planning_horizon,
            calendar_year=period_selectors.calendar_year,
            half_year_index=period_selectors.half_year_index,
            quarter_index=period_selectors.quarter_index,
            month_index=period_selectors.month_index,
            start_date=period_selectors.start_date,
            end_date=period_selectors.end_date,
            planning_period=planning_period,
            working_days=working_days,
            holidays_days=holidays_days,
            vacation_days=vacation_days,
            sick_days=sick_days,
            focus_factor=focus_factor,
            sprint_days=sprint_days,
            overhead_days_per_sprint=overhead_days_per_sprint,
            rd_org=rd_org,
            teams=teams,
            features=features,
            business_goals=business_goals,
        )


@dataclass(frozen=True, slots=True)
class EngineerCapacity:
    team_name: str
    role: str
    seniority: str
    member_name: str
    capacity_percent: float


@dataclass(frozen=True, slots=True)
class FeatureDemand:
    feature: Feature
    demand_dev_days: float
    original_index: int

    def to_dict(self, *, precision: int) -> dict[str, Any]:
        feature_dict: dict[str, Any] = {
            "name": self.feature.name,
            "size": self.feature.size,
            "priority": self.feature.priority,
            "demand_dev_days": round(self.demand_dev_days, precision),
        }
        if self.feature.id is not None:
            feature_dict["id"] = self.feature.id
        return feature_dict
