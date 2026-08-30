import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, HelpCircle, Info, ShieldOff } from 'lucide-react';
import { VerificationRecord } from '../../types/verification';

/**
 * Shows what the document check found for one evidence item.
 *
 * Four separate rows, deliberately never merged into a single badge: what the
 * document appears to be, what was read from it, what the checks found, and
 * whether authenticity was established are four different questions with four
 * different answers. Collapsing them is how a system ends up implying that a
 * readable document is a genuine one.
 *
 * Internal vocabulary (document_id, condition_state, item_kind, state names)
 * is never shown to the applicant.
 */

interface Props {
  record: VerificationRecord;
  documentName: string;
}

const DISPOSITION_COPY: Record<string, { label: string; tone: string; icon: JSX.Element }> = {
  ACCEPTED_FOR_REVIEW: {
    label: 'Ready for an officer to review',
    tone: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    icon: <CheckCircle2 className="h-4 w-4" aria-hidden />,
  },
  NEEDS_APPLICANT_ACTION: {
    label: 'Needs your attention',
    tone: 'border-amber-300 bg-amber-50 text-amber-900',
    icon: <AlertTriangle className="h-4 w-4" aria-hidden />,
  },
  HUMAN_REVIEW_REQUIRED: {
    label: 'Needs to be checked by a person',
    tone: 'border-sky-200 bg-sky-50 text-sky-900',
    icon: <HelpCircle className="h-4 w-4" aria-hidden />,
  },
  REJECTED_STRUCTURAL: {
    label: 'This file could not be opened',
    tone: 'border-rose-200 bg-rose-50 text-rose-900',
    icon: <AlertTriangle className="h-4 w-4" aria-hidden />,
  },
  NOT_ANALYZED: {
    label: 'Not examined',
    tone: 'border-slate-200 bg-slate-50 text-slate-700',
    icon: <Info className="h-4 w-4" aria-hidden />,
  },
};

function documentCheckLine(record: VerificationRecord, documentName: string): string {
  if (record.disposition === 'NOT_ANALYZED') {
    if (record.disposition_reason === 'M4_APPLICABILITY_UNRESOLVED') {
      return 'We cannot yet tell whether this document is needed for your application, so it has not been examined.';
    }
    if (record.disposition_reason === 'M4_APPLICABILITY_FALSE') {
      return 'This document is not required for your application.';
    }
    return 'This system has not been set up to read this kind of document, so its contents have not been examined.';
  }

  switch (record.classification) {
    case 'MATCHES_EXPECTED':
      return `This appears to be the ${documentName} that was asked for.`;
    case 'DIFFERENT_KNOWN_TYPE':
      return `This does not appear to be the ${documentName}. It looks like a different document.`;
    case 'UNKNOWN_TYPE':
      return `We could not recognise this file as the ${documentName}. We are not able to say what it is.`;
    case 'INSUFFICIENT_EVIDENCE':
      return 'There was not enough readable content to tell what this document is.';
    default:
      return 'This document has not been identified.';
  }
}

function informationLine(record: VerificationRecord): string {
  if (record.extraction === 'UNREADABLE') {
    return 'No readable text was found. This may be a scan, which this system cannot read yet.';
  }
  if (record.extraction === 'FAILED') {
    return 'The file could not be processed because of a problem in this system. It can be tried again.';
  }
  if (record.extraction === 'NOT_ATTEMPTED') {
    return 'The contents of this file were not read.';
  }
  const found = record.fields.filter((field) => field.value_present).length;
  return `${found} of ${record.fields.length} pieces of information were read from the document text.`;
}

function checksLine(record: VerificationRecord): string {
  const relevant = record.findings.filter(
    (finding) => finding.outcome === 'MATCH' || finding.outcome === 'MISMATCH'
  );
  if (!relevant.length) return 'No checks could be carried out on this document.';
  const passed = relevant.filter((finding) => finding.outcome === 'MATCH').length;
  const failed = relevant.length - passed;
  return failed === 0
    ? `${passed} check${passed === 1 ? '' : 's'} passed.`
    : `${passed} passed, ${failed} need${failed === 1 ? 's' : ''} your attention.`;
}

/**
 * Authenticity language is kept strictly separate from every other row.
 * "Not applicable" and "not established" are different statements, and neither
 * is ever softened into an implication that the document is genuine.
 */
function authenticityLine(record: VerificationRecord): string {
  switch (record.authenticity.state) {
    case 'NOT_APPLICABLE_APPLICANT_AUTHORED':
      return 'Not applicable — this is a form you fill in yourself, so there is no issuing authority to check it against.';
    case 'NO_MECHANISM_AVAILABLE':
      return 'Not established — no service is available to this system that could confirm this document with the authority that issued it.';
    case 'FAILED':
      return 'A check on this document did not pass. An officer will need to look at it.';
    case 'NOT_ASSESSED':
    default:
      return 'Not assessed.';
  }
}

export default function VerificationBlock({ record, documentName }: Props) {
  const [expanded, setExpanded] = useState(false);
  // Extracted values are the applicant's own personal information. They stay
  // collapsed behind a second, explicit action so they are not left on screen
  // by default, and the summary above never needs them.
  const [showValues, setShowValues] = useState(false);
  const disposition = DISPOSITION_COPY[record.disposition] || DISPOSITION_COPY.NOT_ANALYZED;
  const readable = record.extraction === 'NATIVE_TEXT' || record.extraction === 'PARTIAL';

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Document check
          </span>
          <span className="text-[11px] text-slate-400">separate from the checklist status above</span>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${disposition.tone}`}
        >
          {disposition.icon}
          {disposition.label}
        </span>
      </div>

      <dl className="divide-y divide-slate-100 text-sm">
        <div className="px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">What this file appears to be</dt>
          <dd className="mt-0.5 text-slate-800">{documentCheckLine(record, documentName)}</dd>
        </div>

        <div className="px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">What we could read</dt>
          <dd className="mt-0.5 text-slate-800">{informationLine(record)}</dd>
        </div>

        <div className="px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">Checks</dt>
          <dd className="mt-0.5 text-slate-800">{checksLine(record)}</dd>
        </div>

        <div className="px-3 py-2">
          <dt className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <ShieldOff className="h-3.5 w-3.5" aria-hidden />
            Authenticity
          </dt>
          <dd className="mt-0.5 text-slate-700">{authenticityLine(record)}</dd>
        </div>
      </dl>

      {record.human_review?.reasons?.length ? (
        <div className="border-t border-sky-100 bg-sky-50/60 px-3 py-2">
          <p className="text-xs font-medium text-sky-900">Why a person needs to look at this</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-sky-900">
            {record.human_review.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {record.findings.some((finding) => finding.outcome === 'MISMATCH' && finding.remedy) ? (
        <div className="border-t border-amber-100 bg-amber-50/70 px-3 py-2">
          <ul className="space-y-1 text-xs text-amber-900">
            {record.findings
              .filter((finding) => finding.outcome === 'MISMATCH')
              .map((finding) => (
                <li key={finding.check_id}>
                  {finding.message}
                  {finding.remedy ? <span className="block text-amber-800">{finding.remedy}</span> : null}
                </li>
              ))}
          </ul>
        </div>
      ) : null}

      {record.findings.some((finding) => finding.outcome === 'UNKNOWN' && finding.remedy) ? (
        <div className="border-t border-sky-100 bg-sky-50/60 px-3 py-2">
          <p className="text-xs font-medium text-sky-900">Information that needs attention</p>
          <ul className="mt-1 space-y-1 text-xs text-sky-900">
            {record.findings
              .filter((finding) => finding.outcome === 'UNKNOWN' && finding.remedy)
              .map((finding) => (
                <li key={finding.check_id}>
                  {finding.message}
                  <span className="block text-sky-800">{finding.remedy}</span>
                </li>
              ))}
          </ul>
        </div>
      ) : null}

      {readable && record.fields.length > 0 ? (
        <div className="border-t border-slate-100">
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            Show what was read from this document
          </button>
          {expanded ? (
            <div className="px-3 pb-3">
              <table className="w-full text-xs">
                <tbody className="divide-y divide-slate-100">
                  {record.fields.map((field) => (
                    <tr key={field.field_id}>
                      <td className="py-1.5 pr-3 align-top text-slate-500">{field.label}</td>
                      <td className="py-1.5 pr-3 align-top text-slate-800">
                        {!field.value_present ? (
                          <span className="text-slate-400">not found in this document</span>
                        ) : showValues ? (
                          <span>
                            {field.display_value}
                            {field.masked ? (
                              <span className="ml-1 text-[10px] text-slate-500">(partly hidden)</span>
                            ) : null}
                          </span>
                        ) : (
                          <span className="text-slate-500">read from your document</span>
                        )}
                      </td>
                      <td className="py-1.5 align-top text-right">
                        {field.field_source === 'RESEARCH_REQUIRED' ? (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                            read for information only
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button
                type="button"
                onClick={() => setShowValues((value) => !value)}
                className="mt-2 text-[11px] font-medium text-slate-600 underline hover:text-slate-800"
              >
                {showValues ? 'Hide the values read from this document' : 'Show the values read from this document'}
              </button>
              <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                Items marked “read for information only” are not used to accept or reject your
                submission, because our regulatory sources do not confirm what those fields should
                contain. Names and identity numbers are stored only in a partly hidden form.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
