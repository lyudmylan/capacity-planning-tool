# Assumptions and Formulas

## Scope

V1 evaluates a single planning horizon at a time. It does not split work by week, by sprint assignment, or by engineer specialization.

## Input Assumptions

- `planning_horizon` must be one of `year`, `half_year`, `quarter`, `month`, or `sprint`.
- `working_days` is provided directly for the selected planning horizon.
- Teams are modeled as role groups.
- A role group must define either:
  - `count`, or
  - `members`
- `capacity_percent` can be set at the role-group level or on individual members.
- If a member omits `capacity_percent`, the role-group value is used.
- If both omit it, the default from `config/defaults.json` is used.

## Demand Formula

- `effective_dev_days_per_sprint = sprint_days - overhead_days_per_sprint`
- `XS = effective_dev_days_per_sprint / 2`
- `S = effective_dev_days_per_sprint`
- `M = effective_dev_days_per_sprint * 2`
- `L = effective_dev_days_per_sprint * 3`

The implementation stores the size multipliers in `config/defaults.json` and multiplies them by `effective_dev_days_per_sprint`.

## Capacity Formula

- `net_days_per_engineer = working_days - holidays_days - vacation_days - sick_days`
- `effective_capacity_per_engineer = net_days_per_engineer * capacity_percent * focus_factor`
- `total_capacity = sum(effective capacity across engineers)`

## Evaluation Rules

- The original plan is considered feasible when `demand_dev_days <= capacity_dev_days`.
- Healthy utilization is targeted between `0.8` and `0.9`.
- Healthy buffer is targeted at `10%` or more of total capacity.

## Recommendation Logic

If the original roadmap is not feasible, V1 performs one improvement pass.

Features are removed in this order:

1. Lowest priority first
2. Largest feature first within the same priority
3. Original input order as the final tie-breaker

The recommendation aims to bring the plan down to the healthier limit implied by the configured utilization and buffer targets.

## Deferred vs Dropped

- Removed `Low` priority items are classified as `dropped_features`.
- Removed `Medium`, `High`, and `Critical` items are classified as `deferred_features`.

This keeps the output deterministic while still distinguishing low-value scope cuts from work that should move to a later horizon.
