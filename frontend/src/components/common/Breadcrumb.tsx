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
    <nav className="flex items-center text-xs text-slate-500 py-2.5 px-4 bg-slate-100 border-b border-slate-200" aria-label="Breadcrumb">
      <div className="max-w-7xl mx-auto w-full flex items-center space-x-1.5 overflow-x-auto">
        <button
          onClick={() => goToStep(0)}
          className="flex items-center hover:text-gov-navy transition text-slate-600 font-medium"
        >
          <Home className="w-3.5 h-3.5 mr-1" />
          Gateway
        </button>

        {items.map((item, idx) => (
          <React.Fragment key={idx}>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            {item.step !== undefined ? (
              <button
                onClick={() => goToStep(item.step!)}
                className="hover:text-gov-navy font-medium text-slate-700 hover:underline truncate"
              >
                {item.label}
              </button>
            ) : (
              <span className="font-semibold text-gov-navy truncate">
                {item.label}
              </span>
            )}
          </React.Fragment>
        ))}
      </div>
    </nav>
  );
};
