export interface ApplicantFacts {
  _name?: string;
  stage?: string;
  entity_type?: string;
  entity_name?: string;
  location_authority?: string;
  land_classification?: string;
  builtup_area_sqm?: number | null;
  is_food_business?: boolean | null;
  annual_turnover?: number | null;
  investment_plant_machinery?: number | null;
  employees_total?: number | null;
  workers_for_threshold?: number | null;
  uses_power?: boolean | null;
  contract_labourers?: number | null;
  food_handlers?: number | null;
  boiler_operates?: boolean | null;
  boiler_capacity_litres?: number | null;
  boiler_pressure_kg_cm2?: number | null;
  boiler_water_temp_c?: number | null;
  export?: boolean | null;
  multi_state_operation?: boolean | null;
  mpcb_category?: string | null;
  in_esic_implemented_area?: boolean | null;
  notified_industry_category?: string[];
  [key: string]: any;
}

export interface PersonaMeta {
  id: string;
  name: string;
  tagline: string;
  description: string;
  keyFactsSummary: string[];
}
