import React from 'react';
import { Cpu, CheckCircle2, Sparkles, ArrowRight } from 'lucide-react';
import { DerivedFact, DerivationDiagnostics } from '../../types/engine';
import { ConfidenceTag } from '../common/ConfidenceTag';

export const DerivedFactsBox: React.FC<{
  derivedFacts: Record<string, DerivedFact>;
  diagnostics?: DerivationDiagnostics;
}> = ({ derivedFacts, diagnostics }) => {
  const factKeys = Object.keys(derivedFacts);

  if (factKeys.length === 0) return null;

  return (
    <div className="bg-slate-100 border border-slate-300 rounded p-4 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-200 mb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-gov-navy" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
            Intermediate Derived Facts (Fixed-Point Inference)
          </h3>
        </div>
        {diagnostics && (
          <span className="text-[11px] font-mono text-slate-600">
            Passes Run: {diagnostics.passes_run} (Quiescence Reached: {diagnostics.reached_fixed_point ? 'Yes' : 'No'})
          </span>
        )}
      </div>

      <div className="space-y-2">
        {factKeys.map((key) => {
          const df = derivedFacts[key];
          return (
            <div
              key={key}
              className="bg-white p-3 rounded border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-gov-navy bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                  {df.fact}
                </span>
                <span className="text-slate-500">&rarr;</span>
                <span className="font-mono font-bold text-emerald-700">
                  {String(df.value)}
                </span>
                <span className="text-[11px] text-slate-500 font-sans">
                  (derived via rule <code className="text-gov-navy font-bold">{df.rule_id}@v{df.rule_version}</code> in pass {df.derived_in_pass})
                </span>
              </div>

              <div className="flex items-center gap-2">
                <ConfidenceTag status={df.verification_status} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
