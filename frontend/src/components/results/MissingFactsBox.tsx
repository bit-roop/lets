import React, { useState } from 'react';
import { HelpCircle, RefreshCw, CheckCircle2, ArrowRight } from 'lucide-react';
import { Requirement } from '../../types/engine';
import { useAssessment } from '../../context/AssessmentContext';

export const MissingFactsBox: React.FC<{ unknownRequirements: Requirement[] }> = ({
  unknownRequirements,
}) => {
  const { facts, setFact, runEvaluation, isLoading } = useAssessment();
  const [localMpcb, setLocalMpcb] = useState<string>(facts.mpcb_category || '');
  const [localEsic, setLocalEsic] = useState<boolean | null>(facts.in_esic_implemented_area ?? null);

  if (!unknownRequirements || unknownRequirements.length === 0) return null;

  // Extract unique missing facts
  const allMissing = Array.from(
    new Set(unknownRequirements.flatMap((r) => r.missing_facts || []))
  );

  if (allMissing.length === 0) return null;

  const handleUpdateAndReEvaluate = async () => {
    const updatedFacts = {
      ...facts,
      mpcb_category: localMpcb === '' ? null : localMpcb,
      in_esic_implemented_area: localEsic,
    };
    if (localMpcb) setFact('mpcb_category', localMpcb);
    if (localEsic !== null) setFact('in_esic_implemented_area', localEsic);

    await runEvaluation(updatedFacts);
  };

  return (
    <div className="bg-amber-50/70 border border-amber-300 rounded-md p-4 mb-6 shadow-xs">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-amber-700 shrink-0" />
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900">
              Action Required: Missing Regulatory Facts
            </h3>
            <p className="text-[11.5px] text-amber-800 mt-0.5">
              The engine safely yielded <strong>UNKNOWN</strong> for {unknownRequirements.length} requirement(s) rather than guessing. Provide the missing parameters below to resolve statutory applicability.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-amber-200">
        {/* MPCB Category missing fact */}
        {allMissing.includes('mpcb_category') && (
          <div className="bg-white p-3 rounded border border-amber-200">
            <label className="block text-xs font-bold text-slate-800 mb-1">
              Pollution Control Category (Affects Consent to Establish & Operate)
            </label>
            <p className="text-[10.5px] text-slate-500 mb-2">
              Required by MPCB under Water Act 1974 s.25 & Air Act 1981 s.21.
            </p>
            <select
              value={localMpcb}
              onChange={(e) => setLocalMpcb(e.target.value)}
              className="w-full text-xs px-2.5 py-1.5 border border-slate-300 rounded bg-slate-50 focus:bg-white focus:ring-1 focus:ring-gov-navy font-medium"
            >
              <option value="">-- Still Unspecified (Remain UNKNOWN) --</option>
              <option value="Orange">Orange Category (Fruit/Food Processing Typical)</option>
              <option value="Red">Red Category (Heavy discharge / High BOD)</option>
              <option value="Green">Green Category (Low pollution / Bakery)</option>
              <option value="White">White Category (Non-polluting / Intimation only)</option>
            </select>
          </div>
        )}

        {/* ESIC Implemented Area missing fact */}
        {allMissing.includes('in_esic_implemented_area') && (
          <div className="bg-white p-3 rounded border border-amber-200">
            <label className="block text-xs font-bold text-slate-800 mb-1">
              ESIC Notified District Status (Affects ESIC Registration)
            </label>
            <p className="text-[10.5px] text-slate-500 mb-2">
              Maharashtra is a partially implemented state under ESI Act 1948 s.1(5).
            </p>
            <div className="flex gap-4 mt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                <input
                  type="radio"
                  name="esic_area"
                  checked={localEsic === true}
                  onChange={() => setLocalEsic(true)}
                  className="text-gov-navy focus:ring-gov-navy"
                />
                Unit is in ESIC Notified Area
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                <input
                  type="radio"
                  name="esic_area"
                  checked={localEsic === false}
                  onChange={() => setLocalEsic(false)}
                  className="text-gov-navy focus:ring-gov-navy"
                />
                Non-Notified Rural Area
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="mt-3.5 pt-2 flex justify-end">
        <button
          type="button"
          disabled={isLoading}
          onClick={handleUpdateAndReEvaluate}
          className="px-4 py-2 bg-gov-navy text-white hover:bg-gov-navyLight rounded text-xs font-bold flex items-center gap-2 transition shadow-xs disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Re-evaluating...' : 'Supply Missing Facts & Re-evaluate'}
        </button>
      </div>
    </div>
  );
};
