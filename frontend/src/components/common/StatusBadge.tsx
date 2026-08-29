import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, AlertTriangle } from 'lucide-react';
import { RequirementState } from '../../types/engine';

export const StatusBadge: React.FC<{ state: RequirementState; size?: 'sm' | 'md' }> = ({
  state,
  size = 'md',
}) => {
  const isSm = size === 'sm';
  const padding = isSm ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';
  const iconSize = isSm ? 'w-3 h-3' : 'w-3.5 h-3.5';

  switch (state) {
    case 'APPLICABLE':
      return (
        <span
          className={`inline-flex items-center gap-1 font-bold rounded border bg-emerald-50 text-emerald-800 border-emerald-300 ${padding}`}
          title="This requirement is legally required based on your declared facts."
        >
          <CheckCircle2 className={`${iconSize} text-emerald-600`} />
          APPLICABLE
        </span>
      );
    case 'NOT_APPLICABLE':
      return (
        <span
          className={`inline-flex items-center gap-1 font-bold rounded border bg-slate-100 text-slate-700 border-slate-300 ${padding}`}
          title="This requirement is excluded or does not apply."
        >
          <XCircle className={`${iconSize} text-slate-500`} />
          NOT APPLICABLE
        </span>
      );
    case 'UNKNOWN':
      return (
        <span
          className={`inline-flex items-center gap-1 font-bold rounded border bg-amber-50 text-amber-900 border-amber-300 ${padding}`}
          title="More information is required to evaluate this requirement."
        >
          <HelpCircle className={`${iconSize} text-amber-600`} />
          NEEDS INFORMATION
        </span>
      );
    case 'CONFLICT':
      return (
        <span
          className={`inline-flex items-center gap-1 font-bold rounded border bg-rose-50 text-rose-900 border-rose-300 ${padding}`}
          title="Regulatory conflict detected between competing rules."
        >
          <AlertTriangle className={`${iconSize} text-rose-600`} />
          CONFLICT DETECTED
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center font-bold rounded border bg-slate-100 text-slate-800 ${padding}`}>
          {state}
        </span>
      );
  }
};
