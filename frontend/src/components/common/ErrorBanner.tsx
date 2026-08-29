import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const ErrorBanner: React.FC = () => {
  const { error, clearError } = useAssessment();

  if (!error) return null;

  return (
    <div className="bg-rose-50 border-l-4 border-rose-600 p-4 mb-6 rounded-r shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-rose-600 mr-3 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-rose-900">System Notification</h4>
            <p className="text-xs text-rose-800 mt-0.5">{error}</p>
          </div>
        </div>
        <button
          onClick={clearError}
          className="text-rose-400 hover:text-rose-700 transition ml-4"
          aria-label="Dismiss error"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
