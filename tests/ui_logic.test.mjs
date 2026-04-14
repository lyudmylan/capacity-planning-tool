import test from "node:test";
import assert from "node:assert/strict";

import {
  applyBusinessGoalsToPayload,
  applyEditableFieldsToPayload,
  applyOrgToPayload,
  applyRoadmapFeaturesToPayload,
  applySchedulePolicyToPayload,
  buildFunctionAnalysisModel,
  buildModeAwareSummaryContext,
  buildPeriodSource,
  buildPlanComparison,
  buildStructuredFormState,
  buildSummaryModel,
  getUtilizationStatus,
  readBusinessGoalsFromPayload,
  readEditableFieldsFromPayload,
  readOrgFromPayload,
  readRoadmapFeaturesFromPayload,
  readSchedulePolicyFromPayload,
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

// --- buildModeAwareSummaryContext ---

test("buildModeAwareSummaryContext returns baseline_vs_selected framing for capacity_check", () => {
  const ctx = buildModeAwareSummaryContext({
    planning_mode: "capacity_check",
    baseline_plan: {feasibility: false},
    selected_plan: {feasibility: true},
  });

  assert.equal(ctx.planningMode, "capacity_check");
  assert.equal(ctx.comparisonModel, "baseline_vs_selected");
  assert.equal(ctx.showBaselineComparison, true);
  assert.ok(ctx.primaryQuestion.length > 0);
});

test("buildModeAwareSummaryContext returns selected_plan_primary framing for planning_schedule", () => {
  const ctx = buildModeAwareSummaryContext({
    planning_mode: "planning_schedule",
    dependency_rules_pass: true,
    selected_plan: {feasibility: true},
  });

  assert.equal(ctx.planningMode, "planning_schedule");
  assert.equal(ctx.comparisonModel, "selected_plan_primary");
  assert.equal(ctx.showBaselineComparison, false);
  assert.ok(ctx.primaryQuestion.length > 0);
});

test("buildModeAwareSummaryContext showBaselineComparison is false when no baseline_plan", () => {
  const ctx = buildModeAwareSummaryContext({
    planning_mode: "capacity_check",
  });

  assert.equal(ctx.comparisonModel, "baseline_vs_selected");
  assert.equal(ctx.showBaselineComparison, false);
});

test("buildModeAwareSummaryContext capacity_check and planning_schedule have distinct primary questions", () => {
  const ccCtx = buildModeAwareSummaryContext({planning_mode: "capacity_check"});
  const psCtx = buildModeAwareSummaryContext({planning_mode: "planning_schedule"});

  assert.notEqual(ccCtx.primaryQuestion, psCtx.primaryQuestion);
});

// --- buildSummaryModel mode-aware fields ---

test("buildSummaryModel returns dependencyRulesPass from top-level field for planning_schedule", () => {
  const summary = buildSummaryModel({
    planning_mode: "planning_schedule",
    capacity_dev_days: 80,
    feasibility: true,
    dependency_rules_pass: true,
    delivered_features: [],
    deferred_features: [],
    dropped_features: [],
  });

  assert.equal(summary.dependencyRulesPass, true);
});

test("buildSummaryModel returns dependencyRulesPass false when dependency rules fail", () => {
  const summary = buildSummaryModel({
    planning_mode: "planning_schedule",
    capacity_dev_days: 80,
    feasibility: false,
    dependency_rules_pass: false,
    bottleneck_functions: [],
    delivered_features: [],
    deferred_features: [],
    dropped_features: [],
  });

  assert.equal(summary.dependencyRulesPass, false);
});

test("buildSummaryModel returns dependencyRulesPass null when field is absent (capacity_check)", () => {
  const summary = buildSummaryModel({
    planning_mode: "capacity_check",
    capacity_dev_days: 80,
    baseline_plan: {feasibility: false},
    selected_plan: {
      feasibility: true,
      delivered_features: [],
      deferred_features: [],
      dropped_features: [],
    },
  });

  assert.equal(summary.dependencyRulesPass, null);
});

test("buildSummaryModel returns functionCapacityFit from selected_plan", () => {
  const summary = buildSummaryModel({
    planning_mode: "planning_schedule",
    capacity_dev_days: 80,
    selected_plan: {
      feasibility: true,
      function_capacity_fit: {eng: true, qa: false},
      delivered_features: [],
      deferred_features: [],
      dropped_features: [],
    },
  });

  assert.deepEqual(summary.functionCapacityFit, {eng: true, qa: false});
});

test("buildSummaryModel returns empty functionCapacityFit when absent", () => {
  const summary = buildSummaryModel({
    planning_mode: "capacity_check",
    capacity_dev_days: 80,
    selected_plan: {
      feasibility: true,
      delivered_features: [],
      deferred_features: [],
      dropped_features: [],
    },
  });

  assert.deepEqual(summary.functionCapacityFit, {});
});

// --- buildFunctionAnalysisModel fits field ---

test("buildFunctionAnalysisModel includes fits per row from function_capacity_fit", () => {
  const model = buildFunctionAnalysisModel({
    planning_mode: "planning_schedule",
    capacity_by_function: {eng: 80, qa: 40},
    demand_by_function: {eng: 72, qa: 44},
    utilization_by_function: {eng: 0.9, qa: 1.1},
    buffer_by_function: {eng: 8, qa: -4},
    bottleneck_functions: ["qa"],
    function_capacity_fit: {eng: true, qa: false},
  });

  const engRow = model.rows.find((r) => r.name === "eng");
  const qaRow = model.rows.find((r) => r.name === "qa");

  assert.equal(engRow.fits, true);
  assert.equal(qaRow.fits, false);
});

test("buildFunctionAnalysisModel fits is null when function_capacity_fit is absent", () => {
  const model = buildFunctionAnalysisModel({
    planning_mode: "capacity_check",
    selected_plan: {
      capacity_by_function: {eng: 70},
      demand_by_function: {eng: 60},
      utilization_by_function: {eng: 0.86},
      buffer_by_function: {eng: 10},
      bottleneck_functions: [],
    },
  });

  const engRow = model.rows.find((r) => r.name === "eng");
  assert.equal(engRow.fits, null);
});

// --- readOrgFromPayload / applyOrgToPayload ---

test("readOrgFromPayload extracts teams with members and typed country profile values", () => {
  const data = {
    rd_org: {
      teams: [{
        name: "Core Product",
        members: [
          {id: "eng-1", function: "eng", seniority: "Senior", country_profile: "us"},
          {id: "qa-1", function: "qa", seniority: "Mid", capacity_percent: 0.5, country_profile: "us"},
        ],
      }],
      country_profiles: [{id: "us", country_code: "US", vacation_days_per_employee: 18, sick_days_per_employee: 8}],
    },
  };
  const org = readOrgFromPayload(data);
  assert.equal(org.teams.length, 1);
  assert.equal(org.teams[0].name, "Core Product");
  assert.equal(org.teams[0].members[0].id, "eng-1");
  assert.equal(org.teams[0].members[0].capacity_percent, "");
  assert.equal(org.teams[0].members[1].capacity_percent, "0.5");
  assert.equal(org.country_profiles[0].vacation_days_per_employee, 18);
  assert.equal(org.country_profiles[0].sick_days_per_employee, 8);
});

test("readOrgFromPayload returns empty arrays when rd_org is absent", () => {
  const org = readOrgFromPayload({});
  assert.deepEqual(org.teams, []);
  assert.deepEqual(org.country_profiles, []);
});

test("applyOrgToPayload round-trips teams and country profiles", () => {
  const data = {
    rd_org: {
      teams: [{
        name: "Core Product",
        members: [{id: "eng-1", function: "eng", seniority: "Senior", country_profile: "us"}],
      }],
      country_profiles: [{id: "us", country_code: "US", vacation_days_per_employee: 18, sick_days_per_employee: 8}],
    },
  };
  const org = readOrgFromPayload(data);
  const result = applyOrgToPayload(data, org);
  assert.equal(result.rd_org.teams[0].name, "Core Product");
  assert.equal(result.rd_org.teams[0].members[0].id, "eng-1");
  assert.equal(result.rd_org.country_profiles[0].id, "us");
  assert.equal(result.rd_org.country_profiles[0].vacation_days_per_employee, 18);
});

test("applyOrgToPayload preserves unknown rd_org fields (e.g. org_schedule_policies)", () => {
  const data = {
    rd_org: {
      org_schedule_policies: {post_dev_min_ratio: {qa: 0.4}},
      teams: [{name: "T", members: [{id: "m1", function: "eng", seniority: "Senior", country_profile: "us"}]}],
      country_profiles: [],
    },
  };
  const org = readOrgFromPayload(data);
  const result = applyOrgToPayload(data, org);
  assert.deepEqual(result.rd_org.org_schedule_policies, {post_dev_min_ratio: {qa: 0.4}});
});

test("applyOrgToPayload preserves unknown member fields via id matching", () => {
  const data = {
    rd_org: {
      teams: [{
        name: "T",
        members: [{id: "eng-1", function: "eng", seniority: "Senior", country_profile: "us", custom_tag: "alpha"}],
      }],
      country_profiles: [],
    },
  };
  const org = readOrgFromPayload(data);
  const result = applyOrgToPayload(data, org);
  assert.equal(result.rd_org.teams[0].members[0].custom_tag, "alpha");
});

test("applyOrgToPayload omits capacity_percent when form value is empty", () => {
  const data = {
    rd_org: {
      teams: [{
        name: "T",
        members: [{id: "m1", function: "eng", seniority: "Senior", country_profile: "us"}],
      }],
      country_profiles: [],
    },
  };
  const org = readOrgFromPayload(data);
  const result = applyOrgToPayload(data, org);
  assert.equal("capacity_percent" in result.rd_org.teams[0].members[0], false);
});

// --- readSchedulePolicyFromPayload / applySchedulePolicyToPayload ---

test("readSchedulePolicyFromPayload extracts qa and devops ratios as typed numbers", () => {
  const data = {
    rd_org: {org_schedule_policies: {post_dev_min_ratio: {qa: 0.4, devops: 0.3}}},
  };
  const policy = readSchedulePolicyFromPayload(data);
  assert.equal(policy.qa, 0.4);
  assert.equal(policy.devops, 0.3);
});

test("readSchedulePolicyFromPayload returns nulls when absent", () => {
  const policy = readSchedulePolicyFromPayload({});
  assert.equal(policy.qa, null);
  assert.equal(policy.devops, null);
});

test("applySchedulePolicyToPayload round-trips schedule policies for planning_schedule", () => {
  const data = {
    planning_mode: "planning_schedule",
    rd_org: {org_schedule_policies: {post_dev_min_ratio: {qa: 0.4, devops: 0.4}}, teams: []},
  };
  const policy = readSchedulePolicyFromPayload(data);
  const result = applySchedulePolicyToPayload(data, policy);
  assert.equal(result.rd_org.org_schedule_policies.post_dev_min_ratio.qa, 0.4);
  assert.equal(result.rd_org.org_schedule_policies.post_dev_min_ratio.devops, 0.4);
});

test("applySchedulePolicyToPayload preserves unknown rd_org fields", () => {
  const data = {
    planning_mode: "planning_schedule",
    rd_org: {
      org_schedule_policies: {post_dev_min_ratio: {qa: 0.4}, other_policy: "keep"},
      teams: [{name: "T", members: []}],
    },
  };
  const result = applySchedulePolicyToPayload(data, {qa: 0.4, devops: 0.3});
  assert.equal(result.rd_org.org_schedule_policies.other_policy, "keep");
  assert.equal(result.rd_org.teams[0].name, "T");
});

test("applySchedulePolicyToPayload removes key when typed value is null", () => {
  const data = {
    planning_mode: "planning_schedule",
    rd_org: {org_schedule_policies: {post_dev_min_ratio: {qa: 0.4, devops: 0.4}}, teams: []},
  };
  const result = applySchedulePolicyToPayload(data, {qa: 0.4, devops: null});
  assert.equal(result.rd_org.org_schedule_policies.post_dev_min_ratio.qa, 0.4);
  assert.equal("devops" in result.rd_org.org_schedule_policies.post_dev_min_ratio, false);
});

// --- readRoadmapFeaturesFromPayload / applyRoadmapFeaturesToPayload ---

test("readRoadmapFeaturesFromPayload extracts features with per-function estimates", () => {
  const data = {
    roadmap: {
      features: [{id: "f1", name: "Feature One", priority: "High", estimates: {eng: "M", qa: "S", devops: "XS"}}],
    },
  };
  const features = readRoadmapFeaturesFromPayload(data);
  assert.equal(features.length, 1);
  assert.equal(features[0].id, "f1");
  assert.deepEqual(features[0].estimates, {eng: "M", qa: "S", devops: "XS"});
  assert.equal(features[0].size, "");
});

test("readRoadmapFeaturesFromPayload extracts top-level size field", () => {
  const data = {
    roadmap: {features: [{id: "f1", name: "Feature One", priority: "Critical", size: "L"}]},
  };
  const features = readRoadmapFeaturesFromPayload(data);
  assert.equal(features[0].size, "L");
  assert.deepEqual(features[0].estimates, {});
});

test("readRoadmapFeaturesFromPayload returns empty array when roadmap absent", () => {
  assert.deepEqual(readRoadmapFeaturesFromPayload({}), []);
});

test("applyRoadmapFeaturesToPayload round-trips features with estimates", () => {
  const data = {
    roadmap: {
      features: [{id: "f1", name: "Feature One", priority: "High", estimates: {eng: "M", qa: "S"}}],
    },
  };
  const features = readRoadmapFeaturesFromPayload(data);
  const result = applyRoadmapFeaturesToPayload(data, features);
  assert.equal(result.roadmap.features[0].id, "f1");
  assert.equal(result.roadmap.features[0].estimates.eng, "M");
  assert.equal(result.roadmap.features[0].estimates.qa, "S");
  assert.equal("devops" in result.roadmap.features[0].estimates, false);
});

test("applyRoadmapFeaturesToPayload preserves unknown feature fields via id matching", () => {
  const data = {
    roadmap: {
      features: [{id: "f1", name: "F", priority: "High", estimates: {eng: "M"}, dependencies: ["f0"]}],
    },
  };
  const features = readRoadmapFeaturesFromPayload(data);
  const result = applyRoadmapFeaturesToPayload(data, features);
  assert.deepEqual(result.roadmap.features[0].dependencies, ["f0"]);
});

test("applyRoadmapFeaturesToPayload preserves unknown roadmap fields", () => {
  const data = {
    roadmap: {
      features: [{id: "f1", name: "A", priority: "High", estimates: {eng: "S"}}],
      version: "2.0",
    },
  };
  const features = readRoadmapFeaturesFromPayload(data);
  const result = applyRoadmapFeaturesToPayload(data, features);
  assert.equal(result.roadmap.version, "2.0");
});

// --- readBusinessGoalsFromPayload / applyBusinessGoalsToPayload ---

test("readBusinessGoalsFromPayload returns must-deliver ids as typed array", () => {
  const data = {
    business_goals: {
      must_deliver_feature_ids: ["f1", "f2"],
      max_utilization: 0.85,
      min_buffer_ratio: 0.1,
    },
  };
  const goals = readBusinessGoalsFromPayload(data);
  assert.deepEqual(goals.must_deliver_feature_ids, ["f1", "f2"]);
  assert.equal(goals.max_utilization, 0.85);
  assert.equal(goals.min_buffer_ratio, 0.1);
});

test("readBusinessGoalsFromPayload returns defaults when absent", () => {
  const goals = readBusinessGoalsFromPayload({});
  assert.deepEqual(goals.must_deliver_feature_ids, []);
  assert.equal(goals.max_utilization, null);
  assert.equal(goals.min_buffer_ratio, null);
});

test("applyBusinessGoalsToPayload round-trips business goals", () => {
  const data = {
    business_goals: {
      must_deliver_feature_ids: ["f1", "f2"],
      max_utilization: 0.85,
      min_buffer_ratio: 0.1,
    },
  };
  const goals = readBusinessGoalsFromPayload(data);
  const result = applyBusinessGoalsToPayload(data, goals);
  assert.deepEqual(result.business_goals.must_deliver_feature_ids, ["f1", "f2"]);
  assert.equal(result.business_goals.max_utilization, 0.85);
  assert.equal(result.business_goals.min_buffer_ratio, 0.1);
});

test("applyBusinessGoalsToPayload preserves unknown business_goals fields", () => {
  const data = {
    business_goals: {
      must_deliver_feature_ids: ["f1"],
      max_utilization: 0.9,
      preserve_priorities: true,
      defer_preference: "low",
    },
  };
  const goals = readBusinessGoalsFromPayload(data);
  const result = applyBusinessGoalsToPayload(data, goals);
  assert.equal(result.business_goals.preserve_priorities, true);
  assert.equal(result.business_goals.defer_preference, "low");
});

test("applyBusinessGoalsToPayload handles empty must-deliver input", () => {
  const data = {business_goals: {must_deliver_feature_ids: ["f1"]}};
  const result = applyBusinessGoalsToPayload(data, {
    must_deliver_feature_ids: [],
    max_utilization: null,
    min_buffer_ratio: null,
  });
  assert.deepEqual(result.business_goals.must_deliver_feature_ids, []);
  assert.equal("max_utilization" in result.business_goals, false);
  assert.equal("min_buffer_ratio" in result.business_goals, false);
});

// --- Structured editor helpers ---

// Teams and members

test("readOrgFromPayload reads teams and members from rd_org", () => {
  const data = {
    planning_mode: "capacity_check",
    rd_org: {
      country_profiles: [{id: "us", country_code: "US"}],
      teams: [
        {
          name: "Core Product",
          members: [
            {id: "eng-1", function: "eng", seniority: "Senior", country_profile: "us"},
            {id: "qa-1", function: "qa", seniority: "Mid", country_profile: "us"},
          ],
        },
      ],
    },
  };

  const org = readOrgFromPayload(data);

  assert.equal(org.teams.length, 1);
  assert.equal(org.teams[0].name, "Core Product");
  assert.equal(org.teams[0].members.length, 2);
  assert.equal(org.teams[0].members[0].id, "eng-1");
  assert.equal(org.teams[0].members[1].function, "qa");
});

test("readOrgFromPayload returns empty arrays when rd_org is absent", () => {
  const org = readOrgFromPayload({planning_mode: "capacity_check"});

  assert.deepEqual(org.teams, []);
  assert.deepEqual(org.country_profiles, []);
});

test("applyOrgToPayload writes teams back and preserves org_schedule_policies", () => {
  const original = {
    planning_mode: "planning_schedule",
    rd_org: {
      org_schedule_policies: {post_dev_min_ratio: {qa: 0.4, devops: 0.4}},
      country_profiles: [{id: "il", country_code: "IL"}],
      teams: [{name: "Old Team", members: []}],
    },
  };

  const orgState = {
    teams: [{name: "New Team", members: [{id: "eng-1", function: "eng", seniority: "Senior", country_profile: "il"}]}],
    country_profiles: [{id: "il", country_code: "IL"}],
  };

  const updated = applyOrgToPayload(original, orgState);

  assert.equal(updated.rd_org.teams.length, 1);
  assert.equal(updated.rd_org.teams[0].name, "New Team");
  assert.deepEqual(updated.rd_org.org_schedule_policies, {post_dev_min_ratio: {qa: 0.4, devops: 0.4}});
  assert.equal(updated.planning_mode, "planning_schedule");
});

test("applyOrgToPayload seeds empty rd_org when absent", () => {
  const original = {planning_mode: "capacity_check"};

  const orgState = {
    teams: [{name: "Alpha", members: []}],
    country_profiles: [],
  };

  const updated = applyOrgToPayload(original, orgState);

  assert.ok(updated.rd_org);
  assert.equal(updated.rd_org.teams[0].name, "Alpha");
  assert.deepEqual(updated.rd_org.country_profiles, []);
});

// Country profiles

test("readOrgFromPayload reads country_profiles with all fields", () => {
  const data = {
    rd_org: {
      country_profiles: [
        {
          id: "us",
          country_code: "US",
          working_day_rules: {workweek: "mon-fri"},
          holiday_calendar_rules: {dates: ["2026-07-04"]},
          vacation_days_per_employee: 18,
          sick_days_per_employee: 8,
        },
      ],
      teams: [],
    },
  };

  const org = readOrgFromPayload(data);

  assert.equal(org.country_profiles.length, 1);
  assert.equal(org.country_profiles[0].id, "us");
  assert.equal(org.country_profiles[0].country_code, "US");
  assert.equal(org.country_profiles[0].vacation_days_per_employee, 18);
  assert.deepEqual(org.country_profiles[0].working_day_rules, {workweek: "mon-fri"});
});

test("applyOrgToPayload round-trips country_profiles without loss", () => {
  const profiles = [
    {
      id: "us",
      country_code: "US",
      working_day_rules: {workweek: "mon-fri"},
      holiday_calendar_rules: {dates: ["2026-07-04"]},
      vacation_days_per_employee: 18,
      sick_days_per_employee: 8,
    },
  ];
  const original = {rd_org: {country_profiles: profiles, teams: []}};

  const org = readOrgFromPayload(original);
  const updated = applyOrgToPayload(original, org);

  assert.deepEqual(updated.rd_org.country_profiles, profiles);
});

// Schedule policy

test("readSchedulePolicyFromPayload reads post_dev_min_ratio for planning_schedule", () => {
  const data = {
    planning_mode: "planning_schedule",
    rd_org: {
      org_schedule_policies: {
        post_dev_min_ratio: {qa: 0.4, devops: 0.3},
      },
      teams: [],
      country_profiles: [],
    },
  };

  const policy = readSchedulePolicyFromPayload(data);

  assert.equal(policy.qa, 0.4);
  assert.equal(policy.devops, 0.3);
});

test("readSchedulePolicyFromPayload returns nulls when policy is absent", () => {
  const policy = readSchedulePolicyFromPayload({planning_mode: "capacity_check"});

  assert.equal(policy.qa, null);
  assert.equal(policy.devops, null);
});

test("applySchedulePolicyToPayload writes post_dev_min_ratio for planning_schedule", () => {
  const original = {
    planning_mode: "planning_schedule",
    rd_org: {
      teams: [],
      country_profiles: [],
    },
  };

  const updated = applySchedulePolicyToPayload(original, {qa: 0.4, devops: 0.5});

  assert.equal(updated.rd_org.org_schedule_policies.post_dev_min_ratio.qa, 0.4);
  assert.equal(updated.rd_org.org_schedule_policies.post_dev_min_ratio.devops, 0.5);
  assert.deepEqual(updated.rd_org.teams, []);
});

test("applySchedulePolicyToPayload preserves existing org_schedule_policies fields", () => {
  const original = {
    planning_mode: "planning_schedule",
    rd_org: {
      org_schedule_policies: {
        post_dev_min_ratio: {qa: 0.3, devops: 0.3},
        extra_policy: "keep_me",
      },
      teams: [],
      country_profiles: [],
    },
  };

  const updated = applySchedulePolicyToPayload(original, {qa: 0.5, devops: 0.5});

  assert.equal(updated.rd_org.org_schedule_policies.extra_policy, "keep_me");
  assert.equal(updated.rd_org.org_schedule_policies.post_dev_min_ratio.qa, 0.5);
});

test("applySchedulePolicyToPayload removes org_schedule_policies for capacity_check", () => {
  const original = {
    planning_mode: "capacity_check",
    rd_org: {
      teams: [],
      country_profiles: [],
      org_schedule_policies: {post_dev_min_ratio: {qa: 0.4, devops: 0.4}},
    },
  };

  const updated = applySchedulePolicyToPayload(original, {qa: 0.4, devops: 0.4});

  assert.equal(updated.rd_org.org_schedule_policies, undefined);
  assert.deepEqual(updated.rd_org.teams, []);
  assert.deepEqual(updated.rd_org.country_profiles, []);
});

// Roadmap feature estimates

test("readRoadmapFeaturesFromPayload reads features with function estimates", () => {
  const data = {
    roadmap: {
      features: [
        {id: "f-1", name: "Auth", priority: "High", estimates: {eng: "M", qa: "S"}},
        {id: "f-2", name: "Export", priority: "Low", estimates: {eng: "L", devops: "XS"}},
      ],
    },
  };

  const features = readRoadmapFeaturesFromPayload(data);

  assert.equal(features.length, 2);
  assert.equal(features[0].id, "f-1");
  assert.deepEqual(features[0].estimates, {eng: "M", qa: "S"});
  assert.equal(features[1].estimates.devops, "XS");
});

test("readRoadmapFeaturesFromPayload returns empty array when roadmap is absent", () => {
  const features = readRoadmapFeaturesFromPayload({});

  assert.deepEqual(features, []);
});

test("applyRoadmapFeaturesToPayload writes features preserving other roadmap fields", () => {
  const original = {
    roadmap: {
      features: [{id: "f-1", name: "Old", priority: "Low", estimates: {eng: "S"}}],
      roadmap_version: "v2",
    },
  };

  const newFeatures = [
    {id: "f-1", name: "Old", priority: "High", estimates: {eng: "M", qa: "S"}},
  ];

  const updated = applyRoadmapFeaturesToPayload(original, newFeatures);

  assert.equal(updated.roadmap.features[0].priority, "High");
  assert.deepEqual(updated.roadmap.features[0].estimates, {eng: "M", qa: "S"});
  assert.equal(updated.roadmap.roadmap_version, "v2");
});

test("applyRoadmapFeaturesToPayload preserves unknown feature fields during round-trip", () => {
  const features = [
    {id: "f-1", name: "Auth", priority: "High", estimates: {eng: "M"}, tags: ["security"], internal_note: "urgent"},
  ];
  const original = {roadmap: {features}};

  const read = readRoadmapFeaturesFromPayload(original);
  const updated = applyRoadmapFeaturesToPayload(original, read);

  assert.deepEqual(updated.roadmap.features[0].tags, ["security"]);
  assert.equal(updated.roadmap.features[0].internal_note, "urgent");
});

// Business goals

test("readBusinessGoalsFromPayload reads must_deliver_feature_ids and utilization goals", () => {
  const data = {
    business_goals: {
      must_deliver_feature_ids: ["f-1", "f-2"],
      preserve_priorities: ["Critical"],
      max_utilization: 0.9,
      min_buffer_ratio: 0.1,
    },
  };

  const goals = readBusinessGoalsFromPayload(data);

  assert.deepEqual(goals.must_deliver_feature_ids, ["f-1", "f-2"]);
  assert.equal(goals.max_utilization, 0.9);
  assert.equal(goals.min_buffer_ratio, 0.1);
});

test("readBusinessGoalsFromPayload returns defaults when business_goals is absent", () => {
  const goals = readBusinessGoalsFromPayload({});

  assert.deepEqual(goals.must_deliver_feature_ids, []);
  assert.equal(goals.max_utilization, null);
  assert.equal(goals.min_buffer_ratio, null);
});

test("applyBusinessGoalsToPayload writes goals preserving other business_goal fields", () => {
  const original = {
    business_goals: {
      must_deliver_feature_ids: ["f-1"],
      preserve_priorities: ["Critical", "High"],
      defer_preference: ["Low"],
      max_utilization: 0.85,
      min_buffer_ratio: 0.1,
    },
  };

  const goalsState = {
    must_deliver_feature_ids: ["f-1", "f-3"],
    max_utilization: 0.9,
    min_buffer_ratio: 0.15,
  };

  const updated = applyBusinessGoalsToPayload(original, goalsState);

  assert.deepEqual(updated.business_goals.must_deliver_feature_ids, ["f-1", "f-3"]);
  assert.equal(updated.business_goals.max_utilization, 0.9);
  assert.equal(updated.business_goals.min_buffer_ratio, 0.15);
  assert.deepEqual(updated.business_goals.preserve_priorities, ["Critical", "High"]);
  assert.deepEqual(updated.business_goals.defer_preference, ["Low"]);
});

test("applyBusinessGoalsToPayload seeds business_goals when absent", () => {
  const original = {planning_mode: "capacity_check"};

  const updated = applyBusinessGoalsToPayload(original, {
    must_deliver_feature_ids: ["f-99"],
    max_utilization: 0.9,
    min_buffer_ratio: 0.1,
  });

  assert.deepEqual(updated.business_goals.must_deliver_feature_ids, ["f-99"]);
  assert.equal(updated.business_goals.max_utilization, 0.9);
});
