import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, FileUp, Info, RefreshCw, UploadCloud } from 'lucide-react';
import { api, DocumentApprovalResult, DocumentReadinessResponse, DocumentRequirementRow, DocumentRequirementsResponse, DocumentSubmissionResponse } from '../../api/client';
import { ApplicantFacts } from '../../types/facts';
import { EvaluationResponse } from '../../types/engine';

interface Props {
  facts: ApplicantFacts;
  evaluation: EvaluationResponse;
}

function readinessFor(approvalId: string, response: DocumentReadinessResponse | null) {
  return response?.readiness.find((item) => item.approval_id === approvalId);
}

function statusTone(status?: string) {
  if (status === 'READY') return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (status === 'UNSUPPORTED') return 'text-slate-700 bg-slate-100 border-slate-300';
  if (status === 'INDETERMINATE') return 'text-amber-800 bg-amber-50 border-amber-200';
  return 'text-rose-800 bg-rose-50 border-rose-200';
}

export const DocumentReadinessPanel: React.FC<Props> = ({ facts, evaluation }) => {
  const approvalIds = useMemo(() => evaluation.applicable.map((item) => item.requirement_id), [evaluation.applicable]);
  const applicationId = useMemo(
    () => `local-${facts._name || facts.entity_name || 'assessment'}`.replace(/[^a-zA-Z0-9_-]/g, '-'),
    [facts._name, facts.entity_name]
  );
  const [requirements, setRequirements] = useState<DocumentApprovalResult[]>([]);
  const [specs, setSpecs] = useState<DocumentRequirementsResponse['specs']>([]);
  const [workflow, setWorkflow] = useState<any>(null);
  const [readiness, setReadiness] = useState<DocumentReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [requirementsResult, readinessResult, registryResult] = await Promise.all([
        api.evaluateDocumentRequirements({ facts, approval_ids: approvalIds, workflow_aware: true, include_provisional: true }),
        api.getDocumentReadiness(applicationId, facts, approvalIds),
        api.getDocumentRequirements(),
      ]);
      if (
        !Array.isArray(requirementsResult.approvals) ||
        !Array.isArray(readinessResult.readiness) ||
        !Array.isArray(readinessResult.submissions) ||
        !Array.isArray(registryResult.specs)
      ) {
        throw new Error('Backend returned an invalid M4 response. Please refresh and try again.');
      }
      setRequirements(requirementsResult.approvals);
      setReadiness(readinessResult);
      setSpecs(registryResult.specs);
      setWorkflow(requirementsResult.workflow || readinessResult.workflow || null);
    } catch (err: any) {
      setError(err?.message || 'Could not load document requirements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (approvalIds.length > 0) refresh();
    else {
      setRequirements([]);
      setReadiness(null);
    }
    // Refresh when the engine produces a new applicable set or applicant identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [approvalIds.join('|'), applicationId, evaluation.as_of, facts]);

  const submitFile = async (requirement: DocumentRequirementRow, file: File) => {
    const form = new FormData();
    form.append('application_id', applicationId);
    form.append('document_id', requirement.document_id);
    form.append('item_kind', 'UPLOAD_DOCUMENT');
    form.append('file', file);
    setError(null);
    setMessage(null);
    try {
      const result = await api.submitDocument(form);
      setMessage(`${requirement.document_id}: ${result.state}. Upload presence recorded; authenticity is not verified.`);
      await refresh();
    } catch (err: any) {
      setError(err?.message || 'Evidence submission failed.');
    }
  };

  const submitFormInput = async (requirement: DocumentRequirementRow, value: string) => {
    let structuredData: Record<string, any>;
    try {
      structuredData = JSON.parse(value || '{}');
      if (!structuredData || Array.isArray(structuredData) || typeof structuredData !== 'object') throw new Error();
    } catch {
      setError('Form input must be a JSON object, for example {"value":"provided"}.');
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const result = await api.submitStructuredDocument({ application_id: applicationId, document_id: requirement.document_id, item_kind: 'FORM_INPUT', structured_data: structuredData });
      setMessage(`${requirement.document_id}: ${result.state}. Structured data was received; authenticity is not verified.`);
      await refresh();
    } catch (err: any) {
      setError(err?.message || 'Form input submission failed.');
    }
  };

  if (approvalIds.length === 0) return null;

  return (
    <section className="bg-white border border-slate-300 rounded-md shadow-sm p-4 space-y-4" aria-label="Document readiness">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <FileUp className="w-4 h-4 text-gov-navy" />
            <h2 className="text-sm font-bold text-gov-navy">Evidence & Document Readiness</h2>
          </div>
          <p className="text-xs text-slate-600 mt-1">M4 records required evidence and submission presence. Uploading a file does not prove authenticity.</p>
        </div>
        <button onClick={refresh} disabled={loading} className="text-xs font-semibold text-gov-navy flex items-center gap-1.5 disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded p-2">{error}</div>}
      {message && <div className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded p-2">{message}</div>}

      <div className="space-y-4">
        {workflow?.schedule?.nodes && (
          <div className="bg-slate-50 border border-slate-200 rounded p-3 text-[11px] text-slate-600">
            <div className="font-bold text-slate-800 mb-1">M3 committed workflow scope</div>
            <div>{Object.keys(workflow.schedule.nodes).join(' → ')}</div>
            <div className="mt-1">Document readiness below uses this committed workflow context; provisional items do not silently gate it.</div>
          </div>
        )}
        {requirements.map((approval) => {
          const ready = readinessFor(approval.approval_id, readiness);
          return (
            <div key={approval.approval_id} className="border border-slate-200 rounded-md overflow-hidden">
              <div className="bg-slate-50 px-3 py-2 flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-bold text-slate-800">{approval.approval_id} evidence checklist</div>
                <span className={`text-[11px] font-bold px-2 py-1 border rounded ${statusTone(ready?.status || approval.coverage.status === 'UNSUPPORTED' ? (ready?.status || 'UNSUPPORTED') : undefined)}`}>
                  Readiness: {ready?.status || 'LOADING'}
                </span>
              </div>
              {approval.coverage.status === 'UNSUPPORTED' ? (
                <div className="p-3 text-xs text-slate-600 flex items-start gap-2"><Info className="w-3.5 h-3.5 mt-0.5" /> No authoritative M4 checklist is encoded for this approval.</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {approval.requirements.map((requirement) => {
                    const spec = specs.find((item) => item.document_id === requirement.document_id);
                    return <RequirementRow key={requirement.requirement_id} requirement={requirement} spec={spec} submissions={readiness?.submissions || []} onFile={submitFile} onForm={submitFormInput} />;
                  })}
                </div>
              )}
              {ready?.reasons?.length ? <div className="px-3 py-2 bg-slate-50 text-[11px] text-slate-600">{ready.reasons.join(' ')}</div> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
};

const RequirementRow: React.FC<{
  requirement: DocumentRequirementRow;
  spec?: DocumentRequirementsResponse['specs'][number];
  submissions: DocumentSubmissionResponse[];
  onFile: (requirement: DocumentRequirementRow, file: File) => void;
  onForm: (requirement: DocumentRequirementRow, value: string) => void;
}> = ({ requirement, spec, submissions, onFile, onForm }) => {
  const [formValue, setFormValue] = useState('{"value":""}');
  const kind = requirement.condition ? `${requirement.obligation} · ${requirement.condition_state || 'UNKNOWN'}` : requirement.obligation;
  const scopeNote = requirement.verification_status === 'VERIFIED_SCOPE_UNCLEAR' ? 'Scope unclear; not universally mandatory.' : null;
  const submission = [...submissions].reverse().find((item) => item.document_id === requirement.document_id);
  return (
    <div className="px-3 py-3 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-800">{spec?.name || requirement.document_id}</div>
          <div className="text-[11px] text-slate-600">{kind} · {spec?.item_kind || 'ITEM_KIND_UNAVAILABLE'}</div>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{requirement.verification_status}</span>
      </div>
      {requirement.condition_description && <div className="text-[11px] text-amber-800">Condition: {requirement.condition_description}</div>}
      {scopeNote && <div className="text-[11px] text-amber-800">{scopeNote}</div>}
      <div className="text-[11px] text-slate-600">Supplied: <strong>{submission ? 'Yes' : 'No'}</strong>{submission ? ` · ${submission.state}${submission.validation?.status ? ` · ${submission.validation.status}` : ''}` : ''}</div>
      <div className="text-[11px] text-slate-500">Source: {requirement.source.source_id} · {requirement.source.checklist_item || 'source reference recorded'}</div>
      {requirement.source.url && <a className="text-[11px] text-blue-700 underline" href={requirement.source.url} target="_blank" rel="noreferrer">Open official source</a>}
      {requirement.obligation === 'SUPPORTING' && <div className="text-[11px] text-slate-500">Supporting evidence is non-blocking for readiness.</div>}
      {spec?.item_kind === 'FORM_INPUT' ? (
        <FormInput value={formValue} setValue={setFormValue} onSubmit={() => onForm(requirement, formValue)} />
      ) : spec?.item_kind === 'FEE' ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Fee item — no document upload is requested here.</div>
      ) : spec?.item_kind === 'INSPECTION_EVENT' ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Inspection event — no document upload is requested here.</div>
      ) : spec?.item_kind === 'DECLARATION' ? (
        <FormInput value={formValue} setValue={setFormValue} onSubmit={() => onForm(requirement, formValue)} />
      ) : requirement.verification_status === 'UNSUPPORTED' ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Unsupported item — no verified requirement is encoded.</div>
      ) : (
        <label className="inline-flex items-center gap-2 text-xs font-semibold text-gov-navy cursor-pointer">
          <UploadCloud className="w-3.5 h-3.5" /> Choose file
          <input type="file" className="hidden" accept={spec?.accepted_formats?.map((format) => format.split('/')[1]).join(',') || '.pdf,.png,.jpg,.jpeg'} onChange={(event) => { const file = event.target.files?.[0]; if (file) onFile(requirement, file); }} />
        </label>
      )}
    </div>
  );
};

const FormInput: React.FC<{ value: string; setValue: (value: string) => void; onSubmit: () => void }> = ({ value, setValue, onSubmit }) => (
  <div className="flex flex-col sm:flex-row gap-2">
    <textarea value={value} onChange={(event) => setValue(event.target.value)} rows={2} className="flex-1 border border-slate-300 rounded px-2 py-1.5 text-[11px] font-mono" aria-label="Structured form input" />
    <button onClick={onSubmit} className="self-start px-2.5 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold">Submit input</button>
  </div>
);
