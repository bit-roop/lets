import React, { useEffect, useMemo, useState } from 'react';
import { FileUp, Info, RefreshCw, UploadCloud } from 'lucide-react';
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

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MIME_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'image/jpeg': 'JPG',
  'image/png': 'PNG',
};

function humanFormats(formats?: string[]) {
  return (formats || []).map((format) => MIME_LABELS[format] || format).join(', ') || 'Not specified';
}

function suggestedFilename(name: string, formats?: string[]) {
  const stem = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'evidence';
  const extension = formats?.[0] === 'image/jpeg' ? 'jpg' : formats?.[0]?.split('/')[1] || 'pdf';
  return `${stem}.${extension}`;
}

function evidenceLabel(submission?: DocumentSubmissionResponse) {
  if (!submission) return 'Not provided';
  if (submission.state === 'PROVIDED_UNVALIDATED') return 'Uploaded — authenticity not verified';
  if (submission.state === 'VALID') return 'Accepted by the current M4 checks';
  if (submission.state === 'FORMAT_INVALID') return 'File format needs correction';
  if (submission.state === 'INVALID') return 'Evidence could not be accepted';
  if (submission.state === 'NEEDS_REVIEW') return 'Needs review';
  if (submission.state === 'NOT_PROVIDED') return 'Not provided';
  if (submission.state === 'REUSED_FROM') return 'Reused from another valid submission';
  return submission.state;
}

function validationLabel(status?: string) {
  if (status === 'FORMAT_ONLY') return 'Format checked only';
  if (status === 'FORMAT_INVALID') return 'File format needs correction';
  return status;
}

function obligationLabel(obligation: string) {
  if (obligation === 'MANDATORY') return 'Required evidence';
  if (obligation === 'CONDITIONAL') return 'May be required';
  if (obligation === 'SUPPORTING') return 'Supporting evidence';
  return obligation;
}

function itemKindLabel(itemKind?: string) {
  if (itemKind === 'UPLOAD_DOCUMENT') return 'Document upload';
  if (itemKind === 'FORM_INPUT') return 'Information to enter';
  if (itemKind === 'DECLARATION') return 'Declaration';
  if (itemKind === 'FEE') return 'Fee/payment item';
  if (itemKind === 'INSPECTION_EVENT') return 'Inspection item';
  return 'Evidence item';
}

function sourceStatusLabel(status: string) {
  if (status === 'VERIFIED') return 'Verified source';
  if (status === 'VERIFIED_SCOPE_UNCLEAR') return 'Source verified; scope unclear';
  if (status === 'SECONDARY') return 'Secondary source';
  if (status === 'UNSUPPORTED') return 'No authoritative checklist encoded';
  return status;
}

function factLabel(fact?: string) {
  return (fact || 'applicant information').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function friendlySubmissionError(message?: string) {
  const text = message || 'Please check the entry and try again.';
  if (text.includes('unsupported MIME type')) return 'The selected file type is not accepted. Please choose one of the listed formats.';
  if (text.includes('maximum size')) return 'The selected file is too large. Maximum allowed size is 10 MB.';
  if (text.includes('item_kind mismatch')) return 'This item cannot be submitted using that input type.';
  if (text.includes('unsupported and cannot be submitted')) return 'This item is not currently supported for submission.';
  if (text.includes('Unknown document_id')) return 'This evidence item is not available in the current checklist.';
  return text;
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
      const documentName = specs.find((item) => item.document_id === requirement.document_id)?.name || 'Evidence item';
      setMessage(`${documentName} uploaded — authenticity not verified.`);
      await refresh();
    } catch (err: any) {
      const documentName = specs.find((item) => item.document_id === requirement.document_id)?.name || 'this evidence item';
      setError(`Could not submit ${documentName}. ${friendlySubmissionError(err?.message)}`);
    }
  };

  const submitFormInput = async (requirement: DocumentRequirementRow, value: string, itemKind: 'FORM_INPUT' | 'DECLARATION' = 'FORM_INPUT') => {
    const response = value.trim();
    if (!response) {
      setError('Please enter the requested information before submitting.');
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await api.submitStructuredDocument({ application_id: applicationId, document_id: requirement.document_id, item_kind: itemKind, structured_data: { value: response } });
      const documentName = specs.find((item) => item.document_id === requirement.document_id)?.name || 'Information';
      setMessage(`${documentName} received — authenticity is not applicable to this information entry.`);
      await refresh();
    } catch (err: any) {
      const documentName = specs.find((item) => item.document_id === requirement.document_id)?.name || 'this information';
      setError(`Could not submit ${documentName}. ${friendlySubmissionError(err?.message)}`);
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
            <div>{(workflow.schedule.topological_order || Object.keys(workflow.schedule.nodes)).join(' → ')}</div>
            <div className="mt-1">Document readiness below uses this committed workflow context; provisional items do not silently gate it.</div>
          </div>
        )}
        {requirements.map((approval) => {
          const ready = readinessFor(approval.approval_id, readiness);
          const approvalName = evaluation.applicable.find((item) => item.requirement_id === approval.approval_id)?.name;
          return (
            <div key={approval.approval_id} className="border border-slate-200 rounded-md overflow-hidden">
              <div className="bg-slate-50 px-3 py-2 flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-bold text-slate-800">{approval.approval_id}{approvalName ? ` · ${approvalName}` : ''} evidence checklist</div>
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
  onForm: (requirement: DocumentRequirementRow, value: string, itemKind?: 'FORM_INPUT' | 'DECLARATION') => void;
}> = ({ requirement, spec, submissions, onFile, onForm }) => {
  const [formValue, setFormValue] = useState('');
  const [fileError, setFileError] = useState<string | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const conditionState = requirement.condition_state;
  const kind = obligationLabel(requirement.obligation);
  const scopeNote = requirement.verification_status === 'VERIFIED_SCOPE_UNCLEAR' ? 'Scope unclear; not universally mandatory.' : null;
  const submission = [...submissions].reverse().find((item) => item.document_id === requirement.document_id);
  const isConditionFalse = requirement.condition_state === 'FALSE';
  const isUnsupported = requirement.verification_status === 'UNSUPPORTED';
  const uploadFormats = spec?.accepted_formats || [];
  const uploadName = spec?.name || requirement.document_id;

  const handleFile = (file: File) => {
    setFileError(null);
    if (!uploadFormats.includes(file.type)) {
      setFileError(`Unsupported file type. Please upload: ${humanFormats(uploadFormats)}.`);
      setInputKey((key) => key + 1);
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setFileError('File is too large. Maximum allowed size is 10 MB.');
      setInputKey((key) => key + 1);
      return;
    }
    onFile(requirement, file);
  };
  return (
    <div className="px-3 py-3 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-800">{spec?.name || requirement.document_id}</div>
          <div className="text-[11px] text-slate-600">{kind} · {itemKindLabel(spec?.item_kind)}</div>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Requirement source: {sourceStatusLabel(requirement.verification_status)}</span>
      </div>
      {requirement.condition && conditionState === 'TRUE' && <div className="text-[11px] text-emerald-800">Required because: {requirement.condition_description || 'the current applicant information matches this condition.'}</div>}
      {requirement.condition && conditionState === 'FALSE' && <div className="text-[11px] text-slate-600">Not applicable based on the information provided.</div>}
      {requirement.condition && conditionState === 'UNKNOWN' && <div className="text-[11px] text-amber-800"><strong>More information needed.</strong> This item may be required depending on {requirement.condition_description?.toLowerCase() || 'additional applicant information'}. Information needed: {factLabel(requirement.condition?.fact).toLowerCase()}.</div>}
      {scopeNote && <div className="text-[11px] text-amber-800">{scopeNote}</div>}
      <div className="border-l-2 border-gov-gold pl-2 text-[11px] text-slate-700">
        <div className="font-bold uppercase tracking-wide text-[10px] text-slate-500">Applicant evidence status</div>
        <div className="font-semibold">{evidenceLabel(submission)}</div>
        {submission?.filename && <div>Filename: {submission.filename}</div>}
        {submission?.validation?.status && <div>Backend validation: {submission.validation.status === 'FORMAT_ONLY' ? 'Format checked only' : submission.validation.status}</div>}
      </div>
      <div className="text-[11px] text-slate-500">Official source: {requirement.source.authority}</div>
      <div className="text-[11px] text-slate-500">Checklist reference: {requirement.source.checklist_item || 'source reference recorded'}</div>
      {requirement.source.url && <a className="text-[11px] text-blue-700 underline" href={requirement.source.url} target="_blank" rel="noreferrer">Open official source</a>}
      {requirement.obligation === 'SUPPORTING' && <div className="text-[11px] text-slate-500">Supporting evidence is non-blocking for readiness.</div>}
      {isConditionFalse ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Not required for the current applicant facts.</div>
      ) : isUnsupported ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Unsupported item — no verified requirement is encoded and no submission is accepted.</div>
      ) : spec?.item_kind === 'UPLOAD_DOCUMENT' ? (
        <div className="space-y-2 bg-slate-50 rounded p-2">
          <div className="text-[11px] text-slate-700">Upload the applicant evidence for this requirement.</div>
          <div className="text-[11px] text-slate-600">Accepted formats: <strong>{humanFormats(uploadFormats)}</strong> · Maximum size: <strong>10 MB</strong></div>
          <div className="text-[11px] text-slate-500">Suggested filename: <span className="font-mono">{suggestedFilename(uploadName, uploadFormats)}</span> <span>(guidance only)</span></div>
          {fileError && <div role="alert" className="text-[11px] text-rose-800 bg-rose-50 border border-rose-200 rounded p-2">{fileError}</div>}
          <label htmlFor={`upload-${requirement.requirement_id}`} className="inline-flex items-center gap-2 text-xs font-semibold text-gov-navy cursor-pointer">
            <UploadCloud className="w-3.5 h-3.5" /> Choose file
            <input key={inputKey} id={`upload-${requirement.requirement_id}`} type="file" className="hidden" accept={uploadFormats.join(',')} aria-label={`Upload ${uploadName}`} onChange={(event) => { const file = event.target.files?.[0]; if (file) handleFile(file); }} />
          </label>
        </div>
      ) : spec?.item_kind === 'FORM_INPUT' ? (
        <div className="space-y-1.5"><div className="text-[11px] text-slate-700">What to provide: {spec.description}</div><FormInput value={formValue} setValue={setFormValue} onSubmit={() => onForm(requirement, formValue, 'FORM_INPUT')} /></div>
      ) : spec?.item_kind === 'FEE' ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Fee item — no document upload is requested here.</div>
      ) : spec?.item_kind === 'INSPECTION_EVENT' ? (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">Inspection event — no document upload is requested here.</div>
      ) : spec?.item_kind === 'DECLARATION' ? (
        <div className="space-y-1.5"><div className="text-[11px] text-slate-700">What to declare: {spec.description}</div><FormInput value={formValue} setValue={setFormValue} onSubmit={() => onForm(requirement, formValue, 'DECLARATION')} /></div>
      ) : (
        <div className="text-[11px] text-slate-600 bg-slate-50 rounded p-2">This item type is not available for upload in the current M4 UI.</div>
      )}
    </div>
  );
};

const FormInput: React.FC<{ value: string; setValue: (value: string) => void; onSubmit: () => void }> = ({ value, setValue, onSubmit }) => (
  <div className="flex flex-col sm:flex-row gap-2">
    <div className="flex-1"><label className="block text-[11px] font-semibold text-slate-700 mb-1">What information do you need to provide?</label><textarea value={value} placeholder="Enter your response here" onChange={(event) => setValue(event.target.value)} rows={2} className="w-full border border-slate-300 rounded px-2 py-1.5 text-[11px]" aria-label="Applicant response" /><div className="text-[10px] text-slate-500 mt-1">Your response will be recorded as supplied information. It is not authenticity-verified.</div></div>
    <button onClick={onSubmit} className="self-start px-2.5 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold">Submit input</button>
  </div>
);
