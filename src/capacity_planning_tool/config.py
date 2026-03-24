"""Configuration loading."""

from __future__ import annotations

import json
from pathlib import Path

from capacity_planning_tool.models import DefaultsConfig, InputValidationError


def project_root() -> Path:
    """Return the repository root when running from a source checkout."""
    return Path(__file__).resolve().parents[2]


def defaults_path() -> Path:
    """Return the default config path."""
    return project_root() / "config" / "defaults.json"


def load_defaults() -> DefaultsConfig:
    """Load runtime defaults from JSON config."""
    defaults_file_path = defaults_path()
    try:
        with defaults_file_path.open("r", encoding="utf-8") as defaults_file:
            raw_defaults = json.load(defaults_file)
    except FileNotFoundError as error:
        raise InputValidationError(
            f"Defaults config file was not found: {defaults_file_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise InputValidationError(
            f"Defaults config file contains invalid JSON: {error}"
        ) from error
    except OSError as error:
        raise InputValidationError(
            f"Defaults config file could not be read: {error}"
        ) from error
    return DefaultsConfig.from_dict(raw_defaults)
