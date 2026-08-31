import React, { useEffect, useState } from 'react';
import { ClipboardList, Eye, Trash2 } from 'lucide-react';
import { CaseRecord, getCases, clearCases } from '../utils/caseStore';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';

const statusFor = (c: CaseRecord) => {
  const s = c.evaluationResult.summary;
  if (s.conflict > 0) return { label: 'Needs review', classes: 'bg-red-50 text-red-700 border-red-200' };
  if (s.unknown > 0) return { label: 'Pending info', classes: 'bg-amber-50 text-amber-700 border-amber-200' };
  return { label: 'Cleared', classes: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
};

export const DepartmentReviewPage: React.FC = () => {
  const { viewCase } = useAssessment();
  const [cases, setCases] = useState<CaseRecord[]>([]);

  useEffect(() => {
    setCases(getCases());
  }, []);

  return (
    <div>
      <Breadcrumb items={[{ label: 'Department review' }]} />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink-900 flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-brand" />
              Submitted cases
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">Every check run on this device, for review.</p>
          </div>
          {cases.length > 0 && (
            <button
              onClick={() => { clearCases(); setCases([]); }}
              className="text-xs text-slate-400 hover:text-red-600 flex items-center gap-1"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear all
            </button>
          )}
        </div>

        {cases.length === 0 ? (
          <div className="p-10 text-center bg-white rounded-2xl border border-slate-200 text-sm text-slate-500">
            No cases submitted yet. They'll appear here once someone runs a check.
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="p-3 font-medium">Business</th>
                  <th className="p-3 font-medium">Submitted</th>
                  <th className="p-3 font-medium">Required</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {cases.map((c) => {
                  const status = statusFor(c);
                  return (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="p-3 font-medium text-ink-900">{c.businessName}</td>
                      <td className="p-3 text-slate-500">{new Date(c.submittedAt).toLocaleString('en-IN')}</td>
                      <td className="p-3 text-slate-600">{c.evaluationResult.summary.applicable} requirement(s)</td>
                      <td className="p-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${status.classes}`}>
                          {status.label}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button onClick={() => viewCase(c.id)} className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark">
                          <Eye className="w-3.5 h-3.5" />
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};