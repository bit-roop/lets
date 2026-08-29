import React from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ExternalLink,
  BookOpen,
  Scale,
  Calendar,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { Requirement, EvidenceItem } from '../../types/engine';
import { ConfidenceTag } from '../common/ConfidenceTag';

export const EvidenceDrawer: React.FC<{ requirement: Requirement }> = ({ requirement }) => {
  return (
    <div className="bg-slate-50 border-t border-slate-200 p-4 text-xs space-y-4 rounded-b">
      {/* Evidence Items */}
      {requirement.evidence && requirement.evidence.length > 0 ? (
        requirement.evidence.map((ev, idx) => (
          <div key={idx} className="bg-white border border-slate-200 rounded p-3.5 shadow-2xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-gov-navy bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {ev.rule_id} v{ev.version}
                </span>
                <span className="font-bold text-slate-800">{ev.rule_name}</span>
              </div>
              <div className="flex items-center gap-2">
                <ConfidenceTag status={ev.verification_status} />
                {ev.last_verified && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    Verified: {ev.last_verified}
                  </span>
                )}
              </div>
            </div>

            {/* Evidence Kind Banner */}
            <div className="flex items-center gap-2 text-[11.5px]">
              <span className="font-semibold text-slate-600">Evaluation Outcome:</span>
              {ev.evidence_kind === 'POSITIVE_DEFINITE' && (
                <span className="inline-flex items-center gap-1 text-emerald-800 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Condition Evaluated TRUE &rarr; Positive Requirement
                </span>
              )}
              {ev.evidence_kind === 'ACTIVE_EXCLUSION' && (
                <span className="inline-flex items-center gap-1 text-slate-800 font-semibold bg-slate-100 px-2 py-0.5 rounded border border-slate-300">
                  <XCircle className="w-3.5 h-3.5 text-slate-500" />
                  Active Statutory Exclusion Rule Fired TRUE (Definitive Negative)
                </span>
              )}
              {ev.evidence_kind === 'ABSENCE_OF_TRIGGER' && (
                <span className="inline-flex items-center gap-1 text-slate-600 font-semibold bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  Absence of Trigger &rarr; Requiring conditions did not fire
                </span>
              )}
              {ev.evidence_kind === 'POSITIVE_INDETERMINATE' && (
                <span className="inline-flex items-center gap-1 text-amber-800 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
                  Condition Indeterminate due to missing fact vector input
                </span>
              )}
            </div>

            {/* Facts Used Table */}
            {ev.facts_used && ev.facts_used.length > 0 && (
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1">
                  <Scale className="w-3.5 h-3.5 text-gov-navyLight" />
                  Facts Consulted & Condition Sub-expressions:
                </div>
                <div className="overflow-x-auto border border-slate-200 rounded">
                  <table className="w-full text-left border-collapse text-[11px]">
                    <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="p-2">Fact Key</th>
                        <th className="p-2">Applicant Declared Value</th>
                        <th className="p-2">Operator / Target</th>
                        <th className="p-2">Sub-Expression Result</th>
                        <th className="p-2">Origin</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 font-mono">
                      {ev.facts_used.map((f, fIdx) => (
                        <tr key={fIdx} className="hover:bg-slate-50">
                          <td className="p-2 font-bold text-gov-navy">{f.fact}</td>
                          <td className="p-2 text-slate-800">
                            {f.value === null ? '<MISSING>' : String(f.value)}
                          </td>
                          <td className="p-2 text-slate-600">
                            {f.op} {JSON.stringify(f.target)}
                          </td>
                          <td className="p-2">
                            {f.result === 'TRUE' ? (
                              <span className="text-emerald-700 font-bold">TRUE</span>
                            ) : f.result === 'FALSE' ? (
                              <span className="text-slate-500 font-bold">FALSE</span>
                            ) : (
                              <span className="text-amber-700 font-bold">UNKNOWN</span>
                            )}
                          </td>
                          <td className="p-2">
                            <span
                              className={`text-[9.5px] px-1.5 py-0.5 rounded font-sans font-semibold ${
                                f.fact_origin === 'DERIVED'
                                  ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                  : 'bg-slate-100 text-slate-700 border border-slate-200'
                              }`}
                            >
                              {f.fact_origin}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Note / Legal Reasoning */}
            {ev.note && (
              <div className="bg-slate-50 p-2.5 rounded border border-slate-200 text-slate-700 text-[11px] leading-relaxed">
                <strong>Statutory Note:</strong> {ev.note}
              </div>
            )}

            {/* Official Source Provenance & Link */}
            {ev.source_detail && (
              <div className="bg-gov-navy/5 border border-gov-navy/15 rounded p-3 text-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-gov-navy flex items-center gap-1.5 text-xs">
                    <BookOpen className="w-3.5 h-3.5 text-gov-gold" />
                    Authoritative Gazette & Statutory Authority:
                  </div>
                  {ev.source_detail.source_url && (
                    <a
                      href={ev.source_detail.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-gov-navy hover:text-gov-navyLight bg-white px-2 py-1 rounded border border-gov-navy/20 hover:border-gov-navy shadow-2xs transition"
                    >
                      View Official Source
                      <ExternalLink className="w-3 h-3 text-gov-gold" />
                    </a>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">Department / Authority:</span>
                    <span className="font-semibold text-slate-800">{ev.source_detail.authority}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Instrument / Gazette Order:</span>
                    <span className="font-semibold text-slate-800">
                      {ev.source_detail.document_title}{' '}
                      {ev.source_detail.document_number ? `(${ev.source_detail.document_number})` : ''}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="text-slate-500 italic p-3 bg-white rounded border border-slate-200">
          No rule evaluation trace recorded for this requirement.
        </div>
      )}

      {/* Dependency Graph Sequencing Notice */}
      {requirement.depends_on && requirement.depends_on.length > 0 && (
        <div className="bg-white border border-slate-200 rounded p-3 text-[11px] space-y-1.5">
          <div className="font-bold text-gov-navy uppercase tracking-wider flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-gov-navyLight" />
            Statutory Workflow Dependencies:
          </div>
          <div className="space-y-1">
            {requirement.depends_on.map((dep, dIdx) => (
              <div key={dIdx} className="flex items-start gap-2 bg-slate-50 p-2 rounded border border-slate-200">
                <ArrowRight className="w-3.5 h-3.5 text-gov-navy mt-0.5 shrink-0" />
                <div>
                  <span className="font-bold text-gov-navy mr-1.5">{dep.requirement_id}</span>
                  <span className="text-slate-700 font-medium">({dep.dependency_type} Precondition):</span>
                  <span className="text-slate-600 ml-1">{dep.basis}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
