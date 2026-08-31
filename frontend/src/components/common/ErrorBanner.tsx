import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const ErrorBanner: React.FC = () => {
  const { error, clearError } = useAssessment();

  if (!error) return null;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
      <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
        <AlertCircle className="w-4.5 h-4.5 text-red-500 shrink-0 mt-0.5" />
        <p className="text-sm text-red-800 flex-1">{error}</p>
        <button
          onClick={clearError}
          className="text-red-400 hover:text-red-700 transition"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
