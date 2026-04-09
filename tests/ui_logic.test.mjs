import test from "node:test";
import assert from "node:assert/strict";

import {
  applyEditableFieldsToPayload,
  buildFunctionAnalysisModel,
  buildPeriodSource,
  buildPlanComparison,
  buildStructuredFormState,
  buildSummaryModel,
  getUtilizationStatus,
  readEditableFieldsFromPayload,
  validateInputPayload,
} from "../ui/app.js";

test("readEditableFieldsFromPayload reflects pasted JSON values", () => {
  const editableFields = readEditableFieldsFromPayload({
    planning_mode: "capacity_check",
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 2,
    working_days: 220,
    holidays_days: 12,
    vacation_days: 18,
    sick_days: 4,
    focus_factor: 0.9,
    sprint_days: 15,
    overhead_days_per_sprint: 3,
  });

  assert.deepEqual(editableFields, {
    planning_mode: "capacity_check",
    planning_horizon: "quarter",
    calendar_year: 2026,
    half_year_index: "",
    quarter_index: 2,
    month_index: "",
    start_date: "",
    end_date: "",
    working_days: 220,
    holidays_days: 12,
    vacation_days: 18,
    sick_days: 4,
    focus_factor: 0.9,
    sprint_days: 15,
    overhead_days_per_sprint: 3,
  });
});

test("readEditableFieldsFromPayload includes sprint period selectors when present", () => {
  const editableFields = readEditableFieldsFromPayload({
    planning_mode: "planning_schedule",
    planning_horizon: "sprint",
    start_date: "2026-06-01",
    end_date: "2026-06-14",
  });

  assert.equal(editableFields.planning_mode, "planning_schedule");
  assert.equal(editableFields.start_date, "2026-06-01");
  assert.equal(editableFields.end_date, "2026-06-14");
  assert.equal(editableFields.calendar_year, "");
});

test("buildStructuredFormState keeps absent period selectors blank", () => {
  const formState = buildStructuredFormState({
    planning_mode: "capacity_check",
    planning_horizon: "quarter",
    calendar_year: 2026,
    half_year_index: "",
    quarter_index: 3,
    month_index: "",
    start_date: "",
    end_date: "",
  });

  assert.equal(formState.planning_mode, "capacity_check");
  assert.equal(formState.planning_horizon, "quarter");
  assert.equal(formState.calendar_year, "2026");
  assert.equal(formState.half_year_index, "");
  assert.equal(formState.quarter_index, "3");
  assert.equal(formState.month_index, "");
});

test("applyEditableFieldsToPayload preserves unrelated pasted JSON values", () => {
  const original = {
    planning_horizon: "year",
    calendar_year: 2025,
    month_index: 2,
    working_days: 220,
    holidays_days: 12,
    vacation_days: 18,
    sick_days: 4,
    focus_factor: 0.9,
    sprint_days: 15,
    overhead_days_per_sprint: 3,
    roadmap: {
      features: [
        {id: "feature-1", name: "Launch", size: "L", priority: "Critical"},
      ],
    },
    business_goals: {
      must_deliver_feature_ids: ["feature-1"],
    },
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "quarter",
    working_days: "60",
    holidays_days: "2",
    vacation_days: "5",
    sick_days: "1",
    focus_factor: "0.8",
    sprint_days: "10",
    overhead_days_per_sprint: "2",
  });

  assert.equal(updated.planning_horizon, "quarter");
  assert.equal(updated.working_days, 60);
  assert.equal(updated.focus_factor, 0.8);
  assert.equal(updated.calendar_year, 2025);
  assert.equal(updated.quarter_index, 1);
  assert.equal(updated.month_index, undefined);
  assert.equal(updated.start_date, undefined);
  assert.equal(updated.end_date, undefined);
  assert.deepEqual(updated.roadmap, original.roadmap);
  assert.deepEqual(updated.business_goals, original.business_goals);
});

test("applyEditableFieldsToPayload seeds required selectors when horizon changes to sprint", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 3,
    roadmap: {
      features: [],
    },
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "sprint",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.planning_horizon, "sprint");
  assert.equal(updated.calendar_year, undefined);
  assert.equal(updated.quarter_index, undefined);
  assert.equal(updated.start_date, "2026-07-01");
  assert.equal(updated.end_date, "2026-07-14");
});

test("applyEditableFieldsToPayload retains existing sprint dates when switching within sprint", () => {
  const original = {
    planning_horizon: "sprint",
    start_date: "2026-05-05",
    end_date: "2026-05-19",
    roadmap: {
      features: [],
    },
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "sprint",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.start_date, "2026-05-05");
  assert.equal(updated.end_date, "2026-05-19");
});

test("applyEditableFieldsToPayload sets planning_mode from form value", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 1,
    roadmap: {features: []},
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_mode: "planning_schedule",
    planning_horizon: "quarter",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.planning_mode, "planning_schedule");
  assert.equal(updated.planning_horizon, "quarter");
});

test("applyEditableFieldsToPayload uses explicit calendar_year from form", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2025,
    quarter_index: 1,
    roadmap: {features: []},
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "quarter",
    calendar_year: "2027",
    quarter_index: "3",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.calendar_year, 2027);
  assert.equal(updated.quarter_index, 3);
});

test("applyEditableFieldsToPayload uses explicit sprint dates from form", () => {
  const original = {
    planning_horizon: "sprint",
    start_date: "2026-01-01",
    end_date: "2026-01-14",
    roadmap: {features: []},
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "sprint",
    start_date: "2026-09-01",
    end_date: "2026-09-14",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.start_date, "2026-09-01");
  assert.equal(updated.end_date, "2026-09-14");
});

test("applyEditableFieldsToPayload ignores empty-string period selector form values", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 2,
    roadmap: {features: []},
  };

  // Empty string calendar_year should fall back to inferring from source
  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "quarter",
    calendar_year: "",
    quarter_index: "",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.calendar_year, 2026);
  assert.equal(updated.quarter_index, 2);
});

test("applyEditableFieldsToPayload infers month from existing quarter when month selector is blank", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 3,
    roadmap: {features: []},
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "month",
    calendar_year: "2026",
    month_index: "",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.calendar_year, 2026);
  assert.equal(updated.month_index, 7);
});

test("validateInputPayload returns invalid with no error for empty input", () => {
  const result = validateInputPayload("");
  assert.equal(result.valid, false);
  assert.equal(result.error, null);
});

test("validateInputPayload returns invalid with error for malformed JSON", () => {
  const result = validateInputPayload("{bad json}");
  assert.equal(result.valid, false);
  assert.ok(result.error.startsWith("Invalid JSON:"));
});

test("validateInputPayload returns invalid with error for JSON array", () => {
  const result = validateInputPayload("[1,2,3]");
  assert.equal(result.valid, false);
  assert.ok(result.error.includes("array"));
});

test("validateInputPayload returns valid for a well-formed JSON object", () => {
  const result = validateInputPayload(JSON.stringify({planning_horizon: "quarter", roadmap: {features: []}}));
  assert.equal(result.valid, true);
  assert.equal(result.error, null);
});

test("getUtilizationStatus matches planner target semantics", () => {
  assert.equal(getUtilizationStatus(0.22), "warning");
  assert.equal(getUtilizationStatus(0.8), "feasible");
  assert.equal(getUtilizationStatus(0.9), "feasible");
  assert.equal(getUtilizationStatus(0.91), "infeasible");
});

test("buildPlanComparison highlights selected-plan changes against the original roadmap", () => {
  const comparison = buildPlanComparison(
    {
      roadmap: {
        features: [
          {name: "Billing", size: "L", priority: "Critical"},
          {name: "Export", size: "M", priority: "High"},
          {name: "Theme Refresh", size: "L", priority: "Low"},
        ],
      },
    },
    {
      baseline_plan: {
        demand_dev_days: 88,
        utilization: 1.06,
        buffer_dev_days: -4.8,
      },
      dropped_features: [{name: "Theme Refresh"}],
      selected_plan: {
        demand_dev_days: 64,
        utilization: 0.77,
        buffer_dev_days: 19.2,
        delivered_features: [
          {name: "Billing"},
          {name: "Export"},
        ],
        deferred_features: [],
        dropped_features: [{name: "Theme Refresh"}],
      },
    }
  );

  assert.equal(comparison.original_feature_count, 3);
  assert.equal(comparison.selected_delivered_count, 2);
  assert.equal(comparison.removed_feature_count, 1);
  assert.deepEqual(comparison.removed_feature_names, ["Theme Refresh"]);
  assert.equal(comparison.demand_delta_dev_days, -24);
  assert.equal(comparison.demand_delta_tone, "better");
  assert.equal(comparison.delivered_delta_tone, "worse");
  assert.equal(comparison.buffer_delta_tone, "better");
  assert.equal(comparison.utilization_delta_tone, "better");
  assert.equal(comparison.changed, true);
});

test("buildSummaryModel centers the selected feasible plan for capacity_check", () => {
  const summary = buildSummaryModel({
    planning_mode: "capacity_check",
    capacity_dev_days: 80,
    baseline_plan: {
      feasibility: false,
      demand_dev_days: 88,
      utilization: 1.1,
      buffer_dev_days: -8,
      bottleneck_functions: ["qa"],
    },
    selected_plan: {
      feasibility: true,
      demand_dev_days: 64,
      utilization: 0.8,
      buffer_dev_days: 16,
      delivered_features: [{name: "Billing"}],
      deferred_features: [],
      dropped_features: [{name: "Theme Refresh"}],
      bottleneck_functions: [],
    },
  });

  assert.equal(summary.bannerText, "Selected plan is feasible");
  assert.equal(summary.demandDevDays, 64);
  assert.equal(summary.deliveredCount, 1);
  assert.equal(summary.droppedCount, 1);
});

test("buildSummaryModel explains dependency-rule schedule failures", () => {
  const summary = buildSummaryModel({
    planning_mode: "planning_schedule",
    capacity_dev_days: 80,
    feasibility: false,
    demand_dev_days: 60,
    utilization: 0.75,
    buffer_dev_days: 20,
    delivered_features: [],
    deferred_features: [],
    dropped_features: [],
    dependency_rules_pass: false,
    bottleneck_functions: [],
  });

  assert.equal(summary.bannerText, "Plan is infeasible — dependency rules fail");
});

test("buildFunctionAnalysisModel extracts per-function metrics from selected_plan", () => {
  const model = buildFunctionAnalysisModel({
    planning_mode: "capacity_check",
    capacity_dev_days: 100,
    selected_plan: {
      capacity_by_function: {eng: 70, qa: 30},
      demand_by_function: {eng: 60, qa: 35},
      utilization_by_function: {eng: 0.86, qa: 1.17},
      buffer_by_function: {eng: 10, qa: -5},
      bottleneck_functions: ["qa"],
    },
  });

  assert.equal(model.rows.length, 2);
  assert.equal(model.hasBottlenecks, true);
  assert.deepEqual(model.bottleneckFunctions, ["qa"]);

  const qaRow = model.rows.find((r) => r.name === "qa");
  assert.ok(qaRow, "qa row should exist");
  assert.equal(qaRow.isBottleneck, true);
  assert.equal(qaRow.utilization, 1.17);
  assert.equal(qaRow.buffer, -5);

  const engRow = model.rows.find((r) => r.name === "eng");
  assert.ok(engRow, "eng row should exist");
  assert.equal(engRow.isBottleneck, false);
  assert.equal(engRow.capacity, 70);
});

test("buildFunctionAnalysisModel falls back to top-level fields when selected_plan is absent", () => {
  const model = buildFunctionAnalysisModel({
    planning_mode: "planning_schedule",
    capacity_by_function: {eng: 80, qa: 40, devops: 20},
    demand_by_function: {eng: 72, qa: 36, devops: 18},
    utilization_by_function: {eng: 0.9, qa: 0.9, devops: 0.9},
    buffer_by_function: {eng: 8, qa: 4, devops: 2},
    bottleneck_functions: [],
  });

  assert.equal(model.rows.length, 3);
  assert.equal(model.hasBottlenecks, false);
  assert.deepEqual(model.bottleneckFunctions, []);

  const devopsRow = model.rows.find((r) => r.name === "devops");
  assert.ok(devopsRow, "devops row should exist");
  assert.equal(devopsRow.capacity, 20);
  assert.equal(devopsRow.demand, 18);
  assert.equal(devopsRow.utilization, 0.9);
});

test("readEditableFieldsFromPayload reads planning_mode and all period selectors from payload", () => {
  const fields = readEditableFieldsFromPayload({
    planning_mode: "planning_schedule",
    planning_horizon: "quarter",
    calendar_year: 2026,
    half_year_index: 1,
    quarter_index: 2,
    month_index: 4,
    start_date: "2026-04-01",
    end_date: "2026-04-14",
  });

  assert.equal(fields.planning_mode, "planning_schedule");
  assert.equal(fields.calendar_year, 2026);
  assert.equal(fields.half_year_index, 1);
  assert.equal(fields.quarter_index, 2);
  assert.equal(fields.month_index, 4);
  assert.equal(fields.start_date, "2026-04-01");
  assert.equal(fields.end_date, "2026-04-14");
});

test("applyEditableFieldsToPayload propagates planning_mode when switching modes", () => {
  const original = {
    planning_mode: "capacity_check",
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 1,
    roadmap: {features: []},
  };

  const updated = applyEditableFieldsToPayload(original, {
    planning_mode: "planning_schedule",
    planning_horizon: "quarter",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.planning_mode, "planning_schedule");
});

test("applyEditableFieldsToPayload uses form-provided quarter_index instead of inferring it", () => {
  const original = {
    planning_horizon: "quarter",
    calendar_year: 2026,
    quarter_index: 1,
    month_index: 2,
    roadmap: {features: []},
  };

  // Form explicitly selects Q3, overriding the Q1 in the original payload
  const updated = applyEditableFieldsToPayload(original, {
    planning_horizon: "quarter",
    calendar_year: "2026",
    quarter_index: "3",
    working_days: "",
    holidays_days: "",
    vacation_days: "",
    sick_days: "",
    focus_factor: "",
    sprint_days: "",
    overhead_days_per_sprint: "",
  });

  assert.equal(updated.quarter_index, 3);
  assert.equal(updated.calendar_year, 2026);
  // month_index not present for quarter horizon
  assert.equal(updated.month_index, undefined);
});
