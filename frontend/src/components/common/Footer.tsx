import React from 'react';
import { Shield, BookOpen, ExternalLink, Cpu } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-gov-slate text-slate-400 text-xs border-t border-slate-700 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-6 border-b border-slate-700">
          <div>
            <div className="text-slate-200 font-semibold text-sm mb-2 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-gov-gold" />
              Statutory Research Prototype
            </div>
            <p className="text-slate-400 leading-relaxed">
              Developed for <strong>Smart India Hackathon 2026 (Problem Statement 26130)</strong>. 
              Designed to extend the Maharashtra Industry, Trade and Investment Facilitation (MAITRI) Act 
              with deterministic regulatory derivation.
            </p>
          </div>

          <div>
            <div className="text-slate-200 font-semibold text-sm mb-2 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-gov-gold" />
              Engine Discipline & Standards
            </div>
            <p className="text-slate-400 leading-relaxed">
              Powered by <code>engine-v3</code>: three-valued Kleene logic, bounded fixed-point inference, 
              and active exclusion resolution. Zero non-deterministic LLMs in the regulatory derivation path.
            </p>
          </div>

          <div>
            <div className="text-slate-200 font-semibold text-sm mb-2 flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-gov-gold" />
              Statutory Transparency
            </div>
            <p className="text-slate-400 leading-relaxed">
              Every regulatory claim is tied to a versioned rule citing Maharashtra Factories Rules, 
              FSS Act 2006, Boilers Act 1923, MSMED Act 2006, or MPCB notifications.
            </p>
          </div>
        </div>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between text-slate-400 gap-2">
          <div>
            &copy; 2026 Regulatory Reasoning & Compliance Platform Prototype (PS 26130)
          </div>
          <div className="text-[11px] text-slate-400">
            Official Sources: mahadish.in · fssai.gov.in · mpcb.gov.in · mahaboiler.in
          </div>
        </div>
      </div>
    </footer>
  );
};
