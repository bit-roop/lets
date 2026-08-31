import { ApplicantFacts } from '../types/facts';

export interface StepError {
  field: string;
  label: string;
}

export const STEP_TITLES: Record<number, string> = {
  1: 'Business',
  2: 'Location',
  3: 'Operations',
  4: 'Equipment',
};

const isEmpty = (v: any) =>
  v === null ||
  v === undefined ||
  v === '';

export function getStep1Errors(
  facts: ApplicantFacts
): StepError[] {
  const errors: StepError[] = [];

  if (isEmpty(facts._name) && isEmpty(facts.entity_name)) {
    errors.push({
      field: 'entity_name',
      label: 'Business name',
    });
  }

  if (isEmpty(facts.investment_plant_machinery)) {
    errors.push({
      field: 'investment_plant_machinery',
      label: 'Investment in plant & machinery',
    });
  }

  return errors;
}

export function getStep2Errors(
  facts: ApplicantFacts
): StepError[] {
  const errors: StepError[] = [];

  if (isEmpty(facts.location_authority)) {
    errors.push({
      field: 'location_authority',
      label: 'Location authority',
    });
  }

  if (isEmpty(facts.land_classification)) {
    errors.push({
      field: 'land_classification',
      label: 'Land type',
    });
  }

  if (
    facts.builtup_area_sqm === null ||
    facts.builtup_area_sqm === undefined ||
    facts.builtup_area_sqm <= 0
  ) {
    errors.push({
      field: 'builtup_area_sqm',
      label: 'Built-up area',
    });
  }

  if (
    !facts.midc_estate ||
    facts.midc_estate.trim().length === 0
  ) {
    errors.push({
      field: 'midc_estate',
      label: 'Industrial estate / cluster',
    });
  }

  return errors;
}

export function getStep3Errors(
  facts: ApplicantFacts
): StepError[] {
  const errors: StepError[] = [];

  if (isEmpty(facts.annual_turnover)) {
    errors.push({
      field: 'annual_turnover',
      label: 'Annual turnover',
    });
  }

  if (isEmpty(facts.employees_total)) {
    errors.push({
      field: 'employees_total',
      label: 'Total employees',
    });
  }

  if (isEmpty(facts.workers_for_threshold)) {
    errors.push({
      field: 'workers_for_threshold',
      label: 'Factory floor workers',
    });
  }

  return errors;
}

export function getStep4Errors(
  facts: ApplicantFacts
): StepError[] {
  const errors: StepError[] = [];

  if (facts.boiler_operates) {
    if (isEmpty(facts.boiler_capacity_litres)) {
      errors.push({
        field: 'boiler_capacity_litres',
        label: 'Boiler capacity',
      });
    }

    if (isEmpty(facts.boiler_pressure_kg_cm2)) {
      errors.push({
        field: 'boiler_pressure_kg_cm2',
        label: 'Boiler pressure',
      });
    }

    if (isEmpty(facts.boiler_water_temp_c)) {
      errors.push({
        field: 'boiler_water_temp_c',
        label: 'Boiler water temperature',
      });
    }
  }

  return errors;
}

export function getStepErrors(
  step: number,
  facts: ApplicantFacts
): StepError[] {
  switch (step) {
    case 1:
      return getStep1Errors(facts);

    case 2:
      return getStep2Errors(facts);

    case 3:
      return getStep3Errors(facts);

    case 4:
      return getStep4Errors(facts);

    default:
      return [];
  }
}

export function getAllErrors(
  facts: ApplicantFacts
): { step: number; errors: StepError[] }[] {
  return [1, 2, 3, 4]
    .map((step) => ({
      step,
      errors: getStepErrors(step, facts),
    }))
    .filter((s) => s.errors.length > 0);
}