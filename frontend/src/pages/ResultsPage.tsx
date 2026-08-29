import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  FileCheck2,
  Calendar,
  Layers,
  ArrowLeft,
  RotateCcw,
  Sliders,
  Sparkles,
  Printer,
  ShieldAlert,
} from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { SummaryCards } from '../components/results/SummaryCards';
import { RequirementCard } from '../components/results/RequirementCard';
import { MissingFactsBox } from '../components/results/MissingFactsBox';
import { DerivedFactsBox } from '../components/results/DerivedFactsBox';
import { PersonaSelector } from '../components/intake/PersonaSelector';

export const ResultsPage: React.FC = () => {
  const { evaluationResult, facts, setFact, runEvaluation, goToStep, isLoading } = useAssessment();
  const [activeTab, setActiveTab] = useState<string>('APPLICABLE');
  const [showLiveDemoPanel, setShowLiveDemoPanel] = useState<boolean>(true);

  if (!evaluationResult) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <h3 className="text-sm font-bold text-gov-navy mb-2">No Active Assessment Found</h3>
        <p className="text-xs text-slate-500 mb-4">Please complete the intake wizard to generate compliance results.</p>
        <button
          onClick={() => goToStep(1)}
          className="px-4 py-2 bg-gov-navy text-white rounded text-xs font-bold"
        >
          Start New Assessment
        </button>
      </div>
    );
  }

  const { summary, applicable, not_applicable, unknown, conflict, derived_facts, derivation_diagnostics, warnings } =
    evaluationResult;

  // Live variable change helper
  const handleTurnoverShift = async (newTurnover: number) => {
    setFact('annual_turnover', newTurnover);
    const updatedFacts = { ...facts, annual_turnover: newTurnover };
    await runEvaluation(updatedFacts);
  };

  return (
    <div>
      <Breadcrumb
        items={[
          { label: 'Intake Assessment', step: 1 },
          { label: 'Regulatory Compliance Matrix' },
        ]}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Title & Metadata Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-300">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gov-gold bg-gov-navy px-2 py-0.5 rounded">
                Statutory Assessment Report
              </span>
              <span className="text-xs font-mono text-slate-500">
                Evaluation Date: {evaluationResult.as_of}
              </span>
            </div>
            <h1 className="text-xl font-bold text-gov-navy mt-1">
              Regulatory Approval & Compliance Assessment Matrix
            </h1>
            <p className="text-xs text-slate-600">
              Unit: <strong className="text-slate-800">{facts._name || facts.entity_name || 'Declared Entity'}</strong> &bull; Location:{' '}
              <strong className="text-slate-800">{facts.location_authority} ({facts.land_classification})</strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => goToStep(1)}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 transition shadow-2xs flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              Edit Profile
            </button>
            <button
              onClick={() => window.print()}
              className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 transition shadow-2xs flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5 text-slate-500" />
              Print / Save
            </button>
          </div>
        </div>

        {/* Persona Selector Bar for Quick Switching */}
        <PersonaSelector />

        {/* Live Variable Mutation Interactive Demonstration */}
        {showLiveDemoPanel && (
          <div className="bg-gradient-to-r from-gov-navy to-gov-navyLight text-white rounded-md p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-gov-gold" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-gov-gold">
                  Live Regulatory Demonstration · FSSAI Turnover Threshold Mutation
                </h3>
              </div>
              <button
                onClick={() => setShowLiveDemoPanel(false)}
                className="text-[11px] text-slate-300 hover:text-white underline"
              >
                Hide
              </button>
            </div>
            <p className="text-xs text-slate-200 mb-3 leading-relaxed">
              Demonstrates real-time statutory rule re-firing under the <strong>FSSAI 2026 Regulations (effective 1 April 2026)</strong>. 
              Click below to toggle annual turnover across statutory thresholds:
            </p>
            <div className="flex flex-wrap items-center gap-2.5">
              <button
                disabled={isLoading}
                onClick={() => handleTurnoverShift(12000000)}
                className={`px-3 py-1.5 rounded text-xs font-bold transition border ${
                  facts.annual_turnover === 12000000
                    ? 'bg-gov-gold text-gov-navy border-gov-gold ring-2 ring-white/40 font-extrabold'
                    : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                }`}
              >
                Set ₹1.20 Cr &rarr; Basic Registration (F-01)
              </button>

              <button
                disabled={isLoading}
                onClick={() => handleTurnoverShift(80000000)}
                className={`px-3 py-1.5 rounded text-xs font-bold transition border ${
                  facts.annual_turnover === 80000000
                    ? 'bg-gov-gold text-gov-navy border-gov-gold ring-2 ring-white/40 font-extrabold'
                    : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                }`}
              >
                Set ₹8.00 Cr &rarr; State Licence (F-02)
              </button>

              <button
                disabled={isLoading}
                onClick={() => handleTurnoverShift(600000000)}
                className={`px-3 py-1.5 rounded text-xs font-bold transition border ${
                  facts.annual_turnover === 600000000
                    ? 'bg-gov-gold text-gov-navy border-gov-gold ring-2 ring-white/40 font-extrabold'
                    : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                }`}
              >
                Set ₹60.00 Cr &rarr; Central Licence (F-03)
              </button>
            </div>
          </div>
        )}

        {/* 4-State Summary Metric Cards */}
        <SummaryCards
          summary={summary}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
        />

        {/* Derived Facts Box (e.g. MSME Eligible = True) */}
        <DerivedFactsBox
          derivedFacts={derived_facts}
          diagnostics={derivation_diagnostics}
        />

        {/* Actionable Missing Facts Box for UNKNOWN items */}
        <MissingFactsBox unknownRequirements={unknown} />

        {/* Rule Warnings (if any) */}
        {warnings && warnings.length > 0 && (
          <div className="bg-slate-50 border border-slate-300 rounded p-3 text-xs space-y-1.5">
            <div className="font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 text-[11px]">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              Engine Verification Notices & Warnings ({warnings.length})
            </div>
            <div className="space-y-1 font-mono text-[11px] text-slate-600">
              {warnings.map((w, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold">[{w.severity}]</span>
                  <span>
                    <strong className="text-slate-800">{w.type}:</strong> {w.message}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Requirement Tab Navigation */}
        <div className="border-b border-slate-300 flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('APPLICABLE')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'APPLICABLE'
                ? 'border-emerald-600 text-emerald-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Applicable Approvals ({applicable.length})
          </button>

          <button
            onClick={() => setActiveTab('UNKNOWN')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'UNKNOWN'
                ? 'border-amber-600 text-amber-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
            Needs Information ({unknown.length})
          </button>

          <button
            onClick={() => setActiveTab('NOT_APPLICABLE')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'NOT_APPLICABLE'
                ? 'border-slate-600 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <XCircle className="w-3.5 h-3.5 text-slate-500" />
            Not Applicable / Excluded ({not_applicable.length})
          </button>

          {conflict.length > 0 && (
            <button
              onClick={() => setActiveTab('CONFLICT')}
              className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition flex items-center gap-1.5 ${
                activeTab === 'CONFLICT'
                  ? 'border-rose-600 text-rose-900'
                  : 'border-transparent text-rose-600'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              Conflicts ({conflict.length})
            </button>
          )}
        </div>

        {/* Tab Content List */}
        <div className="space-y-3.5">
          {activeTab === 'APPLICABLE' && (
            <>
              {applicable.length > 0 ? (
                applicable.map((req) => <RequirementCard key={req.requirement_id} requirement={req} />)
              ) : (
                <div className="p-8 text-center bg-white rounded border border-slate-200 text-xs text-slate-500">
                  No statutory requirements applicable for this fact vector.
                </div>
              )}
            </>
          )}

          {activeTab === 'UNKNOWN' && (
            <>
              {unknown.length > 0 ? (
                unknown.map((req) => <RequirementCard key={req.requirement_id} requirement={req} defaultExpanded />)
              ) : (
                <div className="p-8 text-center bg-white rounded border border-slate-200 text-xs text-slate-500">
                  All requirements resolved deterministically. Zero indeterminate items.
                </div>
              )}
            </>
          )}

          {activeTab === 'NOT_APPLICABLE' && (
            <>
              {not_applicable.length > 0 ? (
                not_applicable.map((req) => <RequirementCard key={req.requirement_id} requirement={req} />)
              ) : (
                <div className="p-8 text-center bg-white rounded border border-slate-200 text-xs text-slate-500">
                  No excluded requirements recorded.
                </div>
              )}
            </>
          )}

          {activeTab === 'CONFLICT' && (
            <>
              {conflict.length > 0 ? (
                conflict.map((req) => <RequirementCard key={req.requirement_id} requirement={req} defaultExpanded />)
              ) : (
                <div className="p-8 text-center bg-white rounded border border-slate-200 text-xs text-slate-500">
                  No contradictory rule conflicts detected.
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
