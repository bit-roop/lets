import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, AlertTriangle, Cpu, ArrowRight } from 'lucide-react';
import { EvaluationSummary } from '../../types/engine';

interface SummaryCardsProps {
  summary: EvaluationSummary;
  activeTab: string;
  onSelectTab: (tab: string) => void;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ summary, activeTab, onSelectTab }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-6">
      {/* Applicable */}
      <div
        onClick={() => onSelectTab('APPLICABLE')}
        className={`p-3.5 rounded border transition cursor-pointer ${
          activeTab === 'APPLICABLE'
            ? 'bg-emerald-50 border-emerald-500 shadow-sm ring-1 ring-emerald-500'
            : 'bg-white border-slate-300 hover:border-emerald-400 hover:bg-emerald-50/40'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Applicable
          </span>
          <span className="text-xl font-bold text-emerald-900 font-mono">
            {summary.applicable}
          </span>
        </div>
        <div className="text-[11px] text-emerald-700 mt-1">
          Statutory clearances required to establish & operate
        </div>
      </div>

      {/* Needs Information */}
      <div
        onClick={() => onSelectTab('UNKNOWN')}
        className={`p-3.5 rounded border transition cursor-pointer ${
          activeTab === 'UNKNOWN'
            ? 'bg-amber-50 border-amber-500 shadow-sm ring-1 ring-amber-500'
            : 'bg-white border-slate-300 hover:border-amber-400 hover:bg-amber-50/40'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
            <HelpCircle className="w-4 h-4 text-amber-600" />
            Needs Info
          </span>
          <span className="text-xl font-bold text-amber-900 font-mono">
            {summary.unknown}
          </span>
        </div>
        <div className="text-[11px] text-amber-700 mt-1">
          Missing facts require applicant clarification
        </div>
      </div>

      {/* Not Applicable */}
      <div
        onClick={() => onSelectTab('NOT_APPLICABLE')}
        className={`p-3.5 rounded border transition cursor-pointer ${
          activeTab === 'NOT_APPLICABLE'
            ? 'bg-slate-100 border-slate-500 shadow-sm ring-1 ring-slate-500'
            : 'bg-white border-slate-300 hover:border-slate-400 hover:bg-slate-50'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
            <XCircle className="w-4 h-4 text-slate-500" />
            Excluded
          </span>
          <span className="text-xl font-bold text-slate-800 font-mono">
            {summary.not_applicable}
          </span>
        </div>
        <div className="text-[11px] text-slate-600 mt-1">
          Active statutory exclusions or un-triggered items
        </div>
      </div>

      {/* Conflict */}
      <div
        onClick={() => onSelectTab('CONFLICT')}
        className={`p-3.5 rounded border transition cursor-pointer ${
          activeTab === 'CONFLICT'
            ? 'bg-rose-50 border-rose-500 shadow-sm ring-1 ring-rose-500'
            : summary.conflict > 0
            ? 'bg-rose-50/50 border-rose-300'
            : 'bg-white border-slate-300 hover:border-slate-400'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Conflict
          </span>
          <span className="text-xl font-bold text-rose-900 font-mono">
            {summary.conflict}
          </span>
        </div>
        <div className="text-[11px] text-rose-700 mt-1">
          {summary.conflict === 0 ? 'No regulatory contradictions' : 'Rule contradiction detected'}
        </div>
      </div>
    </div>
  );
};
