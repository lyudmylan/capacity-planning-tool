"""Validated models for planning input and output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class InputValidationError(ValueError):
    """Raised when the incoming JSON payload is invalid."""


SUPPORTED_PLANNING_HORIZONS = {"year", "half_year", "quarter", "month", "sprint"}
SUPPORTED_FEATURE_SIZES = {"XS", "S", "M", "L"}
SUPPORTED_PRIORITIES = {"Critical", "High", "Medium", "Low"}


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


@dataclass(frozen=True, slots=True)
class DefaultsConfig:
    capacity_percent_default: float
    focus_factor_default: float
    sprint_days_default: float
    overhead_days_per_sprint_default: float
    feature_size_multipliers: dict[str, float]
    priority_rank: dict[str, int]
    utilization_target_min: float
    utilization_target_max: float
    buffer_target_ratio: float
    defer_preference_default: tuple[str, ...]
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
            "utilization_target_min",
            "utilization_target_max",
            "buffer_target_ratio",
            "defer_preference_default",
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
        if set(defer_preference) != SUPPORTED_PRIORITIES:
            raise InputValidationError(
                "defer_preference_default must define Critical, High, Medium, and Low."
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
    planning_horizon: str
    working_days: float
    holidays_days: float
    vacation_days: float
    sick_days: float
    focus_factor: float
    sprint_days: float
    overhead_days_per_sprint: float
    teams: tuple[Team, ...]
    features: tuple[Feature, ...]
    business_goals: BusinessGoals

    @classmethod
    def from_dict(cls, data: dict[str, Any], defaults: DefaultsConfig) -> PlanningInput:
        planning_horizon = _require_string(data.get("planning_horizon"), "planning_horizon")
        if planning_horizon not in SUPPORTED_PLANNING_HORIZONS:
            raise InputValidationError(
                f"planning_horizon must be one of {sorted(SUPPORTED_PLANNING_HORIZONS)}."
            )

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

        team_structure = _require_mapping(data.get("team_structure"), "team_structure")
        roadmap = _require_mapping(data.get("roadmap"), "roadmap")
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
            planning_horizon=planning_horizon,
            working_days=working_days,
            holidays_days=holidays_days,
            vacation_days=vacation_days,
            sick_days=sick_days,
            focus_factor=focus_factor,
            sprint_days=sprint_days,
            overhead_days_per_sprint=overhead_days_per_sprint,
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
