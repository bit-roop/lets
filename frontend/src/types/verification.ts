// Milestone 5 evidence-verification types.
//
// These describe what M5 observed about a submitted document. They never
// describe whether an approval applies or whether an M4 requirement is
// satisfied -- those stay with engine-v3, M3 and M4.

export type M4ApplicabilityObserved =
  | 'APPLICABLE_CONDITION_TRUE'
  | 'NOT_APPLICABLE_CONDITION_FALSE'
  | 'UNRESOLVED_CONDITION_UNKNOWN'
  | 'UNRESOLVED_ENGINE_STATE'
  | 'UNSUPPORTED_APPROVAL';

export type VerificationDisposition =
  | 'NOT_ANALYZED'
  | 'REJECTED_STRUCTURAL'
  | 'NEEDS_APPLICANT_ACTION'
  | 'HUMAN_REVIEW_REQUIRED'
  | 'ACCEPTED_FOR_REVIEW';

export type AuthenticityState =
  | 'NOT_ASSESSED'
  | 'NOT_APPLICABLE_APPLICANT_AUTHORED'
  | 'NO_MECHANISM_AVAILABLE'
  | 'UNVERIFIED'
  | 'SUPPORTED'
  | 'VERIFIED'
  | 'FAILED';

export interface VerificationProvenance {
  method: string;
  page: number | null;
  char_span: number[] | null;
  profile_id: string | null;
  profile_version: string | null;
  ruleset_version: string;
  model_id: string | null;
}

export type FieldSensitivity =
  | 'NON_SENSITIVE'
  | 'PERSONAL_NAME'
  | 'IDENTIFIER'
  | 'QUANTITY'
  | 'DATE';

/**
 * Raw and normalized values are deliberately absent from this type: the server
 * does not send them. `display_value` is the value itself for non-sensitive
 * fields and a masked form for names and identifiers.
 */
export interface VerificationField {
  field_id: string;
  /** Applicant-facing label from the profile. Render this, never field_id. */
  label: string;
  field_source: 'PROFILE_GROUNDED' | 'RESEARCH_REQUIRED';
  sensitivity: FieldSensitivity;
  value_present: boolean;
  display_value: string | null;
  masked: boolean;
  confidence: number;
  uncertainty_reason: string | null;
  provenance: VerificationProvenance;
}

export interface VerificationFinding {
  check_id: string;
  outcome: 'MATCH' | 'MISMATCH' | 'UNKNOWN' | 'NOT_APPLICABLE' | 'UNREADABLE';
  severity: 'BLOCKING' | 'ADVISORY' | 'INFORMATIONAL';
  message: string;
  remedy: string | null;
  inputs: string[];
  observed: string | null;
  expected: string | null;
  provenance: VerificationProvenance;
}

export interface VerificationAuthenticity {
  state: AuthenticityState;
  availability: string;
  authoritative: boolean;
  provider_id: string | null;
  evidence: string[];
  checked_at: string | null;
  explanation: string;
}

export interface VerificationConfidence {
  extraction_min: number | null;
  extraction_mean: number | null;
  classification_margin: number | null;
  grounded_field_coverage: number | null;
}

export interface VerificationHumanReview {
  ticket_id: string;
  triggers: string[];
  reasons: string[];
  fields: string[];
  pages: number[];
  disputed: Array<Record<string, any>>;
  checklist: string[];
  status: string;
}

export interface VerificationClassificationDetail {
  label: string | null;
  score: number | null;
  runner_up: string | null;
  runner_up_score: number | null;
  matched_anchors: string[];
}

export interface VerificationRecord {
  record_id: string;
  submission_id: string;
  application_id: string;
  document_id: string;
  submission_sha256: string | null;
  m4_applicability_observed: M4ApplicabilityObserved;
  requirement_match: 'MATCH' | 'LIKELY_MATCH' | 'MISMATCH' | 'INDETERMINATE' | 'NOT_APPLICABLE';
  profile_id: string | null;
  profile_version: string | null;
  ingestion: string;
  extraction: string;
  classification: string;
  classification_detail: VerificationClassificationDetail;
  internal_consistency: string;
  cross_consistency: string;
  fields: VerificationField[];
  findings: VerificationFinding[];
  authenticity: VerificationAuthenticity;
  confidence: VerificationConfidence;
  disposition: VerificationDisposition;
  disposition_reason: string | null;
  human_review: VerificationHumanReview | null;
  created_at: string;
}

export interface VerificationRecordsResponse {
  application_id: string;
  records: VerificationRecord[];
}

export interface M5EvidenceCounters {
  m5_supported_applicable_count: number;
  m5_analyzed_count: number;
  m5_accepted_for_review_count: number;
  m5_needs_action_count: number;
  m5_human_review_count: number;
  m5_rejected_structural_count: number;
  m5_not_analyzed_count: number;
  m5_no_profile_count: number;
  m5_applicability_unresolved_count: number;
  m5_not_applicable_count: number;
  m5_non_upload_excluded_count: number;
  m5_unsupported_excluded_count: number;
  m5_authenticity_established_count: number;
}

export interface VerificationOverlayResponse {
  application_id: string;
  m4_readiness: any;
  m5_evidence: {
    note: string;
    denominator_definition: string;
    counters: M5EvidenceCounters;
    per_requirement: Array<{
      requirement_id: string;
      approval_id: string;
      document_id: string;
      document_name: string;
      m4_applicability_observed: M4ApplicabilityObserved;
      in_m5_denominator: boolean;
      disposition: VerificationDisposition | null;
      has_profile: boolean;
    }>;
  };
}

export interface VerificationCapabilities {
  capabilities: Record<string, any>;
  authenticity: { states_in_use: string; note: string };
  profiles: Array<{
    profile_id: string;
    document_id: string;
    display_name: string;
    applicant_summary: string;
    authenticity_capability: AuthenticityState;
    limitations: string[];
  }>;
  not_analyzed_document_ids: string[];
  not_analyzed_note: string;
}
