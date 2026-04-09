export function readEditableFieldsFromPayload(data) {
  return {
    planning_mode: data.planning_mode ?? "",
    planning_horizon: data.planning_horizon ?? "",
    calendar_year: data.calendar_year ?? "",
    half_year_index: data.half_year_index ?? "",
    quarter_index: data.quarter_index ?? "",
    month_index: data.month_index ?? "",
    start_date: data.start_date ?? "",
    end_date: data.end_date ?? "",
    working_days: data.working_days,
    holidays_days: data.holidays_days,
    vacation_days: data.vacation_days,
    sick_days: data.sick_days,
    focus_factor: data.focus_factor,
    sprint_days: data.sprint_days,
    overhead_days_per_sprint: data.overhead_days_per_sprint,
  };
}

export function validateInputPayload(jsonText) {
  const text = typeof jsonText === "string" ? jsonText.trim() : "";
  if (!text) {
    return {valid: false, error: null};
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    return {valid: false, error: "Invalid JSON: " + e.message};
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    const kind = Array.isArray(parsed) ? "array" : typeof parsed;
    return {valid: false, error: "Input must be a JSON object, not " + kind};
  }
  return {valid: true, error: null};
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

  if (rawFieldValues.planning_mode !== undefined && rawFieldValues.planning_mode !== "") {
    next.planning_mode = rawFieldValues.planning_mode;
  }

  const nextPlanningHorizon = rawFieldValues.planning_horizon;
  next.planning_horizon = nextPlanningHorizon;

  normalizePeriodSelectors(next, nextPlanningHorizon, buildPeriodSource(data, rawFieldValues));

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

export function buildSummaryModel(result) {
  const baselinePlan = result.baseline_plan ?? result;
  const selectedPlan = result.selected_plan ?? result;
  const planningMode = result.planning_mode ?? selectedPlan.planning_mode ?? baselinePlan.planning_mode;
  const deliveredFeatures = selectedPlan.delivered_features ?? result.delivered_features ?? [];
  const deferredFeatures = selectedPlan.deferred_features ?? result.deferred_features ?? [];
  const droppedFeatures = selectedPlan.dropped_features ?? result.dropped_features ?? [];

  let bannerClass = "feasibility-banner feasible";
  let bannerText = "Plan is feasible";
  if (!selectedPlan.feasibility) {
    bannerClass = "feasibility-banner infeasible";
    if (
      planningMode === "planning_schedule"
      && selectedPlan.dependency_rules_pass === false
      && (selectedPlan.bottleneck_functions?.length ?? 0) === 0
    ) {
      bannerText = "Plan is infeasible — dependency rules fail";
    } else if ((selectedPlan.bottleneck_functions?.length ?? 0) > 0) {
      bannerText = "Plan is infeasible — function demand exceeds capacity";
    } else {
      bannerText = "Plan is infeasible — demand exceeds capacity";
    }
  } else if (result.baseline_plan && baselinePlan.feasibility === false) {
    bannerText = "Selected plan is feasible";
  }

  return {
    planningMode,
    bannerClass,
    bannerText,
    capacityDevDays: result.capacity_dev_days,
    demandDevDays: selectedPlan.demand_dev_days,
    utilization: selectedPlan.utilization,
    bufferDevDays: selectedPlan.buffer_dev_days,
    deliveredCount: deliveredFeatures.length,
    deferredCount: deferredFeatures.length,
    droppedCount: droppedFeatures.length,
    selectedPlanFeasible: selectedPlan.feasibility,
  };
}

export function buildFunctionAnalysisModel(result) {
  const selectedPlan = result.selected_plan ?? result;
  const capacityByFunction = selectedPlan.capacity_by_function ?? {};
  const demandByFunction = selectedPlan.demand_by_function ?? {};
  const utilizationByFunction = selectedPlan.utilization_by_function ?? {};
  const bufferByFunction = selectedPlan.buffer_by_function ?? {};
  const bottleneckFunctions = selectedPlan.bottleneck_functions ?? result.bottleneck_functions ?? [];

  const allFunctionNames = Array.from(new Set([
    ...Object.keys(capacityByFunction),
    ...Object.keys(demandByFunction),
    ...Object.keys(utilizationByFunction),
    ...Object.keys(bufferByFunction),
  ]));

  const rows = allFunctionNames.map((name) => ({
    name,
    capacity: capacityByFunction[name] ?? null,
    demand: demandByFunction[name] ?? null,
    utilization: utilizationByFunction[name] ?? null,
    buffer: bufferByFunction[name] ?? null,
    isBottleneck: bottleneckFunctions.includes(name),
  }));

  return {
    rows,
    hasBottlenecks: bottleneckFunctions.length > 0,
    bottleneckFunctions: [...bottleneckFunctions],
  };
}

export function buildPeriodSource(data, rawFieldValues) {
  const calendarYear = parseFormInteger(rawFieldValues.calendar_year) ?? data.calendar_year;
  const halfYearIndex = parseFormInteger(rawFieldValues.half_year_index) ?? data.half_year_index;
  const quarterIndex = parseFormInteger(rawFieldValues.quarter_index) ?? data.quarter_index;
  const monthIndex = parseFormInteger(rawFieldValues.month_index) ?? data.month_index;
  const startDate = isValidIsoDateString(rawFieldValues.start_date) ? rawFieldValues.start_date : data.start_date;
  const endDate = isValidIsoDateString(rawFieldValues.end_date) ? rawFieldValues.end_date : data.end_date;
  return {
    ...data,
    calendar_year: calendarYear,
    half_year_index: halfYearIndex,
    quarter_index: quarterIndex,
    month_index: monthIndex,
    start_date: startDate,
    end_date: endDate,
  };
}

function parseNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isNaN(number) ? undefined : number;
}

function normalizePeriodSelectors(payload, planningHorizon, sourcePayload = payload) {
  delete payload.calendar_year;
  delete payload.half_year_index;
  delete payload.quarter_index;
  delete payload.month_index;
  delete payload.start_date;
  delete payload.end_date;

  const inferred = inferPeriodSelectors(sourcePayload);
  const calendarYear = inferred.calendar_year;
  const halfYearIndex = inferred.half_year_index;
  const quarterIndex = inferred.quarter_index;
  const monthIndex = inferred.month_index;
  const startDate = inferred.start_date;
  const endDate = inferred.end_date;

  if (planningHorizon === "year") {
    payload.calendar_year = calendarYear;
    return;
  }
  if (planningHorizon === "half_year") {
    payload.calendar_year = calendarYear;
    payload.half_year_index = halfYearIndex;
    return;
  }
  if (planningHorizon === "quarter") {
    payload.calendar_year = calendarYear;
    payload.quarter_index = quarterIndex;
    return;
  }
  if (planningHorizon === "month") {
    payload.calendar_year = calendarYear;
    payload.month_index = monthIndex;
    return;
  }
  if (planningHorizon === "sprint") {
    payload.start_date = startDate;
    payload.end_date = endDate;
  }
}

function parseFormInteger(value) {
  if (value == null || value === "") return undefined;
  const n = Number.parseInt(String(value), 10);
  return Number.isFinite(n) ? n : undefined;
}

function isValidIsoDateString(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && parseIsoDate(value) !== undefined;
}

function inferPeriodSelectors(payload) {
  const now = new Date();
  const startDate = parseIsoDate(payload.start_date);
  const endDate = parseIsoDate(payload.end_date);
  const monthFromDate = startDate ? startDate.getUTCMonth() + 1 : undefined;
  const yearFromDate = startDate?.getUTCFullYear() ?? endDate?.getUTCFullYear();
  const rawQuarterIndex = normalizeInteger(payload.quarter_index);
  const rawHalfYearIndex = normalizeInteger(payload.half_year_index);
  const calendarYear = normalizeInteger(payload.calendar_year)
    ?? yearFromDate
    ?? now.getUTCFullYear();
  const monthIndex = clampMonth(
    normalizeInteger(payload.month_index)
      ?? monthFromDate
      ?? quarterToStartMonth(rawQuarterIndex)
      ?? halfYearToStartMonth(rawHalfYearIndex)
      ?? 1
  );
  const quarterIndex = clampQuarter(
    rawQuarterIndex
      ?? monthToQuarter(monthIndex)
  );
  const halfYearIndex = clampHalfYear(
    rawHalfYearIndex
      ?? quarterToHalfYear(quarterIndex)
  );
  const normalizedStartDate = startDate ?? safeUtcDate(calendarYear, monthIndex, 1);
  const normalizedEndDate = endDate ?? addDays(normalizedStartDate, 13);

  return {
    calendar_year: calendarYear,
    half_year_index: halfYearIndex,
    quarter_index: quarterIndex,
    month_index: monthIndex,
    start_date: formatIsoDate(normalizedStartDate),
    end_date: formatIsoDate(normalizedEndDate),
  };
}

function normalizeInteger(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return undefined;
  }
  return Math.trunc(value);
}

function parseIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined;
  }
  const parsed = new Date(value + "T00:00:00Z");
  return Number.isNaN(parsed.getTime()) ? undefined : parsed;
}

function formatIsoDate(value) {
  return value.toISOString().slice(0, 10);
}

function addDays(value, days) {
  const next = new Date(value.getTime());
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

function safeUtcDate(year, monthIndex, day) {
  const normalizedYear = Number.isFinite(year) ? year : new Date().getUTCFullYear();
  const normalizedMonth = Number.isFinite(monthIndex) ? clampMonth(monthIndex) : 1;
  return new Date(Date.UTC(normalizedYear, normalizedMonth - 1, day));
}

function monthToQuarter(monthIndex) {
  return Math.floor((monthIndex - 1) / 3) + 1;
}

function quarterToHalfYear(quarterIndex) {
  return quarterIndex <= 2 ? 1 : 2;
}

function quarterToStartMonth(quarterIndex) {
  if (quarterIndex == null) return undefined;
  return ((clampQuarter(quarterIndex) - 1) * 3) + 1;
}

function halfYearToStartMonth(halfYearIndex) {
  if (halfYearIndex == null) return undefined;
  return clampHalfYear(halfYearIndex) === 1 ? 1 : 7;
}

function clampMonth(value) {
  return Math.min(12, Math.max(1, value));
}

function clampQuarter(value) {
  return Math.min(4, Math.max(1, value));
}

function clampHalfYear(value) {
  return Math.min(2, Math.max(1, value));
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
