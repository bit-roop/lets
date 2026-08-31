import React from 'react';
import {
  CheckCircle2,
  Clock,
  FileClock,
  Inbox,
  MessageSquareWarning,
  Reply,
  XCircle,
} from 'lucide-react';
import {
  ApplicationLifecycleStatus,
  ApprovalLifecycleStatus,
  QueryStatus,
} from '../../api/client';

type Tone = 'neutral' | 'progress' | 'attention' | 'good' | 'bad';

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 border-slate-300',
  progress: 'bg-sky-50 text-sky-900 border-sky-300',
  attention: 'bg-amber-50 text-amber-900 border-amber-300',
  good: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  bad: 'bg-rose-50 text-rose-900 border-rose-300',
};

/**
 * Wording is deliberate. A decision made here is a decision made in a
 * prototype simulation, and the label says so wherever it is shown.
 */
const APPLICATION_LABEL: Record<
  ApplicationLifecycleStatus,
  { text: string; tone: Tone; Icon: React.ElementType }
> = {
  SUBMITTED: { text: 'Awaiting review', tone: 'neutral', Icon: Inbox },
  UNDER_REVIEW: { text: 'Under review (simulation)', tone: 'progress', Icon: FileClock },
  QUERY_RAISED: { text: 'Query raised — your response needed', tone: 'attention', Icon: MessageSquareWarning },
  RESPONDED: { text: 'Response sent — with the department', tone: 'progress', Icon: Reply },
  GRANTED: { text: 'Granted in simulation', tone: 'good', Icon: CheckCircle2 },
  REJECTED: { text: 'Rejected in simulation', tone: 'bad', Icon: XCircle },
};

const APPROVAL_LABEL: Record<
  ApprovalLifecycleStatus,
  { text: string; tone: Tone; Icon: React.ElementType }
> = {
  SUBMITTED: { text: 'Awaiting review', tone: 'neutral', Icon: Inbox },
  IN_SCRUTINY: { text: 'In scrutiny', tone: 'progress', Icon: FileClock },
  QUERY_PENDING: { text: 'Query pending', tone: 'attention', Icon: MessageSquareWarning },
  GRANTED: { text: 'Granted in simulation', tone: 'good', Icon: CheckCircle2 },
  REJECTED: { text: 'Rejected in simulation', tone: 'bad', Icon: XCircle },
};

const QUERY_LABEL: Record<QueryStatus, { text: string; tone: Tone; Icon: React.ElementType }> = {
  OPEN: { text: 'Open', tone: 'attention', Icon: MessageSquareWarning },
  RESPONDED: { text: 'Response sent', tone: 'progress', Icon: Reply },
  RESOLVED: { text: 'Resolved', tone: 'good', Icon: CheckCircle2 },
};

const Badge: React.FC<{ text: string; tone: Tone; Icon: React.ElementType; title?: string }> = ({
  text,
  tone,
  Icon,
  title,
}) => (
  <span
    title={title}
    className={`inline-flex items-center gap-1.5 font-semibold rounded border px-2 py-0.5 text-[11px] ${TONE_CLASS[tone]}`}
  >
    <Icon className="w-3.5 h-3.5" />
    {text}
  </span>
);

export const ApplicationStatusBadge: React.FC<{ status: ApplicationLifecycleStatus }> = ({ status }) => {
  const entry = APPLICATION_LABEL[status] || {
    text: status,
    tone: 'neutral' as Tone,
    Icon: Clock,
  };
  return <Badge {...entry} title="Prototype case status. No government filing exists." />;
};

export const ApprovalStatusBadge: React.FC<{ status: ApprovalLifecycleStatus }> = ({ status }) => {
  const entry = APPROVAL_LABEL[status] || { text: status, tone: 'neutral' as Tone, Icon: Clock };
  return <Badge {...entry} title="Prototype approval status." />;
};

export const QueryStatusBadge: React.FC<{ status: QueryStatus }> = ({ status }) => {
  const entry = QUERY_LABEL[status] || { text: status, tone: 'neutral' as Tone, Icon: Clock };
  return <Badge {...entry} />;
};

/**
 * Evidence readiness comes from M4 and is shown unchanged. A simulated grant
 * never upgrades it, so the two are always rendered as separate facts.
 */
export const ReadinessBadge: React.FC<{ status?: string | null }> = ({ status }) => {
  const value = status || 'PENDING';
  const tone: Tone =
    value === 'READY' ? 'good'
      : value === 'INCOMPLETE' ? 'bad'
      : value === 'INDETERMINATE' ? 'attention'
      : 'neutral';
  const text =
    value === 'READY' ? 'Documents ready'
      : value === 'INCOMPLETE' ? 'Documents incomplete'
      : value === 'INDETERMINATE' ? 'Requirement unresolved'
      : value === 'UNSUPPORTED' ? 'No checklist encoded'
      : value;
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold ${TONE_CLASS[tone]}`}>
      {text}
    </span>
  );
};

/**
 * A compact expandable block. Detailed provenance and engine internals live
 * behind this rather than in front of the applicant.
 */
export const Expandable: React.FC<{
  label: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}> = ({ label, children, defaultOpen = false }) => {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div className="border-t border-slate-200 pt-2 mt-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="text-[11px] font-semibold text-gov-navy hover:underline"
      >
        {open ? `Hide ${label.toLowerCase()}` : label}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
};

/**
 * The single journey the prototype demonstrates, shown as one rail so the
 * applicant can see where the case sits without reading every panel.
 */
export const JOURNEY_STAGES = [
  'Assessment',
  'Approvals',
  'Documents',
  'Verification',
  'Submitted',
  'Department review',
  'Decision',
] as const;

export const JourneyRail: React.FC<{ activeIndex: number }> = ({ activeIndex }) => (
  <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px]" aria-label="Prototype journey">
    {JOURNEY_STAGES.map((stage, index) => {
      const done = index < activeIndex;
      const active = index === activeIndex;
      return (
        <li key={stage} className="flex items-center gap-1.5">
          <span
            className={`px-2 py-0.5 rounded border font-semibold ${
              active
                ? 'bg-gov-navy text-white border-gov-navy'
                : done
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-white text-slate-500 border-slate-200'
            }`}
            aria-current={active ? 'step' : undefined}
          >
            {stage}
          </span>
          {index < JOURNEY_STAGES.length - 1 && <span className="text-slate-300">›</span>}
        </li>
      );
    })}
  </ol>
);


