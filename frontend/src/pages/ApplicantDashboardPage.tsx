import React, { useEffect, useState } from 'react';
import {
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  FileText,
  HelpCircle,
  Landmark,
  Layers,
  RefreshCw,
  RotateCcw,
  Shield,
  ShieldCheck,
  Sparkles,
  Timer,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { api, ApplicationRecord, ApplicationSummary } from '../api/client';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';

interface Props {
  initialApplicationId?: string | null;
}

export const ApplicantDashboardPage: React.FC<Props> = ({ initialApplicationId }) => {
  const { goToStep, resetAssessment } = useAssessment();
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(initialApplicationId || null);
  const [activeApplication, setActiveApplication] = useState<ApplicationRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApplicationsList = async () => {
    try {
      const res = await api.listApplications();
      setApplications(res.applications || []);
      if (res.applications.length > 0 && !selectedAppId) {
        setSelectedAppId(res.applications[0].application_id);
      }
    } catch (err: any) {
      console.warn('Could not load applications list:', err?.message);
    }
  };

  const fetchApplicationDetails = async (appId: string) => {
    setLoading(true);
    setError(null);
    try {
      const record = await api.getApplication(appId);
      setActiveApplication(record);
    } catch (err: any) {
      setError(err?.message || 'Could not load application case details.');
      setActiveApplication(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplicationsList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedAppId) {
      fetchApplicationDetails(selectedAppId);
    }
  }, [selectedAppId]);

  return (
    <div>
      <Breadcrumb
        items={[
          { label: 'Portal Gateway', step: 0 },
          { label: 'Applicant Dashboard & Case Tracking' },
        ]}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-300">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gov-gold bg-gov-navy px-2.5 py-0.5 rounded">
                Prototype Case Tracking & Milestone Monitor
              </span>
              <span className="text-xs font-mono text-slate-500">
                Slice 3 Persistent Case Storage
              </span>
            </div>
            <h1 className="text-xl font-bold text-gov-navy mt-1">
              Application Case Tracking
            </h1>
            <p className="text-xs text-slate-600">
              Monitoring of statutory approvals, document readiness milestones, and sequential clearance deadlines in the prototype workflow.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (selectedAppId) fetchApplicationDetails(selectedAppId);
                fetchApplicationsList();
              }}
              disabled={loading}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 transition shadow-2xs flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>

            <button
              onClick={() => {
                resetAssessment();
                goToStep(1);
              }}
              className="px-3.5 py-1.5 rounded text-xs font-bold text-white bg-gov-navy hover:bg-gov-navyLight transition shadow-2xs flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5 text-gov-gold" />
              New Assessment
            </button>
          </div>
        </div>

        {/* Applications Selector Tabs if multiple */}
        {applications.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide shrink-0">
              Filed Cases:
            </span>
            {applications.map((app) => (
              <button
                key={app.application_id}
                onClick={() => setSelectedAppId(app.application_id)}
                className={`px-3 py-1 rounded text-xs font-mono font-bold transition shrink-0 ${
                  selectedAppId === app.application_id
                    ? 'bg-gov-navy text-gov-gold shadow-xs'
                    : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                }`}
              >
                {app.tracking_reference} ({app.entity_name})
              </button>
            ))}
          </div>
        )}

        {/* Loading State */}
        {loading && !activeApplication && (
          <div className="bg-white border border-slate-300 rounded p-12 text-center">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gov-navy mb-2" />
            <div className="text-xs font-bold text-slate-700">Loading persistent application case...</div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded p-4 text-xs text-rose-900">
            {error}
          </div>
        )}

        {/* Active Application View */}
        {activeApplication && (
          <div className="space-y-6">
            {/* Tracking Reference & Status Hero Card */}
            <div className="bg-white border-l-4 border-l-gov-gold border border-slate-300 rounded-lg p-5 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-extrabold text-gov-navy bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      Tracking No: {activeApplication.tracking_reference}
                    </span>
                    <span className="inline-flex items-center gap-1 font-bold text-[11px] px-2.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      STATUS: {activeApplication.status}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-gov-navy">
                    {activeApplication.entity_name}
                  </h2>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Location: <strong>{activeApplication.facts.location_authority} ({activeApplication.facts.land_classification})</strong> &bull; Submitted:{' '}
                    <span className="font-mono">{new Date(activeApplication.created_at).toLocaleString()}</span>
                  </p>
                </div>

                <div className="text-right sm:border-l sm:border-slate-200 sm:pl-5">
                  <div className="text-[11px] text-slate-500 uppercase font-bold tracking-wide">
                    Statutory Clearances
                  </div>
                  <div className="text-lg font-bold font-mono text-gov-navy mt-0.5">
                    {activeApplication.approvals.length} Approvals Tracked
                  </div>
                  <div className="text-[11px] text-emerald-700 font-semibold mt-0.5">
                    {activeApplication.submissions.length} Evidence Items Attached
                  </div>
                </div>
              </div>
            </div>

            {/* M3 Parallel & Sequential Timeline Card */}
            <div className="bg-white border border-slate-300 rounded-lg p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-gov-navy" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                    M3 Sequential & Parallel Approval Timeline
                  </h3>
                </div>
                <span className="text-[11px] text-slate-500 font-medium">
                  Derived from statutory dependency graph & SLAs
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Phase 1: Immediate Parallel */}
                <div className="bg-emerald-50/40 border border-emerald-200 rounded p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-900 uppercase tracking-wide flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                      Phase 1: Immediate (Can Start Now)
                    </span>
                    <span className="text-[11px] font-mono font-bold bg-white text-emerald-800 px-2 py-0.5 rounded border border-emerald-300">
                      {activeApplication.timeline.phase_1_immediate.count} Approvals
                    </span>
                  </div>
                  <p className="text-[11px] text-emerald-800">
                    Statutory registrations and permissions that can be initiated in parallel immediately.
                  </p>

                  <div className="space-y-2 pt-1">
                    {activeApplication.timeline.phase_1_immediate.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-white p-2.5 rounded border border-emerald-200 text-xs flex items-center justify-between gap-2 shadow-2xs"
                      >
                        <div>
                          <span className="font-mono font-bold text-gov-navy mr-1.5">
                            {item.approval_id}
                          </span>
                          <span className="font-semibold text-slate-800">{item.name}</span>
                          <div className="text-[10.5px] text-slate-500 mt-0.5">
                            {item.department} &bull; SLA: {item.sla_days ? `${item.sla_days} Days` : 'Standard'}
                          </div>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 shrink-0">
                          {item.readiness_status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Phase 2: Sequential Post-Condition */}
                <div className="bg-slate-50 border border-slate-300 rounded p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-slate-600" />
                      Phase 2: Sequential (After Preconditions)
                    </span>
                    <span className="text-[11px] font-mono font-bold bg-white text-slate-700 px-2 py-0.5 rounded border border-slate-300">
                      {activeApplication.timeline.phase_2_sequential.count} Approvals
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600">
                    Operating licences gated by site plan approvals or prior statutory consents.
                  </p>

                  <div className="space-y-2 pt-1">
                    {activeApplication.timeline.phase_2_sequential.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-white p-2.5 rounded border border-slate-300 text-xs flex items-center justify-between gap-2 shadow-2xs"
                      >
                        <div>
                          <span className="font-mono font-bold text-gov-navy mr-1.5">
                            {item.approval_id}
                          </span>
                          <span className="font-semibold text-slate-800">{item.name}</span>
                          <div className="text-[10.5px] text-amber-800 font-medium mt-0.5">
                            {item.precondition_note}
                          </div>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-300 shrink-0">
                          {item.readiness_status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Approvals Detailed Tracking Table */}
            <div className="bg-white border border-slate-300 rounded-lg p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <Landmark className="w-4 h-4 text-gov-navy" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                    Statutory Approval Milestones
                  </h3>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">
                  Total: {activeApplication.approvals.length} Clearances
                </span>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200 text-[11px]">
                    <tr>
                      <th className="p-2.5">Approval ID</th>
                      <th className="p-2.5">Name / Purpose</th>
                      <th className="p-2.5">Department</th>
                      <th className="p-2.5">Statutory SLA</th>
                      <th className="p-2.5">Evidence Readiness</th>
                      <th className="p-2.5">Review Milestone</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {activeApplication.approvals.map((appr, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-2.5 font-mono font-bold text-gov-navy">
                          {appr.approval_id}
                        </td>
                        <td className="p-2.5 font-medium text-slate-800">
                          {appr.name || appr.approval_id}
                          {appr.statute && (
                            <div className="text-[10px] text-slate-500 font-mono">{appr.statute}</div>
                          )}
                        </td>
                        <td className="p-2.5 text-slate-600">
                          {appr.department || 'Competent Authority'}
                        </td>
                        <td className="p-2.5 font-mono text-slate-700">
                          {appr.sla_days ? `${appr.sla_days} Days` : 'Immediate'}
                        </td>
                        <td className="p-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                              appr.readiness_status === 'READY'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                : 'bg-slate-100 text-slate-700 border-slate-300'
                            }`}
                          >
                            {appr.readiness_status || 'PENDING'}
                          </span>
                        </td>
                        <td className="p-2.5">
                          <span className="text-[11px] font-semibold text-sky-900 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                            Submitted · Pending Review Simulation
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Attached Evidence & Submissions Card */}
            <div className="bg-white border border-slate-300 rounded-lg p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gov-navy" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                    Submitted Evidence & M5 Scrutiny References
                  </h3>
                </div>
                <span className="text-[11px] text-slate-500">
                  Zero raw files duplicated in case records
                </span>
              </div>

              {activeApplication.submissions.length > 0 ? (
                <div className="space-y-2">
                  {activeApplication.submissions.map((sub, sIdx) => {
                    const ver = activeApplication.verification_records.find(
                      (v) => v.document_id === sub.document_id
                    );
                    return (
                      <div
                        key={sIdx}
                        className="bg-slate-50 p-3 rounded border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-bold text-slate-800">
                            {sub.document_id}{' '}
                            {sub.filename && <span className="font-mono text-slate-500 font-normal">({sub.filename})</span>}
                          </div>
                          <div className="text-[10.5px] text-slate-500 mt-0.5">
                            Attached Evidence Item &bull; <span className="text-slate-600 font-medium">Recorded in Case Dossier</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300">
                            {sub.state || 'PROVIDED'}
                          </span>
                          {ver && ver.disposition && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                              M5: {ver.disposition}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-slate-500 bg-slate-50 rounded">
                  No individual file uploads attached to this application record.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
