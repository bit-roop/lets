import React from 'react';
import { ShieldCheck, Shield, ShieldAlert } from 'lucide-react';
import { VerificationStatus } from '../../types/engine';

export const ConfidenceTag: React.FC<{
  status?: VerificationStatus;
  confidence?: 'high' | 'medium' | 'low';
  showLabel?: boolean;
}> = ({ status, confidence, showLabel = true }) => {
  if (status === 'VERIFIED' || confidence === 'high') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200"
        title="Confirmed directly against the government notification."
      >
        <ShieldCheck className="w-3 h-3" />
        {showLabel && 'Confirmed'}
      </span>
    );
  }

  if (status === 'SECONDARY' || confidence === 'medium') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"
        title="Based on consistent secondary sources, not yet checked against the original notification."
      >
        <Shield className="w-3 h-3" />
        {showLabel && 'Likely accurate'}
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200"
      title="Not yet verified — treat as a starting point, not a final answer."
    >
      <ShieldAlert className="w-3 h-3" />
      {showLabel && 'Unverified'}
    </span>
  );
};
