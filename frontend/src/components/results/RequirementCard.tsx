import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Landmark, FileText, Clock, HelpCircle, Calculator } from 'lucide-react';
import { Requirement } from '../../types/engine';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceTag } from '../common/ConfidenceTag';
import { EvidenceDrawer } from './EvidenceDrawer';

const ACCENT: Record<string, string> = {
  APPLICABLE: 'border-l-emerald-400',
  UNKNOWN: 'border-l-amber-400',
  NOT_APPLICABLE: 'border-l-slate-200',
  CONFLICT: 'border-l-red-400',
};

export const RequirementCard: React.FC<{ requirement: Requirement; defaultExpanded?: boolean }> = ({
  requirement,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`bg-white rounded-2xl border border-slate-200 border-l-4 ${ACCENT[requirement.state] || 'border-l-slate-200'} overflow-hidden`}>
      <div className="p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-2 mb-1.5">
          <h4 className="text-sm font-semibold text-ink-900 leading-snug pr-4">{requirement.name}</h4>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge state={requirement.state} size="sm" />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500 mt-2">
          <span className="flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-slate-400" />
            {requirement.authority || 'Competent authority'}
          </span>
          <span className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            {requirement.statute || 'Statute'}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            {requirement.sla_days ? `${requirement.sla_days} day turnaround` : 'No fixed turnaround'}
          </span>
          {requirement.quantity && requirement.quantity.value !== null && (
            <span className="flex items-center gap-1.5 font-medium text-brand">
              <Calculator className="w-3.5 h-3.5" />
              Quantity needed: {requirement.quantity.value}
            </span>
          )}
        </div>

        {requirement.state === 'UNKNOWN' && requirement.missing_facts && requirement.missing_facts.length > 0 && (
          <div className="mt-3 flex items-start gap-2 bg-amber-50 rounded-lg p-2.5 text-xs text-amber-800">
            <HelpCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              Still need: <span className="font-medium">{requirement.missing_facts.join(', ')}</span>
            </span>
          </div>
        )}

        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs font-medium text-brand hover:text-brand-dark flex items-center gap-1 transition"
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {isExpanded ? 'Hide details' : 'Why? See the rule and source'}
          </button>
          <ConfidenceTag confidence={requirement.confidence} />
        </div>
      </div>

      {isExpanded && <EvidenceDrawer requirement={requirement} />}
    </div>
  );
};
