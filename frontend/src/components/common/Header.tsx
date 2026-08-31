import React from 'react';
import { ShieldCheck, Layers, RefreshCw, Landmark, AlertCircle } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Header: React.FC = () => {
  const { health, currentStep, goToStep, resetAssessment } = useAssessment();

  return (
    <header className="bg-gov-navy text-white shadow-md border-b-4 border-gov-gold">
      {/* Top Gov Bar */}
      <div className="bg-gov-slate px-4 py-1 text-xs text-slate-300 border-b border-slate-700 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-gov-goldLight tracking-wider uppercase">
            Government of Maharashtra · SIH 2026 PS 26130
          </span>
          <span className="text-slate-500">|</span>
          <span>Regulatory Reasoning & Compliance Pre-Scrutiny Subsystem</span>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          {health ? (
            <span className="flex items-center text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-1.5"></span>
              Engine v{health.engine_version} Online ({health.verification_summary?.VERIFIED || 0} Verified Rules)
            </span>
          ) : (
            <span className="flex items-center text-amber-400">
              <AlertCircle className="w-3.5 h-3.5 mr-1" />
              Checking Engine Connection...
            </span>
          )}
        </div>
      </div>

      {/* Main Brand Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div 
          className="flex items-center space-x-3 cursor-pointer group"
          onClick={() => goToStep(0)}
          title="Return to Portal Gateway"
        >
          <div className="w-10 h-10 rounded bg-gov-navyLight border border-gov-gold/40 flex items-center justify-center text-gov-gold font-bold text-lg shadow-inner">
            <Landmark className="w-6 h-6 text-gov-gold" />
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              MAITRI-COMPLY
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gov-gold/20 text-gov-gold border border-gov-gold/40 uppercase">
                Prototype v3
              </span>
            </div>
            <div className="text-xs text-slate-300">
              Regulatory Approval Discovery & Statutory Assessment Matrix
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2 text-sm">
          <button
            onClick={() => goToStep(0)}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep === 0
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
          >
            Portal Home
          </button>

          <button
            onClick={() => {
              resetAssessment();
              goToStep(1);
            }}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep >= 1 && currentStep <= 5
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
          >
            Start Assessment
          </button>

          {currentStep === 6 && (
            <button
              onClick={() => goToStep(6)}
              className="px-3 py-1.5 rounded font-medium text-xs transition border bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight"
            >
              Results Matrix
            </button>
          )}

          <button
            onClick={() => goToStep(7)}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep === 7
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
          >
            Case Dashboard
          </button>

          <button
            onClick={() => goToStep(8)}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep === 8
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
            title="Officer view over cases filed in this prototype"
          >
            Department Review
          </button>

          <button
            onClick={() => goToStep(9)}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep === 9
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
            title="Critical-path timeline of your approvals"
          >
            Roadmap
          </button>

          <button
            onClick={() => goToStep(10)}
            className={`px-3 py-1.5 rounded font-medium text-xs transition border ${
              currentStep === 10
                ? 'bg-gov-gold text-gov-navy border-gov-gold font-semibold'
                : 'bg-gov-navyLight/60 text-slate-200 border-slate-600 hover:bg-gov-navyLight'
            }`}
            title="Browse every approval type and its official source"
          >
            Library
          </button>

          <button
            onClick={resetAssessment}
            className="p-1.5 rounded bg-gov-navyLight/40 hover:bg-gov-navyLight text-slate-300 hover:text-white border border-slate-700 transition"
            title="Reset Form"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};