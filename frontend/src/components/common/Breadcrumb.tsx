import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

interface BreadcrumbItem {
  label: string;
  step?: number;
}

export const Breadcrumb: React.FC<{ items: BreadcrumbItem[] }> = ({ items }) => {
  const { goToStep } = useAssessment();

  return (
    <nav className="border-b border-slate-200 bg-white" aria-label="Breadcrumb">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center gap-1.5 text-sm text-slate-500 overflow-x-auto">
        <button onClick={() => goToStep(0)} className="flex items-center gap-1 hover:text-brand transition shrink-0">
          <Home className="w-3.5 h-3.5" />
          Home
        </button>
        {items.map((item, idx) => (
          <React.Fragment key={idx}>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300 shrink-0" />
            {item.step !== undefined ? (
              <button onClick={() => goToStep(item.step!)} className="hover:text-brand transition truncate">
                {item.label}
              </button>
            ) : (
              <span className="font-medium text-ink-900 truncate">{item.label}</span>
            )}
          </React.Fragment>
        ))}
      </div>
    </nav>
  );
};
