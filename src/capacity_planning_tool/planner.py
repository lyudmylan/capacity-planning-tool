"""Core capacity planning logic."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from capacity_planning_tool.models import (
    SUPPORTED_ESTIMATE_FUNCTIONS,
    DefaultsConfig,
    EngineerCapacity,
    FeatureDemand,
    InputValidationError,
    PlanningInput,
)

LOGGER = logging.getLogger(__name__)


def _round_number(value: float, precision: int) -> float:
    return round(value, precision)


@dataclass(frozen=True, slots=True)
class EvaluatedPlan:
    delivered_features: tuple[FeatureDemand, ...]
    removed_features: tuple[FeatureDemand, ...]
    demand_dev_days: float
    utilization: float
    buffer_dev_days: float
    demand_by_function: dict[str, float]
    utilization_by_function: dict[str, float | None]
    buffer_by_function: dict[str, float]
    function_capacity_fit: dict[str, bool]
    bottleneck_functions: tuple[str, ...]
    dependency_rules_pass: bool
    dependency_violations: tuple[str, ...]
    feasibility: bool
    acceptable: bool
    goal_compliant: bool
    business_goal_assessment: dict[str, Any]
    score: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class DependencyRuleEvaluation:
    eng_utilization: float
    blocked_demand_by_function: dict[str, float]
    blocked_utilization_by_function: dict[str, float]
    dependency_rules_pass: bool
    dependency_violations: tuple[str, ...]


def _expand_engineers(
    planning_input: PlanningInput, defaults: DefaultsConfig
) -> list[EngineerCapacity]:
    engineers: list[EngineerCapacity] = []
    for team in planning_input.teams:
        for role in team.roles:
            # Until function-aware capacity lands, downstream rd_org roles should not
            # inflate the legacy engineering-capacity calculation.
            if role.role in {"qa", "devops"}:
                continue
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
        demand_by_function = {
            function_name: 0.0 for function_name in SUPPORTED_ESTIMATE_FUNCTIONS
        }
        if feature.estimates is not None:
            for function_name in SUPPORTED_ESTIMATE_FUNCTIONS:
                size = getattr(feature.estimates, function_name)
                if (
                    function_name == "eng"
                    and size is None
                    and feature.size is not None
                ):
                    size = feature.size
                if size is None:
                    continue
                multiplier = defaults.feature_size_multipliers[size]
                demand_by_function[function_name] = effective_dev_days_per_sprint * multiplier
        elif feature.size is not None:
            multiplier = defaults.feature_size_multipliers[feature.size]
            demand_by_function["eng"] = effective_dev_days_per_sprint * multiplier
        else:
            raise InputValidationError("feature must define size or estimates.")

        feature_demands.append(
            FeatureDemand(
                feature=feature,
                demand_dev_days=demand_by_function["eng"],
                demand_by_function=demand_by_function,
                original_index=index,
            )
        )
    return feature_demands


def _demand_by_function(
    feature_demands: list[FeatureDemand], *, precision: int
) -> dict[str, float]:
    demand_totals = {function_name: 0.0 for function_name in SUPPORTED_ESTIMATE_FUNCTIONS}
    for feature_demand in feature_demands:
        for function_name, demand in feature_demand.demand_by_function.items():
            demand_totals[function_name] += demand
    return {
        function_name: _round_number(demand, precision)
        for function_name, demand in demand_totals.items()
    }


def _net_available_days(planning_input: PlanningInput) -> float:
    return (
        planning_input.working_days
        - planning_input.holidays_days
        - planning_input.vacation_days
        - planning_input.sick_days
    )


def _capacity_by_function(
    planning_input: PlanningInput, defaults: DefaultsConfig, *, precision: int
) -> dict[str, float]:
    net_days_per_member = _net_available_days(planning_input)
    capacity_totals = {function_name: 0.0 for function_name in SUPPORTED_ESTIMATE_FUNCTIONS}

    for team in planning_input.teams:
        for role in team.roles:
            if role.role in SUPPORTED_ESTIMATE_FUNCTIONS:
                function_name = role.role
            elif planning_input.rd_org is None:
                function_name = "eng"
            else:
                continue

            if role.members:
                for member in role.members:
                    capacity_totals[function_name] += (
                        net_days_per_member
                        * member.capacity_percent
                        * planning_input.focus_factor
                    )
                continue

            group_capacity = (
                role.capacity_percent
                if role.capacity_percent is not None
                else defaults.capacity_percent_default
            )
            engineer_count = role.count if role.count is not None else 0
            capacity_totals[function_name] += (
                net_days_per_member
                * group_capacity
                * engineer_count
                * planning_input.focus_factor
            )

    return {
        function_name: _round_number(total_capacity, precision)
        for function_name, total_capacity in capacity_totals.items()
    }


def _capacity_dev_days(
    planning_input: PlanningInput,
    engineer_capacities: list[EngineerCapacity],
    *,
    precision: int,
) -> float:
    net_days_per_engineer = _net_available_days(planning_input)
    total_capacity = sum(
        net_days_per_engineer * engineer.capacity_percent * planning_input.focus_factor
        for engineer in engineer_capacities
    )
    return _round_number(total_capacity, precision)


def _function_capacity_fit(
    demand_by_function: dict[str, float], capacity_by_function: dict[str, float]
) -> tuple[dict[str, bool], tuple[str, ...]]:
    capacity_fit = {
        function_name: demand_by_function[function_name] <= capacity_by_function[function_name]
        for function_name in SUPPORTED_ESTIMATE_FUNCTIONS
    }
    bottleneck_functions = tuple(
        function_name
        for function_name in SUPPORTED_ESTIMATE_FUNCTIONS
        if not capacity_fit[function_name]
    )
    return capacity_fit, bottleneck_functions


def _utilization_by_function(
    demand_by_function: dict[str, float],
    capacity_by_function: dict[str, float],
    *,
    precision: int,
) -> dict[str, float | None]:
    return {
        function_name: (
            utilization
            if math.isfinite(
                utilization := _utilization(
                    demand_by_function[function_name],
                    capacity_by_function[function_name],
                    precision=precision,
                )
            )
            else None
        )
        for function_name in SUPPORTED_ESTIMATE_FUNCTIONS
    }


def _buffer_by_function(
    demand_by_function: dict[str, float],
    capacity_by_function: dict[str, float],
    *,
    precision: int,
) -> dict[str, float]:
    return {
        function_name: _buffer_dev_days(
            capacity_by_function[function_name],
            demand_by_function[function_name],
            precision=precision,
        )
        for function_name in SUPPORTED_ESTIMATE_FUNCTIONS
    }


def _dependency_rule_evaluation(
    planning_input: PlanningInput,
    demand_by_function: dict[str, float],
    capacity_by_function: dict[str, float],
    *,
    precision: int,
) -> DependencyRuleEvaluation:
    empty_downstream = {"qa": 0.0, "devops": 0.0}
    if planning_input.planning_mode != "planning_schedule" or planning_input.rd_org is None:
        return DependencyRuleEvaluation(
            eng_utilization=0.0,
            blocked_demand_by_function=empty_downstream,
            blocked_utilization_by_function=empty_downstream,
            dependency_rules_pass=True,
            dependency_violations=(),
        )

    org_schedule_policies = planning_input.rd_org.org_schedule_policies
    post_dev_min_ratio = (
        None if org_schedule_policies is None else org_schedule_policies.post_dev_min_ratio
    )
    if post_dev_min_ratio is None:
        return DependencyRuleEvaluation(
            eng_utilization=0.0,
            blocked_demand_by_function=empty_downstream,
            blocked_utilization_by_function=empty_downstream,
            dependency_rules_pass=True,
            dependency_violations=(),
        )

    eng_utilization = _utilization(
        demand_by_function["eng"],
        capacity_by_function["eng"],
        precision=precision,
    )
    blocked_demand_by_function: dict[str, float] = {}
    blocked_utilization_by_function: dict[str, float] = {}
    dependency_violations: list[str] = []
    for function_name in ("qa", "devops"):
        ratio = getattr(post_dev_min_ratio, function_name)
        if ratio is None:
            blocked_demand = 0.0
        else:
            blocked_demand = _round_number(demand_by_function[function_name] * ratio, precision)
        blocked_demand_by_function[function_name] = blocked_demand

        blocked_utilization = _utilization(
            blocked_demand,
            capacity_by_function[function_name],
            precision=precision,
        )
        blocked_utilization_by_function[function_name] = blocked_utilization

        if eng_utilization + blocked_utilization > 1:
            dependency_violations.append(
                f"{function_name} dependency rule failed: eng_utilization "
                f"({eng_utilization}) + blocked_utilization_{function_name} "
                f"({blocked_utilization}) exceeds 1."
            )

    return DependencyRuleEvaluation(
        eng_utilization=eng_utilization,
        blocked_demand_by_function=blocked_demand_by_function,
        blocked_utilization_by_function=blocked_utilization_by_function,
        dependency_rules_pass=not dependency_violations,
        dependency_violations=tuple(dependency_violations),
    )


def _demand_dev_days(feature_demands: list[FeatureDemand], *, precision: int) -> float:
    return _round_number(sum(feature.demand_dev_days for feature in feature_demands), precision)


def _utilization(demand_dev_days: float, capacity_dev_days: float, *, precision: int) -> float:
    if capacity_dev_days == 0:
        return 0.0 if demand_dev_days == 0 else float("inf")
    return _round_number(demand_dev_days / capacity_dev_days, precision)


def _buffer_dev_days(capacity_dev_days: float, demand_dev_days: float, *, precision: int) -> float:
    return _round_number(capacity_dev_days - demand_dev_days, precision)


def _feature_priority_value(feature: FeatureDemand, defaults: DefaultsConfig) -> int:
    return defaults.priority_rank[feature.feature.priority]


def _serialize_feature_list(
    features: tuple[FeatureDemand, ...] | list[FeatureDemand], *, precision: int
) -> list[dict[str, Any]]:
    return [feature.to_dict(precision=precision) for feature in features]


def _build_business_goal_assessment(
    *,
    planning_input: PlanningInput,
    delivered_features: tuple[FeatureDemand, ...],
    removed_features: tuple[FeatureDemand, ...],
    utilization: float,
    buffer_dev_days: float,
    capacity_dev_days: float,
    defaults: DefaultsConfig,
) -> dict[str, Any]:
    precision = defaults.output_precision
    delivered_references = {feature.feature.reference for feature in delivered_features}
    missing_must_deliver = sorted(
        feature_id
        for feature_id in planning_input.business_goals.must_deliver_feature_ids
        if feature_id not in delivered_references
    )
    removed_preserved_features = sorted(
        feature.feature.reference
        for feature in removed_features
        if feature.feature.priority in planning_input.business_goals.preserve_priorities
    )
    utilization_within_goal = utilization <= planning_input.business_goals.max_utilization
    minimum_buffer = capacity_dev_days * planning_input.business_goals.min_buffer_ratio
    buffer_within_goal = buffer_dev_days >= minimum_buffer
    hard_constraint_violations: list[str] = []
    if missing_must_deliver:
        hard_constraint_violations.append(
            "Missing must-deliver features: " + ", ".join(missing_must_deliver)
        )
    if not utilization_within_goal:
        hard_constraint_violations.append(
            "Utilization exceeds the business-goal limit."
        )
    if not buffer_within_goal:
        hard_constraint_violations.append("Buffer is below the business-goal target.")

    soft_goal_violations: list[str] = []
    if removed_preserved_features:
        soft_goal_violations.append(
            "Removed preserved-priority features: " + ", ".join(removed_preserved_features)
        )

    acceptable = not hard_constraint_violations
    goal_compliant = acceptable and not soft_goal_violations
    return {
        "must_deliver_feature_ids": list(planning_input.business_goals.must_deliver_feature_ids),
        "missing_must_deliver_feature_ids": missing_must_deliver,
        "preserve_priorities": list(planning_input.business_goals.preserve_priorities),
        "removed_preserved_features": removed_preserved_features,
        "max_utilization": _round_number(planning_input.business_goals.max_utilization, precision),
        "min_buffer_ratio": _round_number(
            planning_input.business_goals.min_buffer_ratio, precision
        ),
        "utilization_within_goal": utilization_within_goal,
        "buffer_within_goal": buffer_within_goal,
        "hard_constraint_violations": hard_constraint_violations,
        "soft_goal_violations": soft_goal_violations,
        "acceptable": acceptable,
        "goal_compliant": goal_compliant,
    }


def _plan_score(
    *,
    acceptable: bool,
    goal_compliant: bool,
    business_goal_assessment: dict[str, Any],
    delivered_features: tuple[FeatureDemand, ...],
    removed_features: tuple[FeatureDemand, ...],
    utilization: float,
    buffer_dev_days: float,
    feasibility: bool,
    capacity_dev_days: float,
    defaults: DefaultsConfig,
    planning_input: PlanningInput,
) -> tuple[Any, ...]:
    delivered_priority_value = sum(
        _feature_priority_value(feature, defaults) for feature in delivered_features
    )
    utilization_gap = max(0.0, utilization - planning_input.business_goals.max_utilization)
    required_buffer = capacity_dev_days * planning_input.business_goals.min_buffer_ratio
    buffer_gap = max(0.0, required_buffer - buffer_dev_days)
    score_components: dict[str, Any] = {
        "acceptable": 1 if acceptable else 0,
        "goal_compliant": 1 if goal_compliant else 0,
        "feasible": 1 if feasibility else 0,
        "hard_constraint_violations": -len(
            business_goal_assessment["hard_constraint_violations"]
        ),
        "utilization_gap": -utilization_gap,
        "buffer_gap": -buffer_gap,
        "soft_goal_violations": -len(business_goal_assessment["soft_goal_violations"]),
        "delivered_priority_value": delivered_priority_value,
        "removed_feature_count": -len(removed_features),
    }
    return tuple(score_components[key] for key in defaults.plan_score_order)


def _evaluate_plan(
    *,
    planning_input: PlanningInput,
    delivered_features: tuple[FeatureDemand, ...],
    all_feature_demands: tuple[FeatureDemand, ...],
    capacity_dev_days: float,
    capacity_by_function: dict[str, float],
    defaults: DefaultsConfig,
) -> EvaluatedPlan:
    precision = defaults.output_precision
    removed_features = tuple(
        feature
        for feature in all_feature_demands
        if feature.original_index not in {item.original_index for item in delivered_features}
    )
    demand_by_function = _demand_by_function(list(delivered_features), precision=precision)
    utilization_by_function = _utilization_by_function(
        demand_by_function,
        capacity_by_function,
        precision=precision,
    )
    buffer_by_function = _buffer_by_function(
        demand_by_function,
        capacity_by_function,
        precision=precision,
    )
    function_capacity_fit, bottleneck_functions = _function_capacity_fit(
        demand_by_function,
        capacity_by_function,
    )
    dependency_evaluation = _dependency_rule_evaluation(
        planning_input,
        demand_by_function,
        capacity_by_function,
        precision=precision,
    )
    demand_dev_days = _demand_dev_days(list(delivered_features), precision=precision)
    utilization = _utilization(demand_dev_days, capacity_dev_days, precision=precision)
    buffer_dev_days = _buffer_dev_days(capacity_dev_days, demand_dev_days, precision=precision)
    dependency_rules_pass = dependency_evaluation.dependency_rules_pass
    feasibility = all(function_capacity_fit.values()) and dependency_rules_pass
    business_goal_assessment = _build_business_goal_assessment(
        planning_input=planning_input,
        delivered_features=delivered_features,
        removed_features=removed_features,
        utilization=utilization,
        buffer_dev_days=buffer_dev_days,
        capacity_dev_days=capacity_dev_days,
        defaults=defaults,
    )
    acceptable = feasibility and business_goal_assessment["acceptable"]
    goal_compliant = feasibility and business_goal_assessment["goal_compliant"]
    return EvaluatedPlan(
        delivered_features=delivered_features,
        removed_features=removed_features,
        demand_dev_days=demand_dev_days,
        utilization=utilization,
        buffer_dev_days=buffer_dev_days,
        demand_by_function=demand_by_function,
        utilization_by_function=utilization_by_function,
        buffer_by_function=buffer_by_function,
        function_capacity_fit=function_capacity_fit,
        bottleneck_functions=bottleneck_functions,
        dependency_rules_pass=dependency_rules_pass,
        dependency_violations=dependency_evaluation.dependency_violations,
        feasibility=feasibility,
        acceptable=acceptable,
        goal_compliant=goal_compliant,
        business_goal_assessment=business_goal_assessment,
        score=_plan_score(
            acceptable=acceptable,
            goal_compliant=goal_compliant,
            business_goal_assessment=business_goal_assessment,
            delivered_features=delivered_features,
            removed_features=removed_features,
            utilization=utilization,
            buffer_dev_days=buffer_dev_days,
            feasibility=feasibility,
            capacity_dev_days=capacity_dev_days,
            defaults=defaults,
            planning_input=planning_input,
        ),
    )


def _removable_features(
    evaluated_plan: EvaluatedPlan,
    planning_input: PlanningInput,
    defaults: DefaultsConfig,
) -> list[FeatureDemand]:
    defer_rank = {
        priority: index
        for index, priority in enumerate(planning_input.business_goals.defer_preference)
    }
    removable = [
        feature
        for feature in evaluated_plan.delivered_features
        if feature.feature.reference not in planning_input.business_goals.must_deliver_feature_ids
    ]
    candidate_keys: dict[str, Callable[[FeatureDemand], Any]] = {
        "preserved_priority": lambda feature: (
            feature.feature.priority in planning_input.business_goals.preserve_priorities
        ),
        "defer_preference": lambda feature: defer_rank[feature.feature.priority],
        "demand_desc": lambda feature: -feature.demand_dev_days,
        "original_index": lambda feature: feature.original_index,
    }
    return sorted(
        removable,
        key=lambda feature: tuple(
            candidate_keys[key](feature) for key in defaults.candidate_sort_order
        ),
    )


def _serialize_evaluated_plan(
    evaluated_plan: EvaluatedPlan,
    *,
    capacity_dev_days: float,
    capacity_by_function: dict[str, float],
    precision: int,
) -> dict[str, Any]:
    return {
        "capacity_dev_days": capacity_dev_days,
        "demand_dev_days": evaluated_plan.demand_dev_days,
        "utilization": evaluated_plan.utilization,
        "capacity_by_function": capacity_by_function,
        "demand_by_function": evaluated_plan.demand_by_function,
        "utilization_by_function": evaluated_plan.utilization_by_function,
        "buffer_by_function": evaluated_plan.buffer_by_function,
        "function_capacity_fit": evaluated_plan.function_capacity_fit,
        "bottleneck_functions": list(evaluated_plan.bottleneck_functions),
        "dependency_rules_pass": evaluated_plan.dependency_rules_pass,
        "dependency_violations": list(evaluated_plan.dependency_violations),
        "feasibility": evaluated_plan.feasibility,
        "buffer_dev_days": evaluated_plan.buffer_dev_days,
        "acceptable": evaluated_plan.acceptable,
        "goal_compliant": evaluated_plan.goal_compliant,
        "delivered_features": _serialize_feature_list(
            evaluated_plan.delivered_features, precision=precision
        ),
        "deferred_features": [
            feature.to_dict(precision=precision)
            for feature in evaluated_plan.removed_features
            if feature.feature.priority != "Low"
        ],
        "dropped_features": [
            feature.to_dict(precision=precision)
            for feature in evaluated_plan.removed_features
            if feature.feature.priority == "Low"
        ],
        "business_goal_assessment": evaluated_plan.business_goal_assessment,
    }


def _run_agentic_replanning_loop(
    *,
    planning_input: PlanningInput,
    all_feature_demands: tuple[FeatureDemand, ...],
    capacity_dev_days: float,
    capacity_by_function: dict[str, float],
    defaults: DefaultsConfig,
) -> tuple[EvaluatedPlan, list[dict[str, Any]], list[dict[str, Any]]]:
    precision = defaults.output_precision
    LOGGER.info(
        "Starting replanning loop with max_iterations=%s candidate_limit=%s",
        defaults.agentic_max_iterations,
        defaults.agentic_candidate_limit,
    )
    current_plan = _evaluate_plan(
        planning_input=planning_input,
        delivered_features=all_feature_demands,
        all_feature_demands=all_feature_demands,
        capacity_dev_days=capacity_dev_days,
        capacity_by_function=capacity_by_function,
        defaults=defaults,
    )
    best_plan = current_plan
    all_alternatives: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []

    for iteration in range(defaults.agentic_max_iterations):
        if current_plan.goal_compliant:
            LOGGER.info(
                (
                    "Stopping replanning early at iteration %s because "
                    "the current plan is goal compliant"
                ),
                iteration + 1,
            )
            break

        removable = _removable_features(current_plan, planning_input, defaults)
        if not removable:
            LOGGER.warning(
                "Stopping replanning at iteration %s because no removable features remain",
                iteration + 1,
            )
            iterations.append(
                {
                    "iteration": iteration + 1,
                    "status": "stopped",
                    "reason": "No removable features remain after must-deliver protection.",
                }
            )
            break

        candidates = removable[: defaults.agentic_candidate_limit]
        evaluated_candidates: list[tuple[FeatureDemand, EvaluatedPlan]] = []
        for feature_to_remove in candidates:
            next_delivered = tuple(
                feature
                for feature in current_plan.delivered_features
                if feature.original_index != feature_to_remove.original_index
            )
            candidate_plan = _evaluate_plan(
                planning_input=planning_input,
                delivered_features=next_delivered,
                all_feature_demands=all_feature_demands,
                capacity_dev_days=capacity_dev_days,
                capacity_by_function=capacity_by_function,
                defaults=defaults,
            )
            evaluated_candidates.append((feature_to_remove, candidate_plan))
            all_alternatives.append(
                {
                    "iteration": iteration + 1,
                    "removed_feature": feature_to_remove.to_dict(precision=precision),
                    "plan": _serialize_evaluated_plan(
                        candidate_plan,
                        capacity_dev_days=capacity_dev_days,
                        capacity_by_function=capacity_by_function,
                        precision=precision,
                    ),
                }
            )

        selected_feature, selected_plan = max(
            evaluated_candidates,
            key=lambda item: item[1].score,
        )
        LOGGER.info(
            "Iteration %s selected removal of %s with score %s",
            iteration + 1,
            selected_feature.feature.reference,
            selected_plan.score,
        )
        iterations.append(
            {
                "iteration": iteration + 1,
                "status": "selected",
                "selected_removed_feature": selected_feature.to_dict(precision=precision),
                "selected_plan": _serialize_evaluated_plan(
                    selected_plan,
                    capacity_dev_days=capacity_dev_days,
                    capacity_by_function=capacity_by_function,
                    precision=precision,
                ),
                "evaluated_candidates": [
                    {
                        "removed_feature": feature.to_dict(precision=precision),
                        "plan": _serialize_evaluated_plan(
                            candidate,
                            capacity_dev_days=capacity_dev_days,
                            capacity_by_function=capacity_by_function,
                            precision=precision,
                        ),
                    }
                    for feature, candidate in evaluated_candidates
                ],
            }
        )
        if selected_plan.score <= current_plan.score:
            LOGGER.info(
                "Stopping replanning at iteration %s because no better candidate was found",
                iteration + 1,
            )
            iterations.append(
                {
                    "iteration": iteration + 1,
                    "status": "stopped",
                    "reason": "No better candidate was found.",
                }
            )
            break
        current_plan = selected_plan
        if selected_plan.score > best_plan.score:
            best_plan = selected_plan

    LOGGER.info(
        "Completed replanning with selected demand=%s utilization=%s removed_features=%s",
        best_plan.demand_dev_days,
        best_plan.utilization,
        len(best_plan.removed_features),
    )
    return best_plan, all_alternatives, iterations


def _build_risks(
    *,
    baseline_feasibility: bool,
    baseline_utilization: float,
    baseline_buffer_dev_days: float,
    capacity_dev_days: float,
    selected_plan: EvaluatedPlan,
    defaults: DefaultsConfig,
) -> list[str]:
    risks: list[str] = []
    if not baseline_feasibility:
        risks.append("Roadmap demand exceeds available capacity for the selected horizon.")
    if baseline_utilization > defaults.utilization_target_max:
        risks.append(
            "Utilization is above the target range, leaving little room for interruptions."
        )
    if 0 <= baseline_utilization < defaults.utilization_target_min:
        risks.append(
            "Utilization is below the target range, which may indicate under-committed capacity."
        )
    if baseline_buffer_dev_days < capacity_dev_days * defaults.buffer_target_ratio:
        risks.append("Buffer is below the target threshold, increasing delivery risk.")
    risks.extend(selected_plan.dependency_violations)
    risks.extend(selected_plan.business_goal_assessment["hard_constraint_violations"])
    risks.extend(selected_plan.business_goal_assessment["soft_goal_violations"])
    return risks


def _build_suggestions(
    *,
    baseline_feasibility: bool,
    selected_plan: EvaluatedPlan,
    capacity_dev_days: float,
    defaults: DefaultsConfig,
) -> list[str]:
    if not baseline_feasibility and not selected_plan.removed_features:
        return [
            (
                "Adjust staffing, scope, or schedule policy assumptions to satisfy "
                "planning constraints."
            )
        ]

    if not baseline_feasibility and selected_plan.removed_features:
        return [
            "Reduce scope using the recommended delivered feature set.",
            (
                f"The recommended plan brings demand to {selected_plan.demand_dev_days} dev days "
                f"at {selected_plan.utilization} utilization."
            ),
        ]

    suggestions: list[str] = []
    current_utilization = selected_plan.utilization
    if current_utilization > defaults.utilization_target_max:
        suggestions.append("Defer the lowest-priority feature to rebuild delivery buffer.")
    if 0 <= current_utilization < defaults.utilization_target_min:
        suggestions.append("Pull in more roadmap work if a higher utilization target is desired.")
    if selected_plan.business_goal_assessment["missing_must_deliver_feature_ids"]:
        suggestions.append(
            "Increase capacity or relax must-deliver constraints to reach an acceptable plan."
        )
    if selected_plan.business_goal_assessment["removed_preserved_features"]:
        suggestions.append(
            "Review preserved-priority tradeoffs because some protected work was deferred."
        )
    if not suggestions:
        suggestions.append("Current scope is aligned with the available capacity targets.")
    return suggestions


def _build_tradeoff_summary(
    *,
    baseline_feasibility: bool,
    selected_plan: EvaluatedPlan,
    original_demand_dev_days: float,
    capacity_dev_days: float,
) -> list[str]:
    if baseline_feasibility and selected_plan.goal_compliant:
        return [
            "The original roadmap fits within available capacity and satisfies the business goals."
        ]

    if not baseline_feasibility and not selected_plan.removed_features:
        return [
            (
                "The current roadmap does not satisfy the planning constraints for the selected "
                "horizon."
            )
        ]

    summary = [
        (
            f"The original roadmap required {original_demand_dev_days} dev days "
            f"against {capacity_dev_days} dev days of capacity."
        ),
        (
            f"The selected alternative keeps {len(selected_plan.delivered_features)} features "
            f"and reduces demand to {selected_plan.demand_dev_days} dev days."
        ),
    ]
    if selected_plan.removed_features:
        removed_names = ", ".join(
            feature.feature.name for feature in selected_plan.removed_features
        )
        summary.append(f"Removed scope: {removed_names}.")
    if selected_plan.goal_compliant:
        summary.append(
            "The selected plan satisfies both the hard constraints and soft business goals."
        )
    elif selected_plan.acceptable:
        summary.append(
            "The selected plan is acceptable but required tradeoffs against soft business goals."
        )
    else:
        summary.append(
            "No acceptable plan satisfied the hard business constraints with current capacity."
        )
    return summary


def plan_capacity(planning_input: PlanningInput, defaults: DefaultsConfig) -> dict[str, Any]:
    """Build a JSON-serializable planning result."""
    precision = defaults.output_precision
    engineers = _expand_engineers(planning_input, defaults)
    feature_demands = tuple(_feature_demands(planning_input, defaults))

    capacity_dev_days = _capacity_dev_days(planning_input, engineers, precision=precision)
    capacity_by_function = _capacity_by_function(planning_input, defaults, precision=precision)
    baseline_plan = _evaluate_plan(
        planning_input=planning_input,
        delivered_features=feature_demands,
        all_feature_demands=feature_demands,
        capacity_dev_days=capacity_dev_days,
        capacity_by_function=capacity_by_function,
        defaults=defaults,
    )

    demand_dev_days = baseline_plan.demand_dev_days
    utilization = baseline_plan.utilization
    buffer_dev_days = baseline_plan.buffer_dev_days
    function_capacity_fit = baseline_plan.function_capacity_fit
    bottleneck_functions = baseline_plan.bottleneck_functions
    dependency_rules_pass = baseline_plan.dependency_rules_pass
    dependency_violations = baseline_plan.dependency_violations
    feasibility = baseline_plan.feasibility

    if planning_input.planning_mode == "planning_schedule":
        selected_plan = baseline_plan
        evaluated_alternatives: list[dict[str, Any]] = []
        agentic_iterations: list[dict[str, Any]] = []
    else:
        selected_plan, evaluated_alternatives, agentic_iterations = _run_agentic_replanning_loop(
            planning_input=planning_input,
            all_feature_demands=feature_demands,
            capacity_dev_days=capacity_dev_days,
            capacity_by_function=capacity_by_function,
            defaults=defaults,
        )

    return {
        "capacity_dev_days": capacity_dev_days,
        "demand_dev_days": demand_dev_days,
        "utilization": utilization,
        "capacity_by_function": capacity_by_function,
        "demand_by_function": baseline_plan.demand_by_function,
        "utilization_by_function": baseline_plan.utilization_by_function,
        "buffer_by_function": baseline_plan.buffer_by_function,
        "function_capacity_fit": function_capacity_fit,
        "bottleneck_functions": list(bottleneck_functions),
        "dependency_rules_pass": dependency_rules_pass,
        "dependency_violations": list(dependency_violations),
        "feasibility": feasibility,
        "buffer_dev_days": buffer_dev_days,
        "delivered_features": _serialize_feature_list(
            selected_plan.delivered_features, precision=precision
        ),
        "deferred_features": [
            feature.to_dict(precision=precision)
            for feature in selected_plan.removed_features
            if feature.feature.priority != "Low"
        ],
        "dropped_features": [
            feature.to_dict(precision=precision)
            for feature in selected_plan.removed_features
            if feature.feature.priority == "Low"
        ],
        "selected_plan": _serialize_evaluated_plan(
            selected_plan,
            capacity_dev_days=capacity_dev_days,
            capacity_by_function=capacity_by_function,
            precision=precision,
        ),
        "business_goal_assessment": selected_plan.business_goal_assessment,
        "evaluated_alternatives": evaluated_alternatives,
        "agentic_iterations": agentic_iterations,
        "risks": _build_risks(
            baseline_feasibility=feasibility,
            baseline_utilization=utilization,
            baseline_buffer_dev_days=buffer_dev_days,
            capacity_dev_days=capacity_dev_days,
            selected_plan=selected_plan,
            defaults=defaults,
        ),
        "suggestions": _build_suggestions(
            baseline_feasibility=feasibility,
            selected_plan=selected_plan,
            capacity_dev_days=capacity_dev_days,
            defaults=defaults,
        ),
        "tradeoff_summary": _build_tradeoff_summary(
            baseline_feasibility=feasibility,
            selected_plan=selected_plan,
            original_demand_dev_days=demand_dev_days,
            capacity_dev_days=capacity_dev_days,
        ),
    }
