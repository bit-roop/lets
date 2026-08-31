import React from 'react';
import { Sparkles } from 'lucide-react';
import { DerivedFact, DerivationDiagnostics } from '../../types/engine';
import { ConfidenceTag } from '../common/ConfidenceTag';

export const DerivedFactsBox: React.FC<{
  derivedFacts: Record<string, DerivedFact>;
  diagnostics?: DerivationDiagnostics;
}> = ({ derivedFacts }) => {
  const factKeys = Object.keys(derivedFacts);
  if (factKeys.length === 0) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-brand" />
        <h3 className="text-sm font-semibold text-ink-900">Things we worked out for you</h3>
      </div>
      <div className="space-y-2">
        {factKeys.map((key) => {
          const df = derivedFacts[key];
          return (
            <div key={key} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-sm bg-slate-50 rounded-lg p-2.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-ink-700">{df.fact.replace(/_/g, ' ')}</span>
                <span className="text-slate-400">→</span>
                <span className="font-medium text-emerald-700">{String(df.value)}</span>
              </div>
              <ConfidenceTag status={df.verification_status} />
            </div>
          );
        })}
      </div>
    </div>
  );
};
