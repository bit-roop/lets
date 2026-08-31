import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, AlertTriangle } from 'lucide-react';
import { RequirementState } from '../../types/engine';

const CONFIG: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; classes: string; hint: string }> = {
  APPLICABLE: {
    label: 'Required',
    icon: CheckCircle2,
    classes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    hint: 'This applies to your business based on what you told us.',
  },
  NOT_APPLICABLE: {
    label: 'Not needed',
    icon: XCircle,
    classes: 'bg-slate-100 text-slate-600 border-slate-200',
    hint: 'This does not apply to your business.',
  },
  UNKNOWN: {
    label: 'Need more info',
    icon: HelpCircle,
    classes: 'bg-amber-50 text-amber-700 border-amber-200',
    hint: 'We need a few more details to be sure.',
  },
  CONFLICT: {
    label: 'Conflicting rules',
    icon: AlertTriangle,
    classes: 'bg-red-50 text-red-700 border-red-200',
    hint: 'Two rules disagree — this needs a human to check.',
  },
};

export const StatusBadge: React.FC<{ state: RequirementState; size?: 'sm' | 'md' }> = ({ state, size = 'md' }) => {
  const cfg = CONFIG[state] || {
    label: state,
    icon: HelpCircle,
    classes: 'bg-slate-100 text-slate-600 border-slate-200',
    hint: '',
  };
  const Icon = cfg.icon;
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${cfg.classes} ${padding}`}
      title={cfg.hint}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      {cfg.label}
    </span>
  );
};
