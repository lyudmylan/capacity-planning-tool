import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Minimal HTML parser used by raw-JSON HTML regression tests
# ---------------------------------------------------------------------------

class _AttrCollector(HTMLParser):
    """Collects element IDs and data-tab buttons from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: dict[str, dict] = {}          # id -> {tag, attrs}
        self.tab_buttons: list[dict] = []       # elements with data-tab attr
        self.tab_bar_action_ids: list[str] = [] # IDs inside .tab-bar-actions divs
        self._in_tab_bar_actions = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attrs_d = dict(attrs)
        elem_id = attrs_d.get("id")
        if elem_id:
            self.ids[elem_id] = {"tag": tag, "attrs": attrs_d}
        if "data-tab" in attrs_d:
            self.tab_buttons.append({"tag": tag, **attrs_d})
        cls = attrs_d.get("class", "")
        if "tab-bar-actions" in cls:
            self._in_tab_bar_actions = True
        if self._in_tab_bar_actions and elem_id:
            self.tab_bar_action_ids.append(elem_id)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            self._in_tab_bar_actions = False


def _parse_html(path: Path) -> _AttrCollector:
    collector = _AttrCollector()
    collector.feed(path.read_text(encoding="utf-8"))
    return collector


class UiSpecTests(unittest.TestCase):
    def test_ui_handoff_spec_is_valid_json_with_required_contract_keys(self) -> None:
        spec_path = PROJECT_ROOT / "specs" / "ui_handoff_v1.json"
        with spec_path.open("r", encoding="utf-8") as spec_file:
            spec = json.load(spec_file)

        self.assertEqual(spec["spec_id"], "capacity-planning-ui-handoff")
        self.assertEqual(spec["spec_version"], "2.1")
        self.assertEqual(spec["delivery_model"]["preferred_ui_builder"], "Claude Code")
        self.assertEqual(spec["source_of_truth"]["product_doc"], "docs/product.md")
        self.assertEqual(
            spec["source_of_truth"]["planner_contract_tests"], "tests/test_server.py"
        )
        self.assertIn("human_web_interface", spec["delivery_model"]["interaction_modes"])
        self.assertEqual(
            spec["delivery_model"]["supported_planning_modes"],
            ["capacity_check", "planning_schedule"],
        )
        self.assertEqual(spec["delivery_model"]["target_scope"], "next_ui_iteration")
        self.assertEqual(
            spec["product_constraints"]["planner_calculations"],
            "deterministic_backend_only",
        )
        self.assertEqual(
            spec["product_constraints"]["frontend_calculation_policy"],
            "must_not_duplicate_planner_logic",
        )
        self.assertIn("preferred_ui_builder", spec["delivery_model"])
        self.assertIn("ui_surfaces", spec)
        self.assertIn("input_contract", spec)
        self.assertIn("information_architecture", spec)
        self.assertIn("mode_flows", spec)
        self.assertIn("validation_behavior", spec)
        self.assertIn("ui_state_model", spec)
        self.assertIn("field_presentation", spec)
        self.assertIn("claude_implementation_guidance", spec)
        self.assertIn("output_contract", spec)
        self.assertIn("design_preferences", spec)
        self.assertIn(
            "examples/v2_rd_org_capacity_check.json",
            spec["source_of_truth"]["planner_input_examples"],
        )
        self.assertIn(
            "examples/v2_function_estimates_capacity_check.json",
            spec["source_of_truth"]["planner_input_examples"],
        )
        self.assertEqual(
            spec["information_architecture"]["workspace_model"],
            "single_page_dual_workspace",
        )
        self.assertEqual(
            spec["information_architecture"]["regions"][1]["sections"],
            [
                "summary",
                "function_analysis",
                "scope_decision",
                "goal_and_dependency_review",
                "raw_output_json",
            ],
        )
        self.assertEqual(
            spec["mode_flows"][0]["comparison_model"], "baseline_vs_selected"
        )
        self.assertEqual(
            spec["mode_flows"][1]["comparison_model"], "selected_plan_primary"
        )
        self.assertIn(
            "normalize_period_selectors_on_horizon_change",
            spec["ui_surfaces"][0]["panels"][0]["capabilities"],
        )
        self.assertIn(
            "highlight_bottleneck_functions",
            spec["ui_surfaces"][0]["panels"][2]["capabilities"],
        )
        self.assertIn(
            "show_selected_plan_primary_for_planning_schedule",
            spec["ui_surfaces"][0]["panels"][3]["capabilities"],
        )
        self.assertEqual(
            spec["input_contract"]["v2_required_top_level_fields"],
            ["planning_mode", "rd_org", "roadmap"],
        )
        self.assertEqual(
            spec["input_contract"]["structured_editor_sections"][0]["primary_fields"],
            [
                "planning_mode",
                "planning_horizon",
                "calendar_year",
                "half_year_index",
                "quarter_index",
                "month_index",
                "start_date",
                "end_date",
            ],
        )
        self.assertIn(
            "run_disabled_when_input_is_invalid",
            spec["validation_behavior"]["interaction_rules"],
        )
        self.assertEqual(
            spec["ui_state_model"]["states"],
            [
                "pristine",
                "draft_loaded",
                "draft_dirty",
                "input_invalid",
                "ready_to_run",
                "running",
                "result_ready",
                "run_error",
            ],
        )
        self.assertEqual(
            spec["output_contract"]["capacity_check_top_level_fields"],
            [
                "planning_mode",
                "capacity_dev_days",
                "capacity_by_function",
                "baseline_plan",
                "selected_plan",
                "evaluated_alternatives",
                "agentic_iterations",
                "risks",
                "suggestions",
                "tradeoff_summary",
            ],
        )
        self.assertEqual(
            spec["output_contract"]["evaluated_plan_schedule_only_fields"],
            ["dependency_rules_pass", "dependency_violations"],
        )
        self.assertIn(
            "selected_plan.function_capacity_fit",
            spec["field_presentation"]["primary_output_fields"],
        )
        self.assertIn(
            "selected_plan.utilization_by_function",
            spec["field_presentation"]["secondary_output_fields"],
        )
        self.assertEqual(
            spec["claude_implementation_guidance"]["implementation_order"][0],
            "establish stable input workspace and editor synchronization",
        )

    # ------------------------------------------------------------------
    # Issue #76: tightened spec contract coverage
    # ------------------------------------------------------------------

    def _load_spec(self) -> dict:
        spec_path = PROJECT_ROOT / "specs" / "ui_handoff_v1.json"
        with spec_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def test_input_workspace_sections_match_spec(self) -> None:
        spec = self._load_spec()
        input_region = spec["information_architecture"]["regions"][0]
        self.assertEqual(input_region["id"], "input_workspace")
        self.assertEqual(
            input_region["sections"],
            [
                "example_loader",
                "mode_and_period",
                "capacity_controls",
                "organization",
                "roadmap",
                "business_goals",
                "raw_input_json",
            ],
        )

    def test_raw_json_panel_spec_lists_all_four_capabilities(self) -> None:
        spec = self._load_spec()
        panels = spec["ui_surfaces"][0]["panels"]
        json_panel = next(p for p in panels if p["id"] == "json_panel")
        caps = json_panel["capabilities"]
        for required in (
            "show_input_json", "show_output_json", "copy_output_json", "download_output_json"
        ):
            self.assertIn(required, caps, f"json_panel capability {required!r} missing from spec")

    def test_spec_interaction_rules_include_raw_json_escape_hatch(self) -> None:
        spec = self._load_spec()
        rules = spec["validation_behavior"]["interaction_rules"]
        self.assertIn("raw_json_editor_remains_available_as_fidelity_escape_hatch", rules)

    def test_planning_schedule_output_fields_include_dependency_keys(self) -> None:
        spec = self._load_spec()
        ps_fields = spec["output_contract"]["planning_schedule_top_level_fields"]
        self.assertIn("dependency_rules_pass", ps_fields)
        self.assertIn("dependency_violations", ps_fields)
        self.assertIn("function_capacity_fit", ps_fields)

    def test_spec_evaluated_plan_schedule_only_fields(self) -> None:
        spec = self._load_spec()
        self.assertEqual(
            spec["output_contract"]["evaluated_plan_schedule_only_fields"],
            ["dependency_rules_pass", "dependency_violations"],
        )

    def test_structured_editor_sections_cover_org_roadmap_goals(self) -> None:
        spec = self._load_spec()
        editor_sections = spec["input_contract"]["structured_editor_sections"]
        section_ids = [s["id"] for s in editor_sections]
        for required in ("organization", "schedule_policies", "roadmap", "business_goals"):
            self.assertIn(
                required, section_ids,
                f"structured_editor section {required!r} missing from spec",
            )

    def test_spec_org_section_primary_fields(self) -> None:
        spec = self._load_spec()
        editor_sections = spec["input_contract"]["structured_editor_sections"]
        org_section = next(s for s in editor_sections if s["id"] == "organization")
        for field in (
            "rd_org.teams[].name",
            "rd_org.teams[].members[].id",
            "rd_org.teams[].members[].function",
        ):
            self.assertIn(field, org_section["primary_fields"])

    def test_spec_schedule_policies_section_primary_fields(self) -> None:
        spec = self._load_spec()
        editor_sections = spec["input_contract"]["structured_editor_sections"]
        sp_section = next(s for s in editor_sections if s["id"] == "schedule_policies")
        self.assertIn(
            "rd_org.org_schedule_policies.post_dev_min_ratio.qa",
            sp_section["primary_fields"],
        )
        self.assertIn(
            "rd_org.org_schedule_policies.post_dev_min_ratio.devops",
            sp_section["primary_fields"],
        )

    def test_spec_capacity_check_comparison_model(self) -> None:
        spec = self._load_spec()
        cc_flow = spec["mode_flows"][0]
        self.assertEqual(cc_flow["mode"], "capacity_check")
        self.assertEqual(cc_flow["comparison_model"], "baseline_vs_selected")

    def test_spec_planning_schedule_comparison_model(self) -> None:
        spec = self._load_spec()
        ps_flow = spec["mode_flows"][1]
        self.assertEqual(ps_flow["mode"], "planning_schedule")
        self.assertEqual(ps_flow["comparison_model"], "selected_plan_primary")

    def test_spec_field_presentation_primary_includes_dependency_keys(self) -> None:
        spec = self._load_spec()
        primary = spec["field_presentation"]["primary_output_fields"]
        self.assertIn("dependency_rules_pass", primary)
        self.assertIn("dependency_violations", primary)
        self.assertIn("selected_plan.function_capacity_fit", primary)


class RawJsonHtmlRegressionTests(unittest.TestCase):
    """Regression tests for the raw JSON workflow added in issue #77."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = _parse_html(PROJECT_ROOT / "ui" / "index.html")

    # --- Input JSON tab: Copy and Download buttons exist ---

    def test_copy_input_button_exists(self) -> None:
        self.assertIn("copy-input-btn", self.html.ids)
        self.assertEqual(self.html.ids["copy-input-btn"]["tag"], "button")

    def test_download_input_button_exists(self) -> None:
        self.assertIn("download-input-btn", self.html.ids)
        self.assertEqual(self.html.ids["download-input-btn"]["tag"], "button")

    def test_input_copy_download_are_inside_tab_bar_actions(self) -> None:
        self.assertIn("copy-input-btn", self.html.tab_bar_action_ids)
        self.assertIn("download-input-btn", self.html.tab_bar_action_ids)

    # --- Output raw JSON panel: Copy and Download buttons exist ---

    def test_copy_output_button_exists(self) -> None:
        self.assertIn("copy-output-btn", self.html.ids)
        self.assertEqual(self.html.ids["copy-output-btn"]["tag"], "button")

    def test_download_output_button_exists(self) -> None:
        self.assertIn("download-output-btn", self.html.ids)
        self.assertEqual(self.html.ids["download-output-btn"]["tag"], "button")

    # --- Tab structure: input and output tabs exist ---

    def test_json_input_tab_content_exists(self) -> None:
        self.assertIn("json-tab", self.html.ids)

    def test_form_tab_content_exists(self) -> None:
        self.assertIn("form-tab", self.html.ids)

    def test_output_json_tab_content_exists(self) -> None:
        self.assertIn("output-json-tab", self.html.ids)

    def test_input_json_tab_content_exists(self) -> None:
        self.assertIn("input-json-tab", self.html.ids)

    # --- Tab bar buttons use data-tab attribute ---

    def test_json_tab_button_uses_data_tab(self) -> None:
        tab_ids = [b["data-tab"] for b in self.html.tab_buttons]
        self.assertIn("json-tab", tab_ids)

    def test_output_json_tab_button_uses_data_tab(self) -> None:
        tab_ids = [b["data-tab"] for b in self.html.tab_buttons]
        self.assertIn("output-json-tab", tab_ids)

    def test_input_json_tab_button_uses_data_tab(self) -> None:
        tab_ids = [b["data-tab"] for b in self.html.tab_buttons]
        self.assertIn("input-json-tab", tab_ids)

    # --- Download filename contract locked in JS source ---

    def test_input_download_filename_is_capacity_plan_input_json(self) -> None:
        js_text = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("capacity_plan_input.json", js_text)

    def test_output_download_filename_is_capacity_plan_output_json(self) -> None:
        js_text = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("capacity_plan_output.json", js_text)

    # --- Tab-aware copy/download: activeOutputJsonContent reads active tab state ---

    def test_active_output_json_content_function_present_in_js(self) -> None:
        js_text = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("activeOutputJsonContent", js_text)

    def test_output_panel_checks_input_json_tab_active_class(self) -> None:
        js_text = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("input-json-tab", js_text)
        # The JS must check classList for "active" to determine which tab is visible
        self.assertIn("classList.contains", js_text)

    # --- json-tab-actions element exists and carries correct id ---

    def test_json_tab_actions_element_exists(self) -> None:
        self.assertIn("json-tab-actions", self.html.ids)

    # --- Raw JSON panel subtitle exists ---

    def test_raw_json_panel_has_subtitle(self) -> None:
        html_text = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("panel-subtitle", html_text)

    # --- json_panel section exists ---

    def test_json_panel_section_exists(self) -> None:
        self.assertIn("json-panel", self.html.ids)
        self.assertEqual(self.html.ids["json-panel"]["tag"], "section")
