# Agentic Replanning Plan

## Status

The bounded replanning loop is already shipped.

This document now exists only for the optional future LLM-backed advisor layer.

## Why This Still Exists

The original spec asked for LLM usage to explain risks, suggest which features to defer or drop, and summarize tradeoffs while keeping calculations non-LLM. The current version now has the bounded runtime loop, but it still uses rule-based candidate generation and deterministic narrative output.

## Future Goal

Keep the current deterministic planner, but add an optional advisor layer that can:

- explain risks with richer narrative
- propose broader alternatives than single-feature removals
- summarize tradeoffs in a more business-aware way

without ever replacing the deterministic evaluator.

## Guardrails

- do not move calculations into the LLM
- do not let the LLM become the final scoring authority
- keep bounded retries and explicit stop conditions
- keep the planner output JSON authoritative

## Remaining Future Work

1. Add an optional external LLM adapter without moving calculations into the model.
2. Let that adapter propose richer alternatives than single-feature removals.
3. Optionally let the adapter write `risks`, `suggestions`, and `tradeoff_summary`.
4. Keep deterministic rescoring as the final authority.
5. Add tests covering fallback behavior when the LLM is unavailable.
6. Keep this document focused on future work only; move shipped behavior into [`current_state.md`](current_state.md) or [`assumptions.md`](assumptions.md).
