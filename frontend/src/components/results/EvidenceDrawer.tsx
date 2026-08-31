import React from 'react';
import { ExternalLink, BookOpen, Calendar, CheckCircle2, XCircle, HelpCircle, ArrowRight } from 'lucide-react';
import { Requirement } from '../../types/engine';
import { ConfidenceTag } from '../common/ConfidenceTag';

const KIND_LABEL: Record<string, { text: string; icon: React.ComponentType<{ className?: string }>; classes: string }> = {
  POSITIVE_DEFINITE: { text: 'This rule applies to you', icon: CheckCircle2, classes: 'bg-emerald-50 text-emerald-700' },
  ACTIVE_EXCLUSION: { text: "A specific rule says this doesn't apply", icon: XCircle, classes: 'bg-slate-100 text-slate-600' },
  ABSENCE_OF_TRIGGER: { text: 'Nothing triggered this rule', icon: XCircle, classes: 'bg-slate-100 text-slate-600' },
  POSITIVE_INDETERMINATE: { text: 'Cannot confirm — missing information', icon: HelpCircle, classes: 'bg-amber-50 text-amber-700' },
};

export const EvidenceDrawer: React.FC<{ requirement: Requirement }> = ({ requirement }) => {
  return (
    <div className="bg-slate-50 border-t border-slate-100 p-4 sm:p-5 space-y-4">
      {requirement.evidence && requirement.evidence.length > 0 ? (
        requirement.evidence.map((ev, idx) => {
          const kind = KIND_LABEL[ev.evidence_kind];
          const KindIcon = kind?.icon;
          return (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-xs font-medium text-brand bg-brand-tint px-2 py-0.5 rounded-md">
                    {ev.rule_id}
                  </span>
                  <span className="font-medium text-ink-900">{ev.rule_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <ConfidenceTag status={ev.verification_status} />
                  {ev.last_verified && (
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {ev.last_verified}
                    </span>
                  )}
                </div>
              </div>

              {kind && (
                <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${kind.classes}`}>
                  <KindIcon className="w-3.5 h-3.5" />
                  {kind.text}
                </div>
              )}

              {ev.facts_used && ev.facts_used.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                      <tr>
                        <th className="p-2 font-medium">What we checked</th>
                        <th className="p-2 font-medium">Your value</th>
                        <th className="p-2 font-medium">Condition</th>
                        <th className="p-2 font-medium">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {ev.facts_used.map((f, fIdx) => (
                        <tr key={fIdx}>
                          <td className="p-2 font-medium text-ink-900">{f.fact}</td>
                          <td className="p-2 text-slate-600">{f.value === null ? '—' : String(f.value)}</td>
                          <td className="p-2 text-slate-500">{f.op} {JSON.stringify(f.target)}</td>
                          <td className="p-2">
                            {f.result === 'TRUE' ? (
                              <span className="text-emerald-600 font-medium">Yes</span>
                            ) : f.result === 'FALSE' ? (
                              <span className="text-slate-400 font-medium">No</span>
                            ) : (
                              <span className="text-amber-600 font-medium">Unknown</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {ev.note && <div className="bg-slate-50 rounded-lg p-2.5 text-xs text-slate-600">{ev.note}</div>}

              {ev.source_detail && (
                <div className="bg-brand-tint rounded-lg p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-brand-dark flex items-center gap-1.5 text-xs">
                      <BookOpen className="w-3.5 h-3.5" />
                      Official source
                    </div>
                    {ev.source_detail.source_url && (
                      <a
                        href={ev.source_detail.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark bg-white px-2 py-1 rounded-md"
                      >
                        View source
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-ink-700">
                    <div>
                      <span className="text-slate-500 block">Authority</span>
                      {ev.source_detail.authority}
                    </div>
                    <div>
                      <span className="text-slate-500 block">Document</span>
                      {ev.source_detail.document_title} {ev.source_detail.document_number ? `(${ev.source_detail.document_number})` : ''}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })
      ) : (
        <div className="text-sm text-slate-500 italic p-3 bg-white rounded-xl border border-slate-200">
          No rule trace recorded.
        </div>
      )}

      {requirement.depends_on && requirement.depends_on.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-3.5 space-y-1.5">
          <div className="text-xs font-medium text-ink-700 flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-brand" />
            Do these first
          </div>
          {requirement.depends_on.map((dep, dIdx) => (
            <div key={dIdx} className="flex items-start gap-2 bg-slate-50 p-2 rounded-lg text-xs">
              <span className="font-medium text-brand">{dep.requirement_id}</span>
              <span className="text-slate-500">{dep.basis}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
