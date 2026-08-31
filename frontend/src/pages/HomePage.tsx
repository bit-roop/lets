import React from 'react';
import { ArrowRight, ShieldCheck, BookOpen, GitFork } from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { PersonaSelector } from '../components/intake/PersonaSelector';

export const HomePage: React.FC = () => {
  const { goToStep, resetAssessment } = useAssessment();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      <div className="text-center space-y-4">
        <span className="inline-block text-xs font-medium text-brand bg-brand-tint px-3 py-1 rounded-full">
          Smart India Hackathon 2026 · PS 26130
        </span>
        <h1 className="text-3xl sm:text-4xl font-semibold text-ink-900 tracking-tight leading-tight">
          Know exactly which approvals your business needs
        </h1>
        <p className="text-base text-slate-500 max-w-xl mx-auto leading-relaxed">
          Answer a few questions about your food business in Maharashtra. We'll tell you which
          registrations and licences apply — and show the exact law behind each one.
        </p>
        <div className="pt-2">
          <button
            onClick={() => {
              resetAssessment();
              goToStep(1);
            }}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-brand text-white text-sm font-medium hover:bg-brand-dark transition shadow-card"
          >
            Start your check
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <PersonaSelector />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-200">
        <div className="space-y-1.5">
          <ShieldCheck className="w-5 h-5 text-brand" />
          <h3 className="text-sm font-semibold text-ink-900">Never guesses</h3>
          <p className="text-sm text-slate-500 leading-relaxed">
            If we don't have enough information, we say so — instead of assuming an answer.
          </p>
        </div>
        <div className="space-y-1.5">
          <BookOpen className="w-5 h-5 text-brand" />
          <h3 className="text-sm font-semibold text-ink-900">Shows its sources</h3>
          <p className="text-sm text-slate-500 leading-relaxed">
            Every answer links to the actual law, notification, or department behind it.
          </p>
        </div>
        <div className="space-y-1.5">
          <GitFork className="w-5 h-5 text-brand" />
          <h3 className="text-sm font-semibold text-ink-900">Plans the order</h3>
          <p className="text-sm text-slate-500 leading-relaxed">
            Understands which approvals depend on others, so you know where to start.
          </p>
        </div>
      </div>
    </div>
  );
};
