import { ApplicantFacts } from '../types/facts';
import { EvaluationResponse } from '../types/engine';

export interface CaseRecord {
  id: string;
  submittedAt: string;
  businessName: string;
  asOfDate: string;
  facts: ApplicantFacts;
  evaluationResult: EvaluationResponse;
}

const STORAGE_KEY = 'compliance_cases_v1';

export function saveCase(facts: ApplicantFacts, evaluationResult: EvaluationResponse): CaseRecord {
  const record: CaseRecord = {
    id: `${Date.now()}`,
    submittedAt: new Date().toISOString(),
    businessName: facts._name || facts.entity_name || 'Unnamed business',
    asOfDate: evaluationResult.as_of,
    facts,
    evaluationResult,
  };
  const updated = [record, ...getCases()].slice(0, 50);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return record;
}

export function getCases(): CaseRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function getCaseById(id: string): CaseRecord | undefined {
  return getCases().find((c) => c.id === id);
}

export function clearCases(): void {
  localStorage.removeItem(STORAGE_KEY);
}