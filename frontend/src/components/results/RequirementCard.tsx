import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Landmark,
  FileText,
  HelpCircle,
  Calculator,
  ShieldCheck,
} from 'lucide-react';
import { Requirement } from '../../types/engine';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceTag } from '../common/ConfidenceTag';
import { EvidenceDrawer } from './EvidenceDrawer';

export const RequirementCard: React.FC<{
  requirement: Requirement;
  defaultExpanded?: boolean;
}> = ({ requirement, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getBorderColor = () => {
    switch (requirement.state) {
      case 'APPLICABLE':
        return 'border-l-4 border-l-emerald-600 border-slate-300';
      case 'UNKNOWN':
        return 'border-l-4 border-l-amber-600 border-slate-300';
      case 'NOT_APPLICABLE':
        return 'border-l-4 border-l-slate-400 border-slate-200 opacity-90';
      case 'CONFLICT':
        return 'border-l-4 border-l-rose-600 border-slate-300';
      default:
        return 'border-slate-300';
    }
  };

  return (
    <div className={`bg-white rounded border shadow-2xs transition ${getBorderColor()}`}>
      <div className="p-4">
        {/* Top Meta Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-gov-navy bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {requirement.requirement_id}
            </span>
            <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
              {requirement.requirement_type}
            </span>
            {requirement.quantity && requirement.quantity.value !== null && (
              <span className="text-[11px] font-bold text-gov-navy bg-gov-gold/15 text-gov-navy px-2 py-0.5 rounded border border-gov-gold/40 flex items-center gap-1">
                <Calculator className="w-3 h-3 text-gov-gold" />
                Required Quantity: {requirement.quantity.value}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <ConfidenceTag confidence={requirement.confidence} />
            <StatusBadge state={requirement.state} size="sm" />
          </div>
        </div>

        {/* Title */}
        <h4 className="text-sm font-bold text-gov-navy leading-snug">
          {requirement.name}
        </h4>

        {/* Details Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2.5 text-xs text-slate-600">
          <div className="flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate" title={requirement.authority}>
              {requirement.authority || 'Competent Authority'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate" title={requirement.statute}>
              {requirement.statute || 'Statute / Rules'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>Statutory SLA: {requirement.sla_days ? `${requirement.sla_days} Days` : 'Immediate'}</span>
          </div>
        </div>

        {/* Missing Facts Notice for UNKNOWN */}
        {requirement.state === 'UNKNOWN' && requirement.missing_facts && requirement.missing_facts.length > 0 && (
          <div className="mt-3 bg-amber-50 p-2.5 rounded border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
            <HelpCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold">Missing Input Facts: </span>
              <span className="font-mono font-medium">{requirement.missing_facts.join(', ')}</span>
              <span className="block text-[11px] text-amber-800 mt-0.5">
                The engine cannot deterministically confirm applicability without these parameters.
              </span>
            </div>
          </div>
        )}

        {/* Action Expand Bar */}
        <div className="mt-3.5 pt-2.5 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs font-bold text-gov-navy hover:text-gov-navyLight flex items-center gap-1 transition"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Hide Statutory Trace & Evidence
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                {requirement.state === 'APPLICABLE'
                  ? 'Why is this required? (View Legal Evidence)'
                  : requirement.state === 'NOT_APPLICABLE'
                  ? 'Why is this not applicable? (View Exclusion Trace)'
                  : 'View Rule Provenance & Evidence'}
              </>
            )}
          </button>

          <span className="text-[11px] text-slate-400 font-mono">
            {requirement.evidence?.length || 0} rule(s) evaluated
          </span>
        </div>
      </div>

      {/* Expandable Evidence Drawer */}
      {isExpanded && <EvidenceDrawer requirement={requirement} />}
    </div>
  );
};
