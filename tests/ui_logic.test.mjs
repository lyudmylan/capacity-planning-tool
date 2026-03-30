import test from "node:test";
import assert from "node:assert/strict";

import {
  applyEditableFieldsToPayload,
  buildPlanComparison,
  getUtilizationStatus,
  readEditableFieldsFromPayload,
} from "../ui/app.js";

test("readEditableFieldsFromPayload reflects pasted JSON values", () => {
  const editableFields = readEditableFieldsFromPayload({
    planning_horizon: "year",
    working_days: 220,
    holidays_days: 12,
    vacation_days: 18,
    sick_days: 4,
    focus_factor: 0.9,
    sprint_days: 15,
    overhead_days_per_sprint: 3,
  });

  assert.deepEqual(editableFields, {
    planning_horizon: "year",
    working_days: 220,
    holidays_days: 12,
    vacation_days: 18,
    sick_days: 4,
    focus_factor: 0.9,
    sprint_days: 15,
    overhead_days_per_sprint: 3,
  });
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
