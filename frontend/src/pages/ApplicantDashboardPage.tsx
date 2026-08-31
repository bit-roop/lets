import React, { useEffect, useMemo, useState } from 'react';
import { MessageSquareWarning, RefreshCw, RotateCcw } from 'lucide-react';
import { api, ApplicationRecord, ApplicationSummary, QueryView } from '../api/client';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import {
  ApplicationStatusBadge,
  ApprovalStatusBadge,
  Expandable,
  JourneyRail,
  QueryStatusBadge,
  ReadinessBadge,
} from '../components/lifecycle/LifecycleStatus';

interface Props {
  initialApplicationId?: string | null;
}

/** Where the case sits on the journey rail shown at the top of the page. */
function journeyIndex(status?: string): number {
  switch (status) {
    case 'GRANTED':
    case 'REJECTED':
      return 6;
    case 'UNDER_REVIEW':
    case 'QUERY_RAISED':
    case 'RESPONDED':
      return 5;
    default:
      return 4;
  }
}

export const ApplicantDashboardPage: React.FC<Props> = ({ initialApplicationId }) => {
  const { goToStep, resetAssessment } = useAssessment();
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(initialApplicationId || null);
  const [application, setApplication] = useState<ApplicationRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchList = async () => {
    try {
      const res = await api.listApplications();
      const list = res.applications || [];
      setApplications(list);
      if (list.length > 0) {
        if (!selectedAppId) {
          setSelectedAppId(list[0].application_id);
        }
      } else if (!selectedAppId) {
        setLoading(false);
        setApplication(null);
      }
    } catch (err: any) {
      if (!selectedAppId) {
        setError(err?.message || 'Could not load application cases.');
        setLoading(false);
      }
    }
  };

  const fetchDetail = async (appId: string) => {
    setLoading(true);
    setError(null);
    try {
      setApplication(await api.getApplication(appId));
    } catch (err: any) {
      setError(err?.message || 'Could not load this application case.');
      setApplication(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedAppId) {
      fetchDetail(selectedAppId);
    } else {
      setApplication(null);
    }
  }, [selectedAppId]);

  const lifecycle = application?.lifecycle || null;
  const status = lifecycle?.application_status || (application?.status as any) || 'SUBMITTED';
  const openQueries = useMemo(
    () => (lifecycle?.open_queries || []).filter((q) => q.status === 'OPEN'),
    [lifecycle]
  );
  const grantedCount = (lifecycle?.approvals || []).filter((a) => a.status === 'GRANTED').length;
  const reviewableCount = lifecycle?.approvals.length || 0;

  return (
    <div>
      <Breadcrumb items={[{ label: 'Portal Gateway', step: 0 }, { label: 'Application tracking' }]} />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-300">
          <div>
            <h1 className="text-xl font-bold text-gov-navy">Prototype case tracking</h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Your assessment, evidence, and simulated department progress in one place.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setLoading(true);
                if (selectedAppId) fetchDetail(selectedAppId);
                fetchList();
              }}
              disabled={loading}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => {
                resetAssessment();
                goToStep(1);
              }}
              className="px-3.5 py-1.5 rounded text-xs font-bold text-white bg-gov-navy hover:bg-gov-navyLight flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5 text-gov-gold" />
              New assessment
            </button>
          </div>
        </div>

        {applications.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-[11px] font-semibold text-slate-500 shrink-0">Your cases</span>
            {applications.map((item) => (
              <button
                key={item.application_id}
                onClick={() => setSelectedAppId(item.application_id)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold shrink-0 border ${
                  selectedAppId === item.application_id
                    ? 'bg-gov-navy text-white border-gov-navy'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                }`}
              >
                {item.tracking_reference}
              </button>
            ))}
          </div>
        )}

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

        {loading && !application && (
          <div className="bg-white border border-slate-200 rounded p-10 text-center text-xs text-slate-600">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-gov-navy mb-2" />
            Loading your case.
          </div>
        )}

        {!loading && !application && !error && (
          <div className="bg-white border border-slate-200 rounded-lg p-10 text-center space-y-3 shadow-2xs">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-500 mx-auto flex items-center justify-center font-bold text-sm">
              0
            </div>
            <h3 className="text-sm font-bold text-gov-navy">No application cases yet.</h3>
            <p className="text-xs text-slate-600 max-w-md mx-auto">
              Complete a regulatory assessment and submit an application for prototype case tracking to monitor statutory approvals, document readiness milestones, and simulated department reviews.
            </p>
            <div className="pt-2">
              <button
                onClick={() => {
                  resetAssessment();
                  goToStep(1);
                }}
                className="px-4 py-2 rounded text-xs font-bold text-white bg-gov-navy hover:bg-gov-navyLight transition shadow inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5 text-gov-gold" />
                Start New Assessment
              </button>
            </div>
          </div>
        )}

        {application && (
          <>
            {/* Primary status card */}
            <section className="bg-white border border-slate-300 border-l-4 border-l-gov-gold rounded-lg p-5 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] font-mono font-bold text-gov-navy">
                    {application.tracking_reference}
                  </div>
                  <h2 className="text-lg font-bold text-gov-navy mt-0.5">{application.entity_name}</h2>
                  <div className="mt-2">
                    <ApplicationStatusBadge status={status} />
                  </div>
                </div>
                <div className="sm:text-right">
                  <div className="text-2xl font-bold text-gov-navy">
                    {grantedCount}/{reviewableCount || '—'}
                  </div>
                  <div className="text-[11px] text-slate-500">approvals granted in simulation</div>
                </div>
              </div>
              <div className="border-t border-slate-200 pt-3">
                <JourneyRail activeIndex={journeyIndex(status)} />
              </div>
            </section>

            {/* Open queries lead the page when present */}
            {openQueries.length > 0 && (
              <section className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <MessageSquareWarning className="w-4 h-4 text-amber-700" />
                  <h2 className="text-sm font-bold text-amber-900">
                    {openQueries.length === 1
                      ? 'A department has asked you for something'
                      : `${openQueries.length} departments have asked you for something`}
                  </h2>
                </div>
                {openQueries.map((query) => (
                  <QueryResponseCard
                    key={query.query_id}
                    applicationId={application.application_id}
                    query={query}
                    submissions={application.submissions}
                    onDone={async (message) => {
                      setNotice(message);
                      await fetchDetail(application.application_id);
                    }}
                    onError={setError}
                  />
                ))}
              </section>
            )}

            {/* Approval progress */}
            <section className="bg-white border border-slate-300 rounded-lg p-4 space-y-2">
              <h2 className="text-xs font-bold text-gov-navy">Approval progress</h2>
              {reviewableCount === 0 ? (
                <p className="text-xs text-slate-600">
                  None of the approvals on this case are handled by a department simulated in this
                  prototype, so no review progress is shown.
                </p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {lifecycle!.approvals.map((approval) => (
                    <div
                      key={approval.approval_id}
                      className="py-2.5 flex flex-wrap items-center justify-between gap-2"
                    >
                      <div>
                        <div className="text-xs font-semibold text-slate-800">
                          {approval.name || approval.approval_id}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {approval.department}
                          {approval.sla_days ? ` · published service timeline ${approval.sla_days} days` : ''}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <ReadinessBadge status={approval.readiness_status} />
                        <ApprovalStatusBadge status={approval.status} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <Expandable label="View all approvals on this case">
                <div className="text-[11px] text-slate-600 space-y-1">
                  {application.approvals.map((approval) => (
                    <div key={approval.approval_id} className="flex justify-between gap-3">
                      <span>
                        {approval.name || approval.approval_id}{' '}
                        <span className="text-slate-400">({approval.department || 'authority'})</span>
                      </span>
                      <span>{approval.readiness_status || 'PENDING'}</span>
                    </div>
                  ))}
                  <p className="pt-1 text-slate-500">
                    Approvals outside DISH and FSSAI have no officer view in this prototype. Their
                    regulatory status is unchanged.
                  </p>
                </div>
              </Expandable>
            </section>

            {/* Department activity */}
            <section className="bg-white border border-slate-300 rounded-lg p-4 space-y-2">
              <h2 className="text-xs font-bold text-gov-navy">Latest department activity</h2>
              {(lifecycle?.events.length || 0) === 0 ? (
                <p className="text-xs text-slate-600">
                  No department has opened this case yet.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {[...lifecycle!.events].reverse().slice(0, 4).map((event) => (
                    <div key={event.event_id} className="text-[11px] text-slate-700">
                      <span className="font-mono text-slate-400">
                        {new Date(event.created_at).toLocaleDateString()}
                      </span>{' '}
                      — {event.detail || event.event_type}
                    </div>
                  ))}
                </div>
              )}

              {(lifecycle?.queries.length || 0) > 0 && (
                <Expandable label="View all queries on this case">
                  <div className="space-y-2">
                    {lifecycle!.queries.map((query) => (
                      <div key={query.query_id} className="border border-slate-200 rounded p-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] font-semibold text-slate-800">
                            {query.approval_name || query.approval_id} · {query.department}
                          </span>
                          <QueryStatusBadge status={query.status} />
                        </div>
                        <p className="text-[11px] text-slate-700 mt-1">{query.query_text}</p>
                        {query.response_text && (
                          <p className="text-[11px] text-slate-600 mt-1">
                            Your response: {query.response_text}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </Expandable>
              )}
            </section>

            {/* Timeline and evidence, kept available but not in the way */}
            <section className="bg-white border border-slate-300 rounded-lg p-4">
              <h2 className="text-xs font-bold text-gov-navy">Sequencing and evidence</h2>
              <p className="text-[11px] text-slate-600 mt-1">
                {application.timeline.phase_1_immediate.count} approval
                {application.timeline.phase_1_immediate.count === 1 ? '' : 's'} can be filed straight away;{' '}
                {application.timeline.phase_2_sequential.count} wait on an earlier approval.{' '}
                {application.submissions.length} evidence item
                {application.submissions.length === 1 ? '' : 's'} attached.
              </p>

              <Expandable label="View details">
                <div className="space-y-3 text-[11px]">
                  <div>
                    <div className="font-semibold text-slate-800">Can be filed immediately</div>
                    {application.timeline.phase_1_immediate.items.map((item) => (
                      <div key={item.approval_id} className="text-slate-600">
                        {item.name} — {item.department}
                      </div>
                    ))}
                  </div>
                  {application.timeline.phase_2_sequential.count > 0 && (
                    <div>
                      <div className="font-semibold text-slate-800">Waits on an earlier approval</div>
                      {application.timeline.phase_2_sequential.items.map((item) => (
                        <div key={item.approval_id} className="text-slate-600">
                          {item.name} — {item.precondition_note}
                        </div>
                      ))}
                    </div>
                  )}
                  <div>
                    <div className="font-semibold text-slate-800">Evidence attached</div>
                    {application.submissions.length === 0 ? (
                      <div className="text-slate-600">No files attached to this case.</div>
                    ) : (
                      application.submissions.map((submission) => {
                        const finding = application.verification_records.find(
                          (record) => record.document_id === submission.document_id
                        );
                        return (
                          <div key={submission.submission_id} className="text-slate-600">
                            {submission.document_id}
                            {finding?.disposition ? ` — automated check: ${finding.disposition}` : ''}
                          </div>
                        );
                      })
                    )}
                  </div>
                  <p className="text-slate-500">
                    Automated checks indicate whether expected evidence is present and readable. They
                    do not establish authenticity or government approval.
                  </p>
                </div>
              </Expandable>
            </section>

            <p className="text-[11px] text-slate-500">
              {lifecycle?.simulation_notice ||
                'Department review in this prototype is a simulation. No application has been filed with any government department.'}
            </p>
          </>
        )}
      </div>
    </div>
  );
};

const QueryResponseCard: React.FC<{
  applicationId: string;
  query: QueryView;
  submissions: ApplicationRecord['submissions'];
  onDone: (message: string) => Promise<void>;
  onError: (message: string) => void;
}> = ({ applicationId, query, submissions, onDone, onError }) => {
  const [text, setText] = useState('');
  const [submissionId, setSubmissionId] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const chosen = submissions.find((item) => item.submission_id === submissionId);
      await api.respondToQuery(applicationId, query.query_id, {
        response_text: text,
        response_document_id: chosen?.document_id || null,
        response_submission_id: submissionId || null,
      });
      setText('');
      setSubmissionId('');
      await onDone('Your response has been sent to the department.');
    } catch (err: any) {
      onError(err?.message || 'Your response could not be sent.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white border border-amber-200 rounded p-3 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-800">
          {query.department} · {query.approval_name || query.approval_id}
        </span>
        <QueryStatusBadge status={query.status} />
      </div>
      <p className="text-xs text-slate-800">{query.query_text}</p>
      <div className="text-[11px] text-amber-900 font-semibold">Respond by {query.deadline}</div>

      <label className="block text-[11px] font-semibold text-slate-700">
        Your response
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={3}
          placeholder="Explain what you are providing or correcting."
          className="mt-1 w-full border border-slate-300 rounded px-2 py-1.5 text-xs font-normal"
        />
      </label>

      {submissions.length > 0 && (
        <label className="block text-[11px] font-semibold text-slate-700">
          Point to a document you have already uploaded (optional)
          <select
            value={submissionId}
            onChange={(event) => setSubmissionId(event.target.value)}
            className="mt-1 block w-full border border-slate-300 rounded px-2 py-1.5 text-[11px] font-normal"
          >
            <option value="">No document reference</option>
            {submissions.map((item) => (
              <option key={item.submission_id} value={item.submission_id}>
                {item.document_id}
              </option>
            ))}
          </select>
          <span className="block text-[10px] text-slate-500 mt-1 font-normal">
            To supply a new file, upload it on the readiness page first; only the reference is recorded here.
          </span>
        </label>
      )}

      <button
        onClick={submit}
        disabled={busy || !text.trim()}
        className="px-4 py-1.5 rounded bg-gov-navy text-white text-[11px] font-bold disabled:opacity-50"
      >
        {busy ? 'Sending…' : 'Send response'}
      </button>
    </div>
  );
};
