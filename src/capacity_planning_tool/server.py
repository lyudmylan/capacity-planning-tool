"""Minimal Flask server that bridges the UI to the existing planner."""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import Flask, Response, jsonify, request, send_from_directory

from capacity_planning_tool.config import load_defaults, project_root
from capacity_planning_tool.models import InputValidationError, PlanningInput
from capacity_planning_tool.planner import plan_capacity

LOGGER = logging.getLogger(__name__)

UI_DIR = project_root() / "ui"
EXAMPLES_DIR = project_root() / "examples"


def create_app() -> Flask:
    """Build and return the Flask application."""
    app = Flask(__name__)

    @app.route("/")
    def index() -> Response:
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/assets/<path:asset_path>")
    def asset(asset_path: str) -> Response:
        return send_from_directory(str(UI_DIR), asset_path)

    @app.route("/api/plan", methods=["POST"])
    def run_planner() -> tuple[Response, int]:
        body = request.get_json(silent=True)
        if body is None:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        try:
            defaults = load_defaults()
            planning_input = PlanningInput.from_dict(body, defaults)
            result = plan_capacity(planning_input, defaults)
        except InputValidationError as exc:
            return jsonify({"error": str(exc)}), 422
        except Exception:
            LOGGER.exception("Unexpected planner error")
            return jsonify({"error": "Internal server error."}), 500
        return jsonify(result), 200

    @app.route("/api/examples", methods=["GET"])
    def list_examples() -> tuple[Response, int]:
        examples: list[dict[str, Any]] = []
        for path in sorted(EXAMPLES_DIR.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                examples.append({"name": path.stem, "data": json.load(f)})
        return jsonify(examples), 200

    return app


def main() -> None:
    """Run the development server."""
    import argparse

    parser = argparse.ArgumentParser(description="Capacity Planning UI server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=5000, help="Port number")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = create_app()
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
