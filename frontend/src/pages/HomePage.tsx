import React from 'react';
import {
  ShieldCheck,
  Building2,
  FileCheck2,
  GitFork,
  ArrowRight,
  Landmark,
  Scale,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { PersonaSelector } from '../components/intake/PersonaSelector';

export const HomePage: React.FC = () => {
  const { goToStep, resetAssessment } = useAssessment();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Institutional Card */}
      <div className="bg-gov-navy text-white rounded-lg p-6 sm:p-8 border-l-8 border-gov-gold shadow-md">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider bg-gov-navyLight text-gov-gold border border-gov-gold/30">
            <Landmark className="w-3.5 h-3.5 text-gov-gold" />
            Smart India Hackathon 2026 · Problem Statement 26130
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
            Intelligent Statutory Approval Discovery & Compliance Pre-Scrutiny Platform
          </h1>

          <p className="text-sm text-slate-200 leading-relaxed">
            Eliminates regulatory ambiguity for food processing and industrial units in Maharashtra. 
            Deterministically derives the exact set of registrations, licences, permissions, NOCs, 
            and safety compliances required under state and central statutes—complete with legal provenance and official gazette citations.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={() => {
                resetAssessment();
                goToStep(1);
              }}
              className="px-5 py-2.5 rounded bg-gov-gold text-gov-navy font-bold text-xs uppercase tracking-wider hover:bg-gov-goldLight transition shadow flex items-center gap-2"
            >
              Start New Compliance Assessment
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Preset Persona Quick-Load Component */}
      <PersonaSelector />

      {/* Core Architectural Pillars */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wider text-gov-navy mb-4 flex items-center gap-2">
          <Scale className="w-4 h-4 text-gov-navyLight" />
          Statutory Derivation Architecture & Standards
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-white p-4 rounded border border-slate-300 shadow-2xs space-y-2">
            <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-gov-navy font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-700" />
            </div>
            <h3 className="font-bold text-gov-navy text-sm">Deterministic Kleene Engine</h3>
            <p className="text-slate-600 leading-relaxed">
              Powered by three-valued logic. Missing facts evaluate strictly as <strong>UNKNOWN</strong> rather than collapsing to false, preventing silent loss of regulatory obligations.
            </p>
          </div>

          <div className="bg-white p-4 rounded border border-slate-300 shadow-2xs space-y-2">
            <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-gov-navy font-bold">
              <BookOpen className="w-4 h-4 text-gov-navy" />
            </div>
            <h3 className="font-bold text-gov-navy text-sm">Auditable Gazette Provenance</h3>
            <p className="text-slate-600 leading-relaxed">
              Every requirement resolution provides complete evidence tracing to specific notifications from DISH, FSSAI, MPCB, Boilers Directorate, and MSME Ministry.
            </p>
          </div>

          <div className="bg-white p-4 rounded border border-slate-300 shadow-2xs space-y-2">
            <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-gov-navy font-bold">
              <GitFork className="w-4 h-4 text-gov-navy" />
            </div>
            <h3 className="font-bold text-gov-navy text-sm">Parallel Workflow Sequencing</h3>
            <p className="text-slate-600 leading-relaxed">
              Models legal and operational dependencies as a directed acyclic graph (DAG), identifying parallel tracks and reducing end-to-end journey duration.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
