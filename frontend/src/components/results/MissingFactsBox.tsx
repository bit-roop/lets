import React, { useState } from 'react';
import { HelpCircle, RefreshCw } from 'lucide-react';
import { Requirement } from '../../types/engine';
import { useAssessment } from '../../context/AssessmentContext';

export const MissingFactsBox: React.FC<{ unknownRequirements: Requirement[] }> = ({ unknownRequirements }) => {
  const { facts, setFact, runEvaluation, isLoading } = useAssessment();
  const [localMpcb, setLocalMpcb] = useState<string>(facts.mpcb_category || '');
  const [localEsic, setLocalEsic] = useState<boolean | null>(facts.in_esic_implemented_area ?? null);

  if (!unknownRequirements || unknownRequirements.length === 0) return null;

  const allMissing = Array.from(new Set(unknownRequirements.flatMap((r) => r.missing_facts || [])));
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
    <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-5">
      <div className="flex items-start gap-2.5 mb-4">
        <HelpCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-semibold text-amber-900">A couple more details would help</h3>
          <p className="text-sm text-amber-800 mt-0.5">
            {unknownRequirements.length} item{unknownRequirements.length > 1 ? 's are' : ' is'} waiting on this — we won't guess.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allMissing.includes('mpcb_category') && (
          <div className="bg-white p-3.5 rounded-xl border border-amber-100">
            <label className="field-label">Pollution control category</label>
            <select
              value={localMpcb}
              onChange={(e) => setLocalMpcb(e.target.value)}
              className="field-input"
            >
              <option value="">Still not sure</option>
              <option value="Orange">Orange (typical for food processing)</option>
              <option value="Red">Red (heavy discharge)</option>
              <option value="Green">Green (low pollution)</option>
              <option value="White">White (non-polluting)</option>
            </select>
          </div>
        )}

        {allMissing.includes('in_esic_implemented_area') && (
          <div className="bg-white p-3.5 rounded-xl border border-amber-100">
            <label className="field-label">Is your area ESIC-notified?</label>
            <div className="flex gap-4 mt-2">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-ink-700">
                <input type="radio" name="esic_area" checked={localEsic === true} onChange={() => setLocalEsic(true)} className="text-brand focus:ring-brand" />
                Yes
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-sm text-ink-700">
                <input type="radio" name="esic_area" checked={localEsic === false} onChange={() => setLocalEsic(false)} className="text-brand focus:ring-brand" />
                No
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={isLoading}
          onClick={handleUpdateAndReEvaluate}
          className="px-4 py-2 bg-brand text-white hover:bg-brand-dark rounded-full text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Updating…' : 'Update and re-check'}
        </button>
      </div>
    </div>
  );
};
