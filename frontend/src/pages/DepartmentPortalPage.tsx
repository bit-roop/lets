import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Inbox, MessageSquareWarning, RefreshCw, XCircle } from 'lucide-react';
import {
  api,
  DepartmentCaseDetail,
  DepartmentCaseSummary,
  DepartmentInfo,
} from '../api/client';
import { Breadcrumb } from '../components/common/Breadcrumb';
import {
  ApplicationStatusBadge,
  ApprovalStatusBadge,
  Expandable,
  QueryStatusBadge,
  ReadinessBadge,
} from '../components/lifecycle/LifecycleStatus';

const DEFAULT_DEPARTMENTS: DepartmentInfo[] = [
  { department: 'DISH', label: 'Directorate of Industrial Safety and Health (Prototype Simulation)' },
  { department: 'FSSAI', label: 'Food Safety and Standards Authority (Prototype Simulation)' },
];

function evidenceStateLabel(state?: string | null) {
  if (!state) return 'Not provided';
  if (state === 'PROVIDED_UNVALIDATED') return 'Uploaded';
  if (state === 'VALID') return 'Accepted by the M4 checks';
  if (state === 'FORMAT_INVALID') return 'Format needs correction';
  if (state === 'NEEDS_REVIEW') return 'Needs review';
  return state;
}

function checkOutcomeLabel(outcome?: string | null) {
  if (!outcome) return 'Not examined by the automated checks';
  if (outcome === 'ACCEPTED_FOR_REVIEW') return 'Expected evidence present and readable';
  if (outcome === 'NEEDS_APPLICANT_ACTION') return 'Needs applicant action';
  if (outcome === 'NEEDS_HUMAN_REVIEW') return 'Needs a person to check';
  return outcome.replace(/_/g, ' ').toLowerCase();
}

export const DepartmentPortalPage: React.FC = () => {
  const [departments, setDepartments] = useState<DepartmentInfo[]>(DEFAULT_DEPARTMENTS);
  const [department, setDepartment] = useState<string>('FSSAI');
  const [cases, setCases] = useState<DepartmentCaseSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DepartmentCaseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    api.listDepartments()
      .then((res) => setDepartments(res.departments || DEFAULT_DEPARTMENTS))
      .catch(() => setDepartments(DEFAULT_DEPARTMENTS));
  }, []);

  const loadCases = async (dept: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listDepartmentCases(dept);
      setCases(res.cases || []);
      if (res.cases?.length) {
        const stillPresent = res.cases.some((item) => item.application_id === selectedId);
        if (!stillPresent) setSelectedId(res.cases[0].application_id);
      } else {
        setSelectedId(null);
        setDetail(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Could not load cases for this department.');
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (dept: string, applicationId: string) => {
    setError(null);
    try {
      setDetail(await api.getDepartmentCase(dept, applicationId));
    } catch (err: any) {
      setError(err?.message || 'Could not open this case.');
      setDetail(null);
    }
  };

  useEffect(() => {
    loadCases(department);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [department]);

  useEffect(() => {
    if (selectedId) loadDetail(department, selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, department]);

  const refreshAll = async () => {
    await loadCases(department);
    if (selectedId) await loadDetail(department, selectedId);
  };

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
      setNotice(label);
      await refreshAll();
    } catch (err: any) {
      setError(err?.message || 'That action could not be completed.');
    }
  };

  const needsAttention = useMemo(
    () => cases.filter((c) => c.responded_query_count > 0 || c.application_status === 'SUBMITTED'),
    [cases]
  );

  return (
    <div>
      <Breadcrumb items={[{ label: 'Portal Gateway', step: 0 }, { label: 'Department Review Simulation' }]} />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-slate-300">
          <div>
            <h1 className="text-xl font-bold text-gov-navy">Department review simulation</h1>
            <p className="text-xs text-slate-600 mt-1 max-w-2xl">
              An officer view over cases filed in this prototype. Decisions recorded here are simulated:
              nothing is submitted to a government department and no approval is officially granted.
            </p>
          </div>
          <button
            onClick={refreshAll}
            disabled={loading}
            className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 flex items-center gap-1.5 shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-600">Reviewing as</span>
          {departments.map((entry) => (
            <button
              key={entry.department}
              onClick={() => setDepartment(entry.department)}
              className={`px-3 py-1.5 rounded text-xs font-bold border transition ${
                department === entry.department
                  ? 'bg-gov-navy text-white border-gov-navy'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {entry.department}
            </button>
          ))}
          <span className="text-[11px] text-slate-500">
            {departments.find((d) => d.department === department)?.label}
          </span>
        </div>

        {error && (
          <div role="alert" className="text-xs text-rose-900 bg-rose-50 border border-rose-200 rounded p-3">
            {error}
          </div>
        )}
        {notice && (
          <div className="text-xs text-emerald-900 bg-emerald-50 border border-emerald-200 rounded p-3">
            {notice}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Case queue */}
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <h2 className="text-xs font-bold text-gov-navy">Cases for {department}</h2>
              <span className="text-[11px] text-slate-500">
                {needsAttention.length} of {cases.length} need attention
              </span>
            </div>

            {cases.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded p-6 text-center text-xs text-slate-500">
                <Inbox className="w-5 h-5 mx-auto text-slate-400 mb-2" />
                No cases have been filed for {department} yet. Complete an assessment and submit an
                application to see one here.
              </div>
            ) : (
              cases.map((item) => (
                <button
                  key={item.application_id}
                  onClick={() => setSelectedId(item.application_id)}
                  className={`w-full text-left bg-white border rounded p-3 transition ${
                    selectedId === item.application_id
                      ? 'border-gov-navy ring-1 ring-gov-navy/20'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-mono font-bold text-gov-navy">
                      {item.tracking_reference}
                    </span>
                    {item.open_query_count + item.responded_query_count > 0 && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-900 bg-amber-50 border border-amber-300 rounded px-1.5 py-0.5">
                        <MessageSquareWarning className="w-3 h-3" />
                        {item.open_query_count > 0 ? 'Query open' : 'Response waiting'}
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-slate-800 mt-1">{item.entity_name}</div>
                  <div className="mt-1.5">
                    <ApplicationStatusBadge status={item.application_status} />
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1.5">
                    {item.approvals.length} approval{item.approvals.length === 1 ? '' : 's'} for {department} ·{' '}
                    {item.submissions_count} evidence item{item.submissions_count === 1 ? '' : 's'}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Case detail */}
          <div className="lg:col-span-2 space-y-4">
            {!detail ? (
              <div className="bg-white border border-slate-200 rounded p-8 text-center text-xs text-slate-500">
                Select a case to review it.
              </div>
            ) : (
              <>
                <div className="bg-white border border-slate-300 border-l-4 border-l-gov-gold rounded p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h2 className="text-base font-bold text-gov-navy">{detail.entity_name}</h2>
                      <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                        {detail.tracking_reference} · assessed as of {detail.as_of}
                      </div>
                    </div>
                    <ApplicationStatusBadge status={detail.application_status} />
                  </div>
                </div>

                {/* Approvals and officer actions */}
                <section className="bg-white border border-slate-300 rounded p-4 space-y-3">
                  <h3 className="text-xs font-bold text-gov-navy">
                    Approvals you are reviewing
                  </h3>
                  {detail.approvals.map((approval) => (
                    <ApprovalActionRow
                      key={approval.approval_id}
                      detail={detail}
                      approval={approval}
                      onAct={act}
                    />
                  ))}
                </section>

                {/* Evidence */}
                <section className="bg-white border border-slate-300 rounded p-4 space-y-2">
                  <h3 className="text-xs font-bold text-gov-navy">Evidence submitted</h3>
                  {detail.evidence.length === 0 ? (
                    <p className="text-xs text-slate-500">No evidence items are attached to this case.</p>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {detail.evidence.map((item) => (
                        <div key={item.submission_reference + item.document_id} className="py-2">
                          <div className="text-xs font-semibold text-slate-800">{item.document_id}</div>
                          <div className="text-[11px] text-slate-600 mt-0.5">
                            {evidenceStateLabel(item.evidence_state)} · automated check:{' '}
                            {checkOutcomeLabel(item.automated_check_outcome)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-[11px] text-slate-500 border-t border-slate-200 pt-2">
                    {detail.evidence_notice}
                  </p>
                </section>

                {/* Queries */}
                <section className="bg-white border border-slate-300 rounded p-4 space-y-3">
                  <h3 className="text-xs font-bold text-gov-navy">Queries</h3>
                  {detail.queries.length === 0 ? (
                    <p className="text-xs text-slate-500">No query has been raised on this case.</p>
                  ) : (
                    detail.queries.map((query) => (
                      <div key={query.query_id} className="border border-slate-200 rounded p-3 space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-800">
                            {query.approval_name || query.approval_id}
                          </span>
                          <QueryStatusBadge status={query.status} />
                        </div>
                        <p className="text-xs text-slate-700">{query.query_text}</p>
                        <div className="text-[11px] text-slate-500">Response due {query.deadline}</div>

                        {query.response_text ? (
                          <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                            <div className="text-[11px] font-semibold text-slate-700">
                              Applicant response
                            </div>
                            <p className="text-xs text-slate-800 mt-1">{query.response_text}</p>
                            {query.response_document_id && (
                              <div className="text-[11px] text-slate-500 mt-1">
                                Replacement document referenced: {query.response_document_id}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-[11px] text-slate-500">Awaiting the applicant.</div>
                        )}

                        {query.status === 'RESPONDED' && (
                          <ResolveQueryForm detail={detail} queryId={query.query_id} onAct={act} />
                        )}
                        {query.resolution_note && (
                          <div className="text-[11px] text-slate-600">
                            Closing note: {query.resolution_note}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </section>

                <section className="bg-white border border-slate-300 rounded p-4">
                  <h3 className="text-xs font-bold text-gov-navy">Case history and timeline</h3>
                  <Expandable label="View details">
                    <div className="space-y-1.5">
                      {detail.events.length === 0 ? (
                        <p className="text-xs text-slate-500">No activity recorded yet.</p>
                      ) : (
                        detail.events.map((event) => (
                          <div key={event.event_id} className="text-[11px] text-slate-600">
                            <span className="font-mono text-slate-400">
                              {new Date(event.created_at).toLocaleString()}
                            </span>{' '}
                            — {event.detail || event.event_type}
                          </div>
                        ))
                      )}
                      {detail.timeline && 'summary' in detail.timeline && (
                        <div className="text-[11px] text-slate-600 border-t border-slate-200 pt-2 mt-2">
                          Sequencing from the approval plan recorded when this case was filed:{' '}
                          {(detail.timeline as any).phase_1_immediate?.count ?? 0} can start immediately,{' '}
                          {(detail.timeline as any).phase_2_sequential?.count ?? 0} follow preconditions.
                        </div>
                      )}
                    </div>
                  </Expandable>
                </section>

                <p className="text-[11px] text-slate-500">{detail.simulation_notice}</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const ApprovalActionRow: React.FC<{
  detail: DepartmentCaseDetail;
  approval: DepartmentCaseDetail['approvals'][number];
  onAct: (label: string, fn: () => Promise<unknown>) => Promise<void>;
}> = ({ detail, approval, onAct }) => {
  const [showQuery, setShowQuery] = useState(false);
  const [queryText, setQueryText] = useState('');
  const [deadline, setDeadline] = useState('');
  const [note, setNote] = useState('');

  const id = detail.application_id;
  const dept = detail.department;

  return (
    <div className="border border-slate-200 rounded p-3 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-xs font-semibold text-slate-800">
            {approval.name || approval.approval_id}
          </div>
          <div className="text-[11px] text-slate-500">
            {approval.approval_id}
            {approval.sla_days ? ` · published service timeline ${approval.sla_days} days` : ''}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <ReadinessBadge status={approval.readiness_status} />
          <ApprovalStatusBadge status={approval.status} />
        </div>
      </div>

      {approval.status === 'SUBMITTED' && (
        <button
          onClick={() => onAct('Review started.', () => api.startReview(id, approval.approval_id, dept))}
          className="px-3 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold"
        >
          Start review
        </button>
      )}

      {approval.status === 'IN_SCRUTINY' && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() =>
                onAct('Granted in simulation.', () =>
                  api.grantApproval(id, approval.approval_id, dept, note || undefined)
                )
              }
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-700 text-white text-[11px] font-bold"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Grant in simulation
            </button>
            <button
              onClick={() =>
                onAct('Rejected in simulation.', () =>
                  api.rejectApproval(id, approval.approval_id, dept, note || undefined)
                )
              }
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-white text-rose-800 border border-rose-300 text-[11px] font-bold"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject in simulation
            </button>
            <button
              onClick={() => setShowQuery((value) => !value)}
              className="px-3 py-1.5 rounded bg-white text-slate-700 border border-slate-300 text-[11px] font-bold"
            >
              {showQuery ? 'Cancel query' : 'Raise a query'}
            </button>
          </div>

          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note recorded with the decision"
            aria-label="Decision note"
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-[11px]"
          />

          {showQuery && (
            <div className="bg-slate-50 border border-slate-200 rounded p-2.5 space-y-2">
              <label className="block text-[11px] font-semibold text-slate-700">
                What do you need from the applicant?
                <textarea
                  value={queryText}
                  onChange={(event) => setQueryText(event.target.value)}
                  rows={2}
                  className="mt-1 w-full border border-slate-300 rounded px-2 py-1.5 text-[11px] font-normal"
                />
              </label>
              <label className="block text-[11px] font-semibold text-slate-700">
                Response due by
                <input
                  type="date"
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                  className="mt-1 block border border-slate-300 rounded px-2 py-1.5 text-[11px] font-normal"
                />
              </label>
              <button
                onClick={() =>
                  onAct('Query sent to the applicant.', async () => {
                    await api.raiseQuery(id, {
                      approval_id: approval.approval_id,
                      department: dept,
                      query_text: queryText,
                      deadline,
                    });
                    setQueryText('');
                    setDeadline('');
                    setShowQuery(false);
                  })
                }
                className="px-3 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold"
              >
                Send query
              </button>
            </div>
          )}
        </div>
      )}

      {approval.status === 'QUERY_PENDING' && (
        <p className="text-[11px] text-amber-900">
          Waiting for the applicant to respond. Review resumes once you accept their response below.
        </p>
      )}

      {(approval.status === 'GRANTED' || approval.status === 'REJECTED') && (
        <p className="text-[11px] text-slate-600">
          Prototype department decision recorded
          {approval.decided_at ? ` on ${new Date(approval.decided_at).toLocaleDateString()}` : ''}.
          {approval.decision_note ? ` Note: ${approval.decision_note}` : ''}
        </p>
      )}
    </div>
  );
};

const ResolveQueryForm: React.FC<{
  detail: DepartmentCaseDetail;
  queryId: string;
  onAct: (label: string, fn: () => Promise<unknown>) => Promise<void>;
}> = ({ detail, queryId, onAct }) => {
  const [note, setNote] = useState('');
  return (
    <div className="flex flex-col sm:flex-row gap-2">
      <input
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="Optional closing note"
        aria-label="Query closing note"
        className="flex-1 border border-slate-300 rounded px-2 py-1.5 text-[11px]"
      />
      <button
        onClick={() =>
          onAct('Response accepted. Review has resumed.', () =>
            api.resolveQuery(detail.application_id, queryId, detail.department, note || undefined)
          )
        }
        className="px-3 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold shrink-0"
      >
        Accept response and resume review
      </button>
    </div>
  );
};


