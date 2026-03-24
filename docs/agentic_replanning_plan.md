# Agentic Replanning Plan

## Status

This document started as the design for the next iteration. The bounded replanning loop described here is now implemented. The remaining future work is optional LLM-backed candidate generation or narrative support.

## Why This Still Exists

The original spec asked for LLM usage to explain risks, suggest which features to defer or drop, and summarize tradeoffs while keeping calculations non-LLM. The current version now has the bounded runtime loop, but it still uses rule-based candidate generation and deterministic narrative output.

## Product Goal

Given:

- team capacity
- planning horizon
- roadmap demand
- explicit business goals

the tool should recommend the best acceptable plan, not just the first feasible trimmed plan.

## Example Business Goals

- Deliver features `1`, `5`, `7`, and `8` by the end of Q2
- Preserve all `Critical` features unless no feasible plan exists
- Keep utilization below `0.9`
- Preserve at least `10%` capacity buffer
- Prefer deferring internal work before customer-facing work
- Keep at least one growth feature in scope

## Implemented Input Extension

Add an optional JSON section like:

```json
{
  "business_goals": {
    "must_deliver_feature_ids": ["1", "5", "7", "8"],
    "preserve_priorities": ["Critical"],
    "max_utilization": 0.9,
    "min_buffer_ratio": 0.1,
    "defer_preference": ["Low", "Medium", "High", "Critical"]
  }
}
```

This shape is now implemented in spirit, with explicit machine-readable business goals.

## Implemented Architecture

### Deterministic Layer

Responsible for:

- parsing input JSON
- computing capacity and demand
- generating feature-level demand values
- evaluating candidate plans against feasibility, utilization, and buffer rules
- scoring candidate plans against business-goal constraints

### Agentic Layer

Responsible for:

- reading deterministic planner output
- proposing one or more scope alternatives
- deciding which features to defer or drop to satisfy business goals
- selecting better candidates across bounded iterations

### Guardrail

Every agent-proposed alternative must be re-evaluated by the deterministic layer before it can be returned.

## Implemented Agentic Loop

Use a bounded loop:

1. Compute the baseline plan deterministically.
2. If the baseline plan is acceptable, keep it.
3. Otherwise, generate candidate alternatives that respect the business goals.
4. Re-score each candidate deterministically.
5. Keep the best acceptable candidate.
6. Stop after a small fixed number of rounds or once no better candidate is found.

This is the implemented agentic pattern:

- propose
- evaluate
- revise
- stop

## Current Output Direction

The tool continues to emit JSON only and now includes fields such as:

- `selected_plan_reason`
- `evaluated_alternatives`
- `business_goal_assessment`
- `agentic_iterations`

## Non-Goals

The next iteration should still avoid:

- moving calculations into the LLM
- weekly or sprint-by-sprint scheduling allocation
- a UI or database layer
- open-ended autonomous behavior without bounded retries

## Remaining Future Work

1. Add an optional external LLM adapter without moving calculations into the model.
2. Let that adapter propose richer alternatives than single-feature removals.
3. Optionally let the adapter write `risks`, `suggestions`, and `tradeoff_summary`.
4. Keep deterministic rescoring as the final authority.
5. Add tests covering fallback behavior when the LLM is unavailable.
