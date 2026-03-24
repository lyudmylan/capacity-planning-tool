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

function parseNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isNaN(number) ? undefined : number;
}
