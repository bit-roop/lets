export interface SlaInfo {
  kind: 'STANDARD' | 'ZERO_DURATION' | 'UNSPECIFIED' | 'INVALID';
  days: number | null;
  raw_value: any;
  source: string;
  excluded_from_duration: boolean;
  note: string | null;
}

export interface WorkflowNode {
  requirement_id: string;
  name: string;
  requirement_type: string;
  department: string | null;
  authority: string | null;
  statute: string | null;
  state: string;
  confidence: string;
  sla: SlaInfo;
  inclusion: 'SCHEDULED' | 'PROVISIONAL' | 'EXCLUDED';
  inclusion_reason: string;
  missing_facts: string[];
  missing_fact_origin: Record<string, string>;
  quantity: any;
  document_slots: any[];
}

export interface WorkflowEdge {
  from_id: string;
  to_id: string;
  dependency_type: string;
  verification_status: string;
  basis: string | null;
  admitted: boolean;
  admission_reason: string;
  origin: string;
  dropped: boolean;
  dropped_reason: string | null;
}

export interface ScheduledNode {
  requirement_id: string;
  earliest_start_day: number;
  earliest_finish_day: number;
  latest_start_day: number | null;
  latest_finish_day: number | null;
  slack_days: number | null;
  on_critical_path: boolean;
  depth: number;
  duration_days: number;
  duration_is_lower_bound: boolean;
  blocks: string[];
  blocks_transitively: string[];
  blocked_by: string[];
}

export interface Schedule {
  label: 'COMMITTED' | 'PROVISIONAL';
  scope_note: string;
  topological_order: string[];
  parallel_bands: string[][];
  nodes: Record<string, ScheduledNode>;
  sequential_duration_days: number;
  parallel_duration_days: number;
  critical_paths: string[][];
  critical_path_duration_days: number;
  duration_completeness: 'COMPLETE' | 'PARTIAL';
  excluded_from_duration: string[];
  schedule_confidence: string;
  confidence_basis: string;
  duration_unit: string;
}

export interface ProvisionalDeltaDetail {
  requirement_id: string;
  name: string;
  requirement_type: string;
  department: string | null;
  state: string;
  sla_kind: string;
  sla_days: number | null;
  duration_days: number;
  earliest_start_day: number;
  earliest_finish_day: number;
  on_provisional_critical_path: boolean;
  missing_facts: string[];
  blocked_by: string[];
  blocks: string[];
  explanation: string;
}

export interface ProvisionalDelta {
  additional_requirements: ProvisionalDeltaDetail[];
  additional_node_count: number;
  committed_duration_days: number;
  provisional_duration_days: number;
  critical_path_change_days: number;
  committed_critical_paths: string[][];
  provisional_critical_paths: string[][];
  critical_path_changed: boolean;
  unlocked_by_facts: string[];
  summary_explanation: string;
}

export interface WorkflowResult {
  workflow_version: string;
  generated_for: Record<string, any>;
  nodes: Record<string, WorkflowNode>;
  edges: WorkflowEdge[];
  schedule: Schedule | null;
  provisional_schedule: Schedule | null;
  provisional_delta: ProvisionalDelta | null;
  cycles: string[][];
  graph_diagnostics: Record<string, any>;
  warnings: { type: string; severity: string; message: string; [k: string]: any }[];
}

export interface EvaluateWithWorkflowResponse {
  evaluation: Record<string, any>;
  workflow: WorkflowResult;
}