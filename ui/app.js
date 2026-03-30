export function readEditableFieldsFromPayload(data) {
  return {
    planning_horizon: data.planning_horizon ?? "",
    working_days: data.working_days,
    holidays_days: data.holidays_days,
    vacation_days: data.vacation_days,
    sick_days: data.sick_days,
    focus_factor: data.focus_factor,
    sprint_days: data.sprint_days,
    overhead_days_per_sprint: data.overhead_days_per_sprint,
  };
}

export function applyEditableFieldsToPayload(data, rawFieldValues) {
  const next = {...data};
  const fields = [
    "working_days",
    "holidays_days",
    "vacation_days",
    "sick_days",
    "focus_factor",
    "sprint_days",
    "overhead_days_per_sprint",
  ];

  next.planning_horizon = rawFieldValues.planning_horizon;
  for (const field of fields) {
    const value = parseNumber(rawFieldValues[field]);
    if (value !== undefined) {
      next[field] = value;
    }
  }
  return next;
}

export function getUtilizationStatus(utilization) {
  if (utilization > 0.9) {
    return "infeasible";
  }
  if (utilization >= 0.8) {
    return "feasible";
  }
  return "warning";
}

export function buildPlanComparison(inputData, result) {
  const originalFeatureCount = inputData.roadmap?.features?.length ?? 0;
  const baselinePlan = result.baseline_plan ?? result;
  const selectedPlan = result.selected_plan ?? {};
  const selectedDeliveredCount = selectedPlan.delivered_features?.length
    ?? result.delivered_features?.length
    ?? originalFeatureCount;
  const removedFeatures = [
    ...(selectedPlan.deferred_features ?? result.deferred_features ?? []),
    ...(selectedPlan.dropped_features ?? result.dropped_features ?? []),
  ];
  const originalDemand = baselinePlan.demand_dev_days;
  const selectedDemand = selectedPlan.demand_dev_days ?? originalDemand;
  const originalUtilization = baselinePlan.utilization;
  const selectedUtilization = selectedPlan.utilization ?? originalUtilization;
  const originalBuffer = baselinePlan.buffer_dev_days;
  const selectedBuffer = selectedPlan.buffer_dev_days ?? originalBuffer;

  return {
    original_feature_count: originalFeatureCount,
    selected_delivered_count: selectedDeliveredCount,
    removed_feature_count: removedFeatures.length,
    removed_feature_names: removedFeatures.map((feature) => feature.name),
    original_demand_dev_days: originalDemand,
    selected_demand_dev_days: selectedDemand,
    demand_delta_dev_days: selectedDemand - originalDemand,
    original_utilization: originalUtilization,
    selected_utilization: selectedUtilization,
    utilization_delta: selectedUtilization - originalUtilization,
    original_buffer_dev_days: originalBuffer,
    selected_buffer_dev_days: selectedBuffer,
    buffer_delta_dev_days: selectedBuffer - originalBuffer,
    delivered_delta_tone: getSignedOutcomeTone(
      selectedDeliveredCount - originalFeatureCount,
      {positive: "better", negative: "worse"}
    ),
    demand_delta_tone: getSignedOutcomeTone(
      selectedDemand - originalDemand,
      {positive: "worse", negative: "better"}
    ),
    utilization_delta_tone: getUtilizationTone(
      originalUtilization,
      selectedUtilization
    ),
    buffer_delta_tone: getSignedOutcomeTone(
      selectedBuffer - originalBuffer,
      {positive: "better", negative: "worse"}
    ),
    changed: removedFeatures.length > 0,
  };
}

function parseNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isNaN(number) ? undefined : number;
}

function getSignedOutcomeTone(value, mapping) {
  if (value > 0) return mapping.positive;
  if (value < 0) return mapping.negative;
  return "";
}

function getUtilizationTone(originalUtilization, selectedUtilization) {
  const originalGap = utilizationGap(originalUtilization);
  const selectedGap = utilizationGap(selectedUtilization);
  if (selectedGap < originalGap) return "better";
  if (selectedGap > originalGap) return "worse";
  return "";
}

function utilizationGap(utilization) {
  if (utilization < 0.8) return 0.8 - utilization;
  if (utilization > 0.9) return utilization - 0.9;
  return 0;
}
