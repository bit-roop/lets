export type RequirementState = 'APPLICABLE' | 'NOT_APPLICABLE' | 'UNKNOWN' | 'CONFLICT';

export type RequirementType =
  | 'APPROVAL'
  | 'REGISTRATION'
  | 'LICENCE'
  | 'NOC'
  | 'CONSENT'
  | 'CERTIFICATE'
  | 'INSPECTION'
  | 'COMPLIANCE'
  | 'RENEWAL'
  | 'TRAINING'
  | 'INCENTIVE'
  | string;

export type Confidence = 'high' | 'medium' | 'low';

export type VerificationStatus = 'VERIFIED' | 'SECONDARY' | 'UNVERIFIED';

export type EvidenceKind =
  | 'POSITIVE_DEFINITE'
  | 'POSITIVE_INDETERMINATE'
  | 'ABSENCE_OF_TRIGGER'
  | 'ACTIVE_EXCLUSION'
  | 'EXCLUSION_INDETERMINATE';

export interface FactTrace {
  fact: string;
  value: any;
  op: string;
  target: any;
  result: 'TRUE' | 'FALSE' | 'UNKNOWN';
  reason: string;
  fact_origin: 'SUPPLIED' | 'DERIVED';
}

export interface SourceRef {
  source_id?: string;
  statute?: string;
  instrument?: string;
  effective_from?: string;
  effective_to?: string | null;
}

export interface SourceDetail {
  source_type?: string;
  authority?: string;
  document_title?: string;
  document_number?: string;
  document_date?: string;
  section?: string;
  verification_status?: VerificationStatus;
  verified_at?: string | null;
  verified_by?: string;
  source_url?: string;
  note?: string;
}

export interface DerivedFact {
  fact: string;
  value: any;
  value_type: 'string' | 'number' | 'boolean' | 'enum' | 'list';
  rule_id: string;
  rule_version: number;
  source: SourceRef;
  verification_status: VerificationStatus;
  input_facts: string[];
  derived_in_pass: number;
  derived_at: string;
  operation: string;
}

export interface IndeterminateDerivation {
  fact: string;
  rule_id: string;
  rule_version: number;
  source: SourceRef;
  verification_status: VerificationStatus;
  missing_facts: string[];
  reason: string;
  derived_in_pass: number;
}

export interface DerivedFactConflict {
  fact: string;
  derived_in_pass: number;
  competing_values: string[];
  competing_derivations: DerivedFact[];
  resolution: string;
  note: string;
}

export interface QuantitySpec {
  value: number | null;
  missing_facts: string[];
  formula: string;
}

export interface DependencyItem {
  requirement_id: string;
  dependency_type: 'LEGAL' | 'PROCESS' | 'OPERATIONAL' | 'RECOMMENDED' | 'UNVERIFIED';
  basis?: string;
  verification_status?: VerificationStatus;
  action?: string;
}

export interface EvidenceItem {
  rule_id: string;
  version: number;
  rule_name: string;
  result: 'TRUE' | 'FALSE' | 'UNKNOWN';
  evidence_kind: EvidenceKind;
  facts_used: FactTrace[];
  derived_facts_used?: DerivedFact[];
  source?: SourceRef;
  source_detail?: SourceDetail;
  verification_status: VerificationStatus;
  last_verified?: string | null;
  note?: string;
}

export interface Requirement {
  requirement_id: string;
  name: string;
  requirement_type: RequirementType;
  authority?: string;
  department?: string;
  statute?: string;
  sla_days?: number;
  state: RequirementState;
  confidence: Confidence;
  evidence: EvidenceItem[];
  missing_facts?: string[];
  missing_fact_origin?: Record<string, 'NOT_SUPPLIED' | 'WITHHELD_DUE_TO_CONFLICT'>;
  quantity?: QuantitySpec;
  depends_on?: DependencyItem[];
  scheduling_depends_on?: string[];
  candidate_dependencies?: DependencyItem[];
}

export interface DerivationDiagnostics {
  passes_run: number;
  max_passes: number;
  repeated_derivations_suppressed: number;
  reached_fixed_point: boolean;
}

export interface EngineWarning {
  type: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  rule_id?: string;
  requirement_id?: string;
  fact?: string;
}

export interface EvaluationSummary {
  applicable: number;
  not_applicable: number;
  unknown: number;
  conflict: number;
  derived_facts: number;
  indeterminate_derivations: number;
  derived_fact_conflicts: number;
  derivation_passes: number;
  rules_evaluated: number;
  warnings: number;
}

export interface EvaluationResponse {
  as_of: string;
  summary: EvaluationSummary;
  applicable: Requirement[];
  not_applicable: Requirement[];
  unknown: Requirement[];
  conflict: Requirement[];
  derived_facts: Record<string, DerivedFact>;
  indeterminate_derivations: IndeterminateDerivation[];
  derived_fact_conflicts: DerivedFactConflict[];
  derivation_diagnostics: DerivationDiagnostics;
  warnings: EngineWarning[];
}

export interface HealthResponse {
  status: string;
  engine_version: string;
  requirements_count: number;
  rules_count: number;
  sources_count: number;
  verification_summary: Record<string, number>;
}
