import { EvaluationResponse, HealthResponse } from '../types/engine';
import { ApplicantFacts } from '../types/facts';
import {
  VerificationCapabilities,
  VerificationOverlayResponse,
  VerificationRecord,
  VerificationRecordsResponse,
} from '../types/verification';

export type {
  VerificationCapabilities,
  VerificationOverlayResponse,
  VerificationRecord,
  VerificationRecordsResponse,
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const isFormData = typeof FormData !== 'undefined' && options?.body instanceof FormData;
    const response = await fetch(url, {
      ...options,
      headers: isFormData
        ? options?.headers
        : { 'Content-Type': 'application/json', ...options?.headers },
    });

    if (!response.ok) {
      let errData;
      try {
        errData = await response.json();
      } catch {
        errData = await response.text();
      }
      throw new ApiError(
        typeof errData === 'object' && errData.detail ? errData.detail : `HTTP ${response.status}`,
        response.status,
        errData
      );
    }

    return (await response.json()) as T;
  } catch (error: any) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || 'Network request failed', 0, null);
  }
}

export const api = {
  getHealth: () => fetchJson<HealthResponse>('/api/health'),
  getCatalogue: () => fetchJson<Record<string, any>>('/api/catalogue'),
  getSources: () => fetchJson<Record<string, any>>('/api/sources'),
  getPersonas: () => fetchJson<{ id: string; name: string }[]>('/api/personas'),
  getPersonaById: (personaId: string) => fetchJson<ApplicantFacts>(`/api/personas/${personaId}`),
  evaluate: (facts: ApplicantFacts, asOf?: string) =>
    fetchJson<EvaluationResponse>('/api/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        facts,
        as_of: asOf || new Date().toISOString().split('T')[0],
      }),
    }),
  getDocumentRequirements: (approvalId?: string) =>
    fetchJson<DocumentRequirementsResponse>(
      `/api/documents/requirements${approvalId ? `?approval_id=${encodeURIComponent(approvalId)}` : ''}`
    ),
  evaluateDocumentRequirements: (payload: DocumentRequirementsRequest) =>
    fetchJson<DocumentRequirementsEvaluation>('/api/documents/requirements', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  submitDocument: (formData: FormData) =>
    fetchJson<DocumentSubmissionResponse>('/api/documents/submit', {
      method: 'POST',
      body: formData,
    }),
  submitStructuredDocument: (payload: StructuredDocumentSubmission) =>
    fetchJson<DocumentSubmissionResponse>('/api/documents/submit', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getDocumentReadiness: (applicationId: string, facts: ApplicantFacts, approvalIds?: string[]) => {
    const params = new URLSearchParams({
      application_id: applicationId,
      facts: JSON.stringify(facts),
      workflow_aware: 'true',
    });
    if (approvalIds?.length === 1) params.set('approval_id', approvalIds[0]);
    return fetchJson<DocumentReadinessResponse>(`/api/documents/readiness?${params.toString()}`);
  },

  // --- Milestone 5: evidence verification (additive) ---
  // These endpoints report what M5 observed about submitted documents. They do
  // not change M4 readiness, requirements, or which approvals apply.
  //
  // Both calls pass the M4 result the caller already holds. M5 observes the
  // applicability M4 established rather than triggering a fresh evaluation, so
  // it always reports on exactly the M4 state the applicant is being shown.
  analyzeSubmission: (submissionId: string, m4Result: DocumentRequirementsEvaluation) =>
    fetchJson<VerificationRecord>('/api/verification/analyze', {
      method: 'POST',
      body: JSON.stringify({ submission_id: submissionId, m4_result: m4Result }),
    }),
  getVerificationRecords: (applicationId: string) =>
    fetchJson<VerificationRecordsResponse>(
      `/api/verification/records?application_id=${encodeURIComponent(applicationId)}`
    ),
  getVerificationOverlay: (
    applicationId: string,
    m4Result: DocumentRequirementsEvaluation,
    m4Readiness: DocumentReadinessResponse | null
  ) =>
    fetchJson<VerificationOverlayResponse>('/api/verification/evidence', {
      method: 'POST',
      body: JSON.stringify({
        application_id: applicationId,
        m4_result: m4Result,
        m4_readiness: m4Readiness,
      }),
    }),
  getVerificationCapabilities: () =>
    fetchJson<VerificationCapabilities>('/api/verification/capabilities'),

  // --- Milestone 5, Slice 3: Persistent Application Case & Tracking ---
  createApplication: (payload: ApplicationCreateRequest) =>
    fetchJson<ApplicationRecord>('/api/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listApplications: () =>
    fetchJson<ApplicationListResponse>('/api/applications'),
  getApplication: (applicationId: string) =>
    fetchJson<ApplicationRecord>(`/api/applications/${encodeURIComponent(applicationId)}`),

  // --- Slice 4: prototype department review simulation ---
  // These endpoints act on the persisted case only. None of them re-runs the
  // engine, the workflow builder, or M4/M5 evaluation.
  listDepartments: () => fetchJson<{ departments: DepartmentInfo[] }>('/api/departments'),
  listDepartmentCases: (department: string) =>
    fetchJson<DepartmentCaseListResponse>(
      `/api/departments/${encodeURIComponent(department)}/applications`
    ),
  getDepartmentCase: (department: string, applicationId: string) =>
    fetchJson<DepartmentCaseDetail>(
      `/api/departments/${encodeURIComponent(department)}/applications/${encodeURIComponent(applicationId)}`
    ),
  startReview: (applicationId: string, approvalId: string, department: string) =>
    fetchJson<ApprovalLifecycleView>(
      `/api/applications/${encodeURIComponent(applicationId)}/approvals/${encodeURIComponent(approvalId)}/start-review`,
      { method: 'POST', body: JSON.stringify({ department }) }
    ),
  grantApproval: (applicationId: string, approvalId: string, department: string, decisionNote?: string) =>
    fetchJson<ApprovalLifecycleView>(
      `/api/applications/${encodeURIComponent(applicationId)}/approvals/${encodeURIComponent(approvalId)}/grant`,
      { method: 'POST', body: JSON.stringify({ department, decision_note: decisionNote || null }) }
    ),
  rejectApproval: (applicationId: string, approvalId: string, department: string, decisionNote?: string) =>
    fetchJson<ApprovalLifecycleView>(
      `/api/applications/${encodeURIComponent(applicationId)}/approvals/${encodeURIComponent(approvalId)}/reject`,
      { method: 'POST', body: JSON.stringify({ department, decision_note: decisionNote || null }) }
    ),
  raiseQuery: (applicationId: string, payload: RaiseQueryPayload) =>
    fetchJson<QueryView>(`/api/applications/${encodeURIComponent(applicationId)}/queries`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listQueries: (applicationId: string, department?: string) =>
    fetchJson<QueryListResponse>(
      `/api/applications/${encodeURIComponent(applicationId)}/queries${
        department ? `?department=${encodeURIComponent(department)}` : ''
      }`
    ),
  respondToQuery: (applicationId: string, queryId: string, payload: RespondToQueryPayload) =>
    fetchJson<QueryView>(
      `/api/applications/${encodeURIComponent(applicationId)}/queries/${encodeURIComponent(queryId)}/respond`,
      { method: 'POST', body: JSON.stringify(payload) }
    ),
  resolveQuery: (applicationId: string, queryId: string, department: string, resolutionNote?: string) =>
    fetchJson<QueryView>(
      `/api/applications/${encodeURIComponent(applicationId)}/queries/${encodeURIComponent(queryId)}/resolve`,
      { method: 'POST', body: JSON.stringify({ department, resolution_note: resolutionNote || null }) }
    ),
};

// --- Slice 4 types ----------------------------------------------------------

export type ApprovalLifecycleStatus =
  | 'SUBMITTED'
  | 'IN_SCRUTINY'
  | 'QUERY_PENDING'
  | 'GRANTED'
  | 'REJECTED';

export type ApplicationLifecycleStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'QUERY_RAISED'
  | 'RESPONDED'
  | 'GRANTED'
  | 'REJECTED';

export type QueryStatus = 'OPEN' | 'RESPONDED' | 'RESOLVED';

export interface DepartmentInfo {
  department: string;
  label: string;
}

export interface ApprovalLifecycleView {
  approval_id: string;
  name?: string | null;
  department: string;
  status: ApprovalLifecycleStatus;
  decision_note?: string | null;
  decided_at?: string | null;
  readiness_status?: string | null;
  sla_days?: number | null;
  statute?: string | null;
  updated_at?: string | null;
}

export interface QueryView {
  query_id: string;
  application_id: string;
  approval_id: string;
  approval_name?: string | null;
  department: string;
  query_text: string;
  deadline: string;
  status: QueryStatus;
  response_text?: string | null;
  response_document_id?: string | null;
  response_submission_id?: string | null;
  responded_at?: string | null;
  resolution_note?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LifecycleEventView {
  event_id: string;
  approval_id?: string | null;
  department?: string | null;
  actor: string;
  event_type: string;
  detail?: string | null;
  created_at: string;
}

export interface ApplicationLifecycleView {
  application_status: ApplicationLifecycleStatus;
  reviewable_departments: string[];
  approvals: ApprovalLifecycleView[];
  queries: QueryView[];
  open_queries: QueryView[];
  events: LifecycleEventView[];
  simulation_notice: string;
}

export interface DepartmentCaseSummary {
  application_id: string;
  tracking_reference: string;
  entity_name: string;
  application_status: ApplicationLifecycleStatus;
  department: string;
  approvals: ApprovalLifecycleView[];
  open_query_count: number;
  responded_query_count: number;
  submissions_count: number;
  last_activity_at?: string | null;
  created_at: string;
}

export interface DepartmentEvidenceItem {
  document_id: string;
  submission_reference: string;
  evidence_state?: string | null;
  automated_check_outcome?: string | null;
  automated_check_consistency?: string | null;
}

export interface DepartmentCaseDetail {
  application_id: string;
  tracking_reference: string;
  entity_name: string;
  application_status: ApplicationLifecycleStatus;
  department: string;
  as_of: string;
  approvals: ApprovalLifecycleView[];
  evidence: DepartmentEvidenceItem[];
  queries: QueryView[];
  timeline: ApplicationRecord['timeline'] | Record<string, never>;
  events: LifecycleEventView[];
  created_at: string;
  updated_at: string;
  evidence_notice: string;
  simulation_notice: string;
}

export interface DepartmentCaseListResponse {
  department: string;
  label: string;
  cases: DepartmentCaseSummary[];
  total_count: number;
}

export interface QueryListResponse {
  application_id: string;
  queries: QueryView[];
  total_count: number;
}

export interface RaiseQueryPayload {
  approval_id: string;
  department: string;
  query_text: string;
  deadline: string;
}

export interface RespondToQueryPayload {
  response_text: string;
  response_document_id?: string | null;
  response_submission_id?: string | null;
}

export interface ApplicationCreateRequest {
  application_id?: string;
  entity_name: string;
  facts: ApplicantFacts;
  as_of?: string;
  approvals?: Array<{
    approval_id: string;
    name?: string;
    department?: string;
    statute?: string;
    sla_days?: number | null;
    readiness_status?: string;
    engine_state?: string;
  }>;
  submissions?: Array<{
    document_id: string;
    submission_id: string;
    filename?: string | null;
    item_kind?: string;
    state?: string;
  }>;
  verification_records?: Array<{
    document_id: string;
    record_id?: string;
    disposition?: string;
    internal_consistency?: string;
    confidence_overall?: number;
  }>;
  workflow_snapshot?: any;
}

export interface ApplicationSummary {
  application_id: string;
  tracking_reference: string;
  entity_name: string;
  status: string;
  as_of: string;
  approvals_count: number;
  ready_count: number;
  submissions_count: number;
  created_at: string;
  updated_at: string;
}

export interface ApplicationListResponse {
  applications: ApplicationSummary[];
  total_count: number;
}

export interface TimelinePhaseItem {
  approval_id: string;
  name: string;
  department: string;
  sla_days?: number | null;
  readiness_status: string;
  blocked_by: string[];
  precondition_note?: string;
}

export interface ApplicationRecord {
  application_id: string;
  tracking_reference: string;
  entity_name: string;
  status: string;
  as_of: string;
  facts: ApplicantFacts;
  approvals: Array<{
    approval_id: string;
    name?: string;
    department?: string;
    statute?: string;
    sla_days?: number | null;
    readiness_status?: string;
    engine_state?: string;
  }>;
  submissions: Array<{
    document_id: string;
    submission_id: string;
    filename?: string | null;
    item_kind?: string;
    state?: string;
  }>;
  verification_records: Array<{
    document_id: string;
    record_id?: string;
    disposition?: string;
    internal_consistency?: string;
    confidence_overall?: number;
  }>;
  timeline: {
    summary: string;
    total_approvals: number;
    phase_1_immediate: {
      phase_number: number;
      title: string;
      description: string;
      count: number;
      items: TimelinePhaseItem[];
    };
    phase_2_sequential: {
      phase_number: number;
      title: string;
      description: string;
      count: number;
      items: TimelinePhaseItem[];
    };
  };
  created_at: string;
  updated_at: string;
  // Slice 4. Present once the department lifecycle layer is available.
  lifecycle?: ApplicationLifecycleView | null;
}

export interface DocumentRequirementRow {
  requirement_id: string;
  approval_id: string;
  document_id: string;
  obligation: 'MANDATORY' | 'CONDITIONAL' | 'SUPPORTING' | string;
  condition: Record<string, any> | null;
  condition_description: string | null;
  blocking: boolean;
  verification_status: 'VERIFIED' | 'VERIFIED_SCOPE_UNCLEAR' | 'SECONDARY' | 'UNSUPPORTED' | string;
  source: {
    source_id: string;
    authority: string;
    title: string;
    url?: string | null;
    checklist_item?: string | null;
    section?: string | null;
    verification_status: string;
    last_verified?: string | null;
  };
  condition_state?: 'TRUE' | 'FALSE' | 'UNKNOWN' | string;
  condition_trace?: any[];
  notes?: string | null;
}

export interface DocumentApprovalResult {
  approval_id: string;
  engine_state: string | null;
  coverage: {
    approval_id: string;
    status: 'SUPPORTED' | 'UNSUPPORTED' | string;
    reason: string;
    requirement_count: number;
    source_ids: string[];
  };
  requirements: DocumentRequirementRow[];
}

export interface DocumentRequirementsResponse {
  coverage: DocumentApprovalResult['coverage'][];
  specs: Array<{
    document_id: string;
    name: string;
    item_kind: 'UPLOAD_DOCUMENT' | 'FORM_INPUT' | 'FEE' | 'INSPECTION_EVENT' | 'DECLARATION' | string;
    description: string;
    accepted_formats?: string[];
  }>;
  requirements: DocumentRequirementRow[];
}

export interface DocumentRequirementsRequest {
  facts: ApplicantFacts;
  as_of?: string;
  approval_ids?: string[];
  include_provisional?: boolean;
  workflow_aware?: boolean;
}

export interface DocumentRequirementsEvaluation {
  approvals: DocumentApprovalResult[];
  engine_evaluation: EvaluationResponse;
  workflow?: any;
}

export interface DocumentSubmissionResponse {
  submission_id: string;
  document_id: string;
  application_id: string;
  filename?: string | null;
  state: string;
  validation?: { status?: string; semantics?: string; fields?: Record<string, any> } | null;
  sha256?: string | null;
  size_bytes?: number | null;
  mime_type?: string | null;
  duplicate?: boolean;
  verification_note?: string;
}

export interface StructuredDocumentSubmission {
  application_id: string;
  document_id: string;
  item_kind: string;
  structured_data: Record<string, any>;
}

export interface DocumentReadinessRow {
  approval_id: string;
  status: 'READY' | 'INCOMPLETE' | 'INDETERMINATE' | 'UNSUPPORTED' | string;
  mandatory_total: number;
  mandatory_satisfied: number;
  missing_requirement_ids: string[];
  indeterminate_requirement_ids: string[];
  unsupported_requirement_ids: string[];
  supporting_missing_requirement_ids: string[];
  reasons: string[];
}

export interface DocumentReadinessResponse {
  application_id: string;
  readiness: DocumentReadinessRow[];
  submissions: DocumentSubmissionResponse[];
  workflow?: any;
}
