import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Printer,
  RotateCcw,
  ShieldAlert,
  Sliders,
  XCircle,
} from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { RequirementCard } from '../components/results/RequirementCard';
import { MissingFactsBox } from '../components/results/MissingFactsBox';
import { DerivedFactsBox } from '../components/results/DerivedFactsBox';
import { PersonaSelector } from '../components/intake/PersonaSelector';
import { DocumentReadinessPanel } from '../components/results/DocumentReadinessPanel';
import { Expandable, JourneyRail } from '../components/lifecycle/LifecycleStatus';

export const ResultsPage: React.FC = () => {
  const { evaluationResult, facts, setFact, runEvaluation, goToStep, isLoading } = useAssessment();
  const [showDemoTools, setShowDemoTools] = useState<boolean>(false);

  if (!evaluationResult) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <h3 className="text-sm font-bold text-gov-navy mb-2">No assessment yet</h3>
        <p className="text-xs text-slate-500 mb-4">
          Complete the intake wizard to see which approvals apply to your unit.
        </p>
        <button
          onClick={() => goToStep(1)}
          className="px-4 py-2 bg-gov-navy text-white rounded text-xs font-bold"
        >
          Start an assessment
        </button>
      </div>
    );
  }

  const { applicable, not_applicable, unknown, conflict, derived_facts, derivation_diagnostics, warnings } =
    evaluationResult;

  const handleTurnoverShift = async (newTurnover: number) => {
    setFact('annual_turnover', newTurnover);
    await runEvaluation({ ...facts, annual_turnover: newTurnover });
  };

  return (
    <div>
      <Breadcrumb items={[{ label: 'Intake Assessment', step: 1 }, { label: 'Your approvals' }]} />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-slate-300">
          <div>
            <h1 className="text-xl font-bold text-gov-navy">Approvals you need</h1>
            <p className="text-xs text-slate-600 mt-1">
              {facts._name || facts.entity_name || 'Your unit'} · {facts.location_authority} (
              {facts.land_classification}) · assessed as of {evaluationResult.as_of}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => goToStep(1)}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              Edit answers
            </button>
            <button
              onClick={() => window.print()}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5 text-slate-500" />
              Print
            </button>
          </div>
        </div>

        <JourneyRail activeIndex={1} />

        {/* 1. What approvals do I need? */}
        <section className="space-y-3">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-bold text-gov-navy flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              {applicable.length} approval{applicable.length === 1 ? '' : 's'} apply to you
            </h2>
            <span className="text-[11px] text-slate-500">
              {unknown.length} need more information · {not_applicable.length} do not apply
            </span>
          </div>

          {applicable.length > 0 ? (
            <div className="space-y-3">
              {applicable.map((req) => (
                <RequirementCard key={req.requirement_id} requirement={req} />
              ))}
            </div>
          ) : (
            <div className="p-6 text-center bg-white rounded border border-slate-200 text-xs text-slate-500">
              No statutory requirement is applicable for the facts you provided.
            </div>
          )}
        </section>

        {/* Regulatory uncertainty stays visible, but compact. */}
        {unknown.length > 0 && (
          <section className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
            <h2 className="text-sm font-bold text-amber-900 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-amber-700" />
              Needs clarification ({unknown.length})
            </h2>
            <p className="text-xs text-amber-900">
              These requirements cannot be settled from the information given. They are not being
              treated as inapplicable — answering the questions below will resolve them.
            </p>
            <MissingFactsBox unknownRequirements={unknown} />
            <Expandable label="View the affected requirements">
              <div className="space-y-3">
                {unknown.map((req) => (
                  <RequirementCard key={req.requirement_id} requirement={req} />
                ))}
              </div>
            </Expandable>
          </section>
        )}

        {conflict.length > 0 && (
          <section className="bg-rose-50 border border-rose-200 rounded-lg p-4 space-y-2">
            <h2 className="text-sm font-bold text-rose-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-700" />
              Conflicting rules ({conflict.length})
            </h2>
            <p className="text-xs text-rose-900">
              Two or more rules disagree here. The conflict is reported rather than silently resolved.
            </p>
            <Expandable label="View the conflicts" defaultOpen>
              <div className="space-y-3">
                {conflict.map((req) => (
                  <RequirementCard key={req.requirement_id} requirement={req} defaultExpanded />
                ))}
              </div>
            </Expandable>
          </section>
        )}

        {/* 2. What documents do I need, and 3. are they ready for review? */}
        <DocumentReadinessPanel facts={facts} evaluation={evaluationResult} />

        {/* Engine detail, available for a judge but out of the applicant's way. */}
        <section className="bg-white border border-slate-300 rounded-lg p-4">
          <h2 className="text-xs font-bold text-gov-navy">How this was decided</h2>
          <p className="text-[11px] text-slate-600 mt-1">
            Every result above traces to a dated rule and an official source. Expand for the derived
            facts, excluded requirements, and engine notices.
          </p>

          <Expandable label="View details">
            <div className="space-y-4">
              <DerivedFactsBox derivedFacts={derived_facts} diagnostics={derivation_diagnostics} />

              <div>
                <h3 className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-2">
                  <XCircle className="w-3.5 h-3.5 text-slate-500" />
                  Does not apply to you ({not_applicable.length})
                </h3>
                {not_applicable.length > 0 ? (
                  <div className="space-y-3">
                    {not_applicable.map((req) => (
                      <RequirementCard key={req.requirement_id} requirement={req} />
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500">No requirement was excluded.</p>
                )}
              </div>

              {warnings && warnings.length > 0 && (
                <div className="bg-slate-50 border border-slate-200 rounded p-3 text-[11px] space-y-1.5">
                  <div className="font-bold text-slate-700 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                    Engine notices ({warnings.length})
                  </div>
                  {warnings.map((w, idx) => (
                    <div key={idx} className="text-slate-600">
                      <span className="text-amber-700 font-bold">[{w.severity}]</span>{' '}
                      <strong className="text-slate-800">{w.type}:</strong> {w.message}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Expandable>
        </section>

        {/* Demo controls, collapsed by default so they don't compete with the journey. */}
        <section className="bg-white border border-slate-300 rounded-lg p-4">
          <button
            type="button"
            onClick={() => setShowDemoTools((value) => !value)}
            aria-expanded={showDemoTools}
            className="text-xs font-bold text-gov-navy flex items-center gap-2"
          >
            <Sliders className="w-3.5 h-3.5 text-gov-navyLight" />
            {showDemoTools ? 'Hide demonstration controls' : 'Demonstration controls'}
          </button>

          {showDemoTools && (
            <div className="mt-3 space-y-4">
              <PersonaSelector />
              <div className="bg-gov-navy text-white rounded p-4">
                <h3 className="text-xs font-bold text-gov-gold">
                  Turnover thresholds under the FSSAI licensing regulations
                </h3>
                <p className="text-[11px] text-slate-200 mt-1 mb-3">
                  Change the declared turnover to watch the applicable FSSAI approval change.
                </p>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: 12000000, label: '₹1.20 Cr — registration (F-01)' },
                    { value: 80000000, label: '₹8.00 Cr — state licence (F-02)' },
                    { value: 600000000, label: '₹60.00 Cr — central licence (F-03)' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      disabled={isLoading}
                      onClick={() => handleTurnoverShift(option.value)}
                      className={`px-3 py-1.5 rounded text-[11px] font-bold border transition ${
                        facts.annual_turnover === option.value
                          ? 'bg-gov-gold text-gov-navy border-gov-gold'
                          : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
