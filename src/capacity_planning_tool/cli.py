"""CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from capacity_planning_tool.config import load_defaults
from capacity_planning_tool.models import InputValidationError, PlanningInput
from capacity_planning_tool.planner import plan_capacity


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capacity-plan",
        description="Evaluate capacity planning inputs and print JSON output.",
    )
    parser.add_argument("--input", required=True, help="Path to the input JSON file.")
    parser.add_argument(
        "--output",
        required=False,
        help="Optional path to write the output JSON. Defaults to stdout.",
    )
    return parser


def _read_input(path: Path) -> PlanningInput:
    with path.open("r", encoding="utf-8") as input_file:
        raw_input = json.load(input_file)
    defaults = load_defaults()
    return PlanningInput.from_dict(raw_input, defaults)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    try:
        defaults = load_defaults()
        planning_input = _read_input(input_path)
        result = plan_capacity(planning_input, defaults)
    except FileNotFoundError as error:
        parser.exit(status=1, message=f"{error}\n")
    except (InputValidationError, json.JSONDecodeError) as error:
        parser.exit(status=1, message=f"Invalid input: {error}\n")

    serialized = json.dumps(result, indent=2)
    if output_path is None:
        sys.stdout.write(serialized + "\n")
        return 0

    output_path.write_text(serialized + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
