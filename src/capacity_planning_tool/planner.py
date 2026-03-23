"""Core capacity planning logic."""

from __future__ import annotations

from typing import Any

from capacity_planning_tool.models import (
    DefaultsConfig,
    EngineerCapacity,
    FeatureDemand,
    PlanningInput,
)


def _round_number(value: float, precision: int) -> float:
    return round(value, precision)


def _expand_engineers(
    planning_input: PlanningInput, defaults: DefaultsConfig
) -> list[EngineerCapacity]:
    engineers: list[EngineerCapacity] = []
    for team in planning_input.teams:
        for role in team.roles:
            if role.members:
                for member in role.members:
                    engineers.append(
                        EngineerCapacity(
                            team_name=team.name,
                            role=role.role,
                            seniority=role.seniority,
                            member_name=member.name,
                            capacity_percent=member.capacity_percent,
                        )
                    )
                continue

            group_capacity = (
                role.capacity_percent
                if role.capacity_percent is not None
                else defaults.capacity_percent_default
            )
            engineer_count = role.count if role.count is not None else 0
            for index in range(engineer_count):
                engineers.append(
                    EngineerCapacity(
                        team_name=team.name,
                        role=role.role,
                        seniority=role.seniority,
                        member_name=f"{team.name}-{role.role}-{index + 1}",
                        capacity_percent=group_capacity,
                    )
                )
    return engineers


def _feature_demands(
    planning_input: PlanningInput, defaults: DefaultsConfig
) -> list[FeatureDemand]:
    effective_dev_days_per_sprint = (
        planning_input.sprint_days - planning_input.overhead_days_per_sprint
    )
    feature_demands: list[FeatureDemand] = []
    for index, feature in enumerate(planning_input.features):
        multiplier = defaults.feature_size_multipliers[feature.size]
        feature_demands.append(
            FeatureDemand(
                feature=feature,
                demand_dev_days=effective_dev_days_per_sprint * multiplier,
                original_index=index,
            )
        )
    return feature_demands


def _capacity_dev_days(
    planning_input: PlanningInput,
    engineer_capacities: list[EngineerCapacity],
    *,
    precision: int,
) -> float:
    net_days_per_engineer = (
        planning_input.working_days
        - planning_input.holidays_days
        - planning_input.vacation_days
        - planning_input.sick_days
    )
    total_capacity = sum(
        net_days_per_engineer * engineer.capacity_percent * planning_input.focus_factor
        for engineer in engineer_capacities
    )
    return _round_number(total_capacity, precision)


def _demand_dev_days(feature_demands: list[FeatureDemand], *, precision: int) -> float:
    return _round_number(sum(feature.demand_dev_days for feature in feature_demands), precision)


def _utilization(demand_dev_days: float, capacity_dev_days: float, *, precision: int) -> float:
    if capacity_dev_days == 0:
        return 0.0 if demand_dev_days == 0 else float("inf")
    return _round_number(demand_dev_days / capacity_dev_days, precision)


def _buffer_dev_days(capacity_dev_days: float, demand_dev_days: float, *, precision: int) -> float:
    return _round_number(capacity_dev_days - demand_dev_days, precision)


def _sort_for_recommendation(
    feature_demands: list[FeatureDemand], defaults: DefaultsConfig
) -> list[FeatureDemand]:
    return sorted(
        feature_demands,
        key=lambda item: (
            defaults.priority_rank[item.feature.priority],
            -item.demand_dev_days,
            item.original_index,
        ),
    )


def _recommend_scope_changes(
    feature_demands: list[FeatureDemand],
    capacity_dev_days: float,
    defaults: DefaultsConfig,
) -> tuple[list[FeatureDemand], list[FeatureDemand]]:
    target_demand = min(
        capacity_dev_days,
        capacity_dev_days * defaults.utilization_target_max,
        capacity_dev_days * (1 - defaults.buffer_target_ratio),
    )
    removable = _sort_for_recommendation(feature_demands, defaults)
    delivered = list(feature_demands)
    removed: list[FeatureDemand] = []
    remaining_demand = sum(item.demand_dev_days for item in feature_demands)

    for item in removable:
        if remaining_demand <= target_demand:
            break
        delivered = [
            candidate
            for candidate in delivered
            if candidate.original_index != item.original_index
        ]
        removed.append(item)
        remaining_demand -= item.demand_dev_days

    delivered.sort(key=lambda item: item.original_index)
    removed.sort(key=lambda item: item.original_index)
    return delivered, removed


def _build_risks(
    *,
    feasibility: bool,
    utilization: float,
    buffer_dev_days: float,
    capacity_dev_days: float,
    defaults: DefaultsConfig,
) -> list[str]:
    risks: list[str] = []
    if not feasibility:
        risks.append("Roadmap demand exceeds available capacity for the selected horizon.")
    if utilization > defaults.utilization_target_max:
        risks.append(
            "Utilization is above the target range, leaving little room for interruptions."
        )
    if 0 <= utilization < defaults.utilization_target_min:
        risks.append(
            "Utilization is below the target range, which may indicate under-committed capacity."
        )
    if buffer_dev_days < capacity_dev_days * defaults.buffer_target_ratio:
        risks.append("Buffer is below the target threshold, increasing delivery risk.")
    return risks


def _build_suggestions(
    *,
    feasibility: bool,
    removed_features: list[FeatureDemand],
    delivered_features: list[FeatureDemand],
    capacity_dev_days: float,
    defaults: DefaultsConfig,
    precision: int,
) -> list[str]:
    if not feasibility and removed_features:
        recommended_demand = _round_number(
            sum(feature.demand_dev_days for feature in delivered_features), precision
        )
        recommended_utilization = _utilization(
            recommended_demand, capacity_dev_days, precision=precision
        )
        return [
            "Reduce scope using the recommended delivered feature set.",
            (
                f"The recommended plan brings demand to {recommended_demand} dev days "
                f"at {recommended_utilization} utilization."
            ),
        ]

    suggestions: list[str] = []
    current_utilization = _utilization(
        _round_number(sum(feature.demand_dev_days for feature in delivered_features), precision),
        capacity_dev_days,
        precision=precision,
    )
    if current_utilization > defaults.utilization_target_max:
        suggestions.append("Defer the lowest-priority feature to rebuild delivery buffer.")
    if 0 <= current_utilization < defaults.utilization_target_min:
        suggestions.append("Pull in more roadmap work if a higher utilization target is desired.")
    if not suggestions:
        suggestions.append("Current scope is aligned with the available capacity targets.")
    return suggestions


def _build_tradeoff_summary(
    *,
    feasibility: bool,
    delivered_features: list[FeatureDemand],
    removed_features: list[FeatureDemand],
    original_demand_dev_days: float,
    capacity_dev_days: float,
    precision: int,
) -> list[str]:
    if feasibility:
        return ["The original roadmap fits within available capacity."]

    recommended_demand = _round_number(
        sum(feature.demand_dev_days for feature in delivered_features), precision
    )
    summary = [
        (
            f"The original roadmap required {original_demand_dev_days} dev days "
            f"against {capacity_dev_days} dev days of capacity."
        ),
        (
            f"The recommended alternative keeps {len(delivered_features)} features "
            f"and reduces demand to {recommended_demand} dev days."
        ),
    ]
    if removed_features:
        removed_names = ", ".join(feature.feature.name for feature in removed_features)
        summary.append(f"Removed scope: {removed_names}.")
    return summary


def plan_capacity(planning_input: PlanningInput, defaults: DefaultsConfig) -> dict[str, Any]:
    """Build a JSON-serializable planning result."""
    precision = defaults.output_precision
    engineers = _expand_engineers(planning_input, defaults)
    feature_demands = _feature_demands(planning_input, defaults)

    capacity_dev_days = _capacity_dev_days(planning_input, engineers, precision=precision)
    demand_dev_days = _demand_dev_days(feature_demands, precision=precision)
    utilization = _utilization(demand_dev_days, capacity_dev_days, precision=precision)
    buffer_dev_days = _buffer_dev_days(capacity_dev_days, demand_dev_days, precision=precision)
    feasibility = demand_dev_days <= capacity_dev_days

    delivered_features = list(feature_demands)
    removed_features: list[FeatureDemand] = []
    if not feasibility and defaults.improvement_passes > 0:
        delivered_features, removed_features = _recommend_scope_changes(
            feature_demands, capacity_dev_days, defaults
        )

    deferred_features = [
        feature.to_dict(precision=precision)
        for feature in removed_features
        if feature.feature.priority != "Low"
    ]
    dropped_features = [
        feature.to_dict(precision=precision)
        for feature in removed_features
        if feature.feature.priority == "Low"
    ]

    return {
        "capacity_dev_days": capacity_dev_days,
        "demand_dev_days": demand_dev_days,
        "utilization": utilization,
        "feasibility": feasibility,
        "buffer_dev_days": buffer_dev_days,
        "delivered_features": [
            feature.to_dict(precision=precision) for feature in delivered_features
        ],
        "deferred_features": deferred_features,
        "dropped_features": dropped_features,
        "risks": _build_risks(
            feasibility=feasibility,
            utilization=utilization,
            buffer_dev_days=buffer_dev_days,
            capacity_dev_days=capacity_dev_days,
            defaults=defaults,
        ),
        "suggestions": _build_suggestions(
            feasibility=feasibility,
            removed_features=removed_features,
            delivered_features=delivered_features,
            capacity_dev_days=capacity_dev_days,
            defaults=defaults,
            precision=precision,
        ),
        "tradeoff_summary": _build_tradeoff_summary(
            feasibility=feasibility,
            delivered_features=delivered_features,
            removed_features=removed_features,
            original_demand_dev_days=demand_dev_days,
            capacity_dev_days=capacity_dev_days,
            precision=precision,
        ),
    }
