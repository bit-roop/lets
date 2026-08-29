import React from 'react';
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';
import { VerificationStatus } from '../../types/engine';

export const ConfidenceTag: React.FC<{
  status?: VerificationStatus;
  confidence?: 'high' | 'medium' | 'low';
  showLabel?: boolean;
}> = ({ status, confidence, showLabel = true }) => {
  if (status === 'VERIFIED' || confidence === 'high') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200"
        title="Direct statutory backing verified against department gazette / notification."
      >
        <ShieldCheck className="w-3 h-3 text-emerald-600" />
        {showLabel && 'VERIFIED SOURCE'}
      </span>
    );
  }

  if (status === 'SECONDARY' || confidence === 'medium') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200"
        title="Derived from consistent secondary sources; awaiting direct gazette verification."
      >
        <Shield className="w-3 h-3 text-amber-600" />
        {showLabel && 'SECONDARY PROVENANCE'}
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-800 border border-rose-200"
      title="Unverified / disputed threshold. Not used as a definitive statutory claim."
    >
      <ShieldAlert className="w-3 h-3 text-rose-600" />
      {showLabel && 'UNVERIFIED DATA'}
    </span>
  );
};
