import { EvaluationResponse, HealthResponse } from '../types/engine';
import { ApplicantFacts } from '../types/facts';

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
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
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
};
