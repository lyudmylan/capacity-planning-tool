"""Configuration loading."""

from __future__ import annotations

import json
from pathlib import Path

from capacity_planning_tool.models import DefaultsConfig


def project_root() -> Path:
    """Return the repository root when running from a source checkout."""
    return Path(__file__).resolve().parents[2]


def defaults_path() -> Path:
    """Return the default config path."""
    return project_root() / "config" / "defaults.json"


def load_defaults() -> DefaultsConfig:
    """Load runtime defaults from JSON config."""
    with defaults_path().open("r", encoding="utf-8") as defaults_file:
        raw_defaults = json.load(defaults_file)
    return DefaultsConfig.from_dict(raw_defaults)
