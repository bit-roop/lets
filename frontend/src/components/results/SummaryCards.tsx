import React from 'react';
import { CheckCircle2, HelpCircle, XCircle, AlertTriangle } from 'lucide-react';
import { EvaluationSummary } from '../../types/engine';

interface SummaryCardsProps {
  summary: EvaluationSummary;
  activeTab: string;
  onSelectTab: (tab: string) => void;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ summary, activeTab, onSelectTab }) => {
  const cards = [
    { key: 'APPLICABLE', label: 'Required', count: summary.applicable, icon: CheckCircle2, color: 'emerald' },
    { key: 'UNKNOWN', label: 'Need info', count: summary.unknown, icon: HelpCircle, color: 'amber' },
    { key: 'NOT_APPLICABLE', label: 'Not needed', count: summary.not_applicable, icon: XCircle, color: 'slate' },
    { key: 'CONFLICT', label: 'Conflicts', count: summary.conflict, icon: AlertTriangle, color: 'red' },
  ];

  const colorMap: Record<string, { bg: string; ring: string; text: string; iconText: string }> = {
    emerald: { bg: 'bg-emerald-50', ring: 'ring-emerald-400', text: 'text-emerald-800', iconText: 'text-emerald-600' },
    amber: { bg: 'bg-amber-50', ring: 'ring-amber-400', text: 'text-amber-800', iconText: 'text-amber-600' },
    slate: { bg: 'bg-slate-100', ring: 'ring-slate-400', text: 'text-slate-700', iconText: 'text-slate-500' },
    red: { bg: 'bg-red-50', ring: 'ring-red-400', text: 'text-red-800', iconText: 'text-red-600' },
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((c) => {
        const Icon = c.icon;
        const active = activeTab === c.key;
        const col = colorMap[c.color];
        return (
          <button
            key={c.key}
            onClick={() => onSelectTab(c.key)}
            className={`text-left p-4 rounded-xl border transition ${
              active ? `${col.bg} border-transparent ring-2 ${col.ring}` : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <Icon className={`w-4 h-4 ${col.iconText}`} />
              <span className="text-2xl font-semibold text-ink-900">{c.count}</span>
            </div>
            <div className="text-sm font-medium text-ink-700 mt-1.5">{c.label}</div>
          </button>
        );
      })}
    </div>
  );
};
