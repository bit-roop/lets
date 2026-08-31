import React, { useEffect, useMemo, useState } from 'react';
import {
  GanttChartSquare, AlertTriangle, Info, Clock, Layers, Gauge,
  ChevronRight, X, ArrowRight,
} from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { ConfidenceTag } from '../components/common/ConfidenceTag';
import { api, ApiError } from '../api/client';
import { EvaluateWithWorkflowResponse, Schedule, WorkflowNode } from '../types/workflow';

type Mode = 'COMMITTED' | 'PROVISIONAL';

const StatCard: React.FC<{ icon: React.ComponentType<{ className?: string }>; label: string; value: string; hint?: string }> = ({
  icon: Icon,
  label,
  value,
  hint,
}) => (
  <div className="bg-white rounded-xl border border-slate-200 p-4">
    <div className="flex items-center gap-2 text-slate-400 mb-1.5">
      <Icon className="w-4 h-4" />
      <span className="text-xs font-medium">{label}</span>
    </div>
    <div className="text-xl font-semibold text-ink-900">{value}</div>
    {hint && <div className="text-xs text-slate-400 mt-0.5">{hint}</div>}
  </div>
);

export const RoadmapPage: React.FC = () => {
  const { facts, asOfDate, evaluationResult, goToStep } = useAssessment();
  const [data, setData] = useState<EvaluateWithWorkflowResponse | null>(null);
  const [mode, setMode] = useState<Mode>('COMMITTED');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!evaluationResult) return;
    setLoading(true);
    setError(null);
    api
      .evaluateWithWorkflow(facts, asOfDate)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not build the roadmap.'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evaluationResult]);

  const activeSchedule: Schedule | null = useMemo(() => {
    if (!data) return null;
    return mode === 'COMMITTED' ? data.workflow.schedule : data.workflow.provisional_schedule;
  }, [data, mode]);

  const nodeLookup: Record<string, WorkflowNode> = data?.workflow.nodes || {};

  if (!evaluationResult) {
    return (
      <div className="max-w-lg mx-auto px-4 py-20 text-center">
        <h3 className="text-base font-semibold text-ink-900 mb-2">No roadmap yet</h3>
        <p className="text-sm text-slate-500 mb-5">Run a compliance check first — the roadmap is built from its results.</p>
        <button onClick={() => goToStep(1)} className="px-5 py-2.5 bg-brand text-white rounded-full text-sm font-medium">
          Start check
        </button>
      </div>
    );
  }

  if (loading) {
    return <div className="max-w-lg mx-auto px-4 py-20 text-center text-sm text-slate-500">Building your roadmap…</div>;
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto px-4 py-20 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const { workflow } = data;
  const delta = workflow.provisional_delta;

  if (!activeSchedule || Object.keys(activeSchedule.nodes).length === 0) {
    return (
      <div>
        <Breadcrumb items={[{ label: 'Roadmap' }]} />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="p-10 text-center bg-white rounded-2xl border border-slate-200 text-sm text-slate-500">
            Nothing to schedule yet — no requirements are confirmed applicable
            {mode === 'COMMITTED' ? ' (try the "Pending info included" view).' : '.'}
          </div>
        </div>
      </div>
    );
  }

  const maxDay = Math.max(activeSchedule.parallel_duration_days, activeSchedule.critical_path_duration_days, 1);
  const selectedNode = selected ? nodeLookup[selected] : null;
  const selectedTiming = selected ? activeSchedule.nodes[selected] : null;

  return (
    <div>
      <Breadcrumb items={[{ label: 'Compliance check', step: 6 }, { label: 'Roadmap' }]} />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink-900 flex items-center gap-2">
              <GanttChartSquare className="w-5 h-5 text-brand" />
              Approval roadmap
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              What to file, in what order, and how long it should take based on statutory dependencies.
            </p>
          </div>
          <div className="flex items-center bg-white border border-slate-200 rounded-full p-1 text-sm">
            <button
              onClick={() => setMode('COMMITTED')}
              className={`px-3.5 py-1.5 rounded-full font-medium transition ${mode === 'COMMITTED' ? 'bg-brand text-white' : 'text-slate-500 hover:text-ink-900'}`}
            >
              Confirmed only
            </button>
            <button
              onClick={() => setMode('PROVISIONAL')}
              className={`px-3.5 py-1.5 rounded-full font-medium transition ${mode === 'PROVISIONAL' ? 'bg-brand text-white' : 'text-slate-500 hover:text-ink-900'}`}
            >
              Pending info included
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            icon={Clock}
            label="Fastest possible"
            value={`${activeSchedule.parallel_duration_days} ${activeSchedule.duration_unit.replace('sla_', '')}`}
            hint="Filing independent approvals in parallel"
          />
          <StatCard
            icon={Layers}
            label="One at a time"
            value={`${activeSchedule.sequential_duration_days} ${activeSchedule.duration_unit.replace('sla_', '')}`}
            hint="If filed strictly in sequence"
          />
          <StatCard
            icon={GanttChartSquare}
            label="Critical path"
            value={`${activeSchedule.critical_path_duration_days} days`}
            hint={`${activeSchedule.critical_paths.length || 0} longest chain(s)`}
          />
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1.5">
              <Gauge className="w-4 h-4" />
              <span className="text-xs font-medium">Schedule confidence</span>
            </div>
            {activeSchedule.schedule_confidence === 'not_applicable' ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                No ordering constraints
              </span>
            ) : (
              <ConfidenceTag confidence={activeSchedule.schedule_confidence as 'high' | 'medium' | 'low'} />
            )}
          </div>
        </div>

        {activeSchedule.duration_completeness === 'PARTIAL' && (
          <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-sm text-amber-800">
            <Info className="w-4 h-4 mt-0.5 shrink-0" />
            Some approvals don't have a recorded processing time, so this timeline is a lower bound — the real duration could be longer.
          </div>
        )}

        {mode === 'PROVISIONAL' && delta && delta.additional_node_count > 0 && (
          <div className="bg-brand rounded-2xl p-5 space-y-3">
            <div className="text-white text-sm font-medium">{delta.summary_explanation}</div>
            <div className="space-y-2">
              {delta.additional_requirements.map((d) => (
                <div key={d.requirement_id} className="bg-white/10 rounded-xl p-3 text-sm text-white/90">
                  <span className="font-medium text-white">{d.name}:</span> {d.explanation}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Gantt chart */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 overflow-x-auto">
          <div className="min-w-[640px]">
            {/* day ruler */}
            <div className="flex justify-between text-[11px] text-slate-400 mb-2 pl-48 pr-2">
              <span>Day 0</span>
              <span>Day {Math.round(maxDay / 2)}</span>
              <span>Day {maxDay}</span>
            </div>

            <div className="space-y-2">
              {activeSchedule.parallel_bands.map((band, bandIdx) => (
                <div key={bandIdx} className="space-y-1.5">
                  {band.map((rid) => {
                    const node = nodeLookup[rid];
                    const timing = activeSchedule.nodes[rid];
                    if (!node || !timing) return null;

                    const leftPct = (timing.earliest_start_day / maxDay) * 100;
                    const widthPct = Math.max(((timing.earliest_finish_day - timing.earliest_start_day) / maxDay) * 100, 1.5);
                    const isProvisionalOnly = node.state === 'UNKNOWN';

                    return (
                      <div key={rid} className="flex items-center gap-3">
                        <div className="w-48 shrink-0 text-xs text-ink-700 font-medium truncate pr-2" title={node.name}>
                          {node.name}
                        </div>
                        <div className="relative flex-1 h-7 bg-slate-50 rounded-lg">
                          <button
                            onClick={() => setSelected(rid)}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className={`absolute top-0.5 bottom-0.5 rounded-md flex items-center px-2 text-[11px] font-medium text-white transition hover:opacity-90 ${
                              timing.on_critical_path
                                ? 'bg-red-500'
                                : isProvisionalOnly
                                ? 'bg-amber-400 bg-[repeating-linear-gradient(45deg,rgba(255,255,255,.35)_0,rgba(255,255,255,.35)_4px,transparent_4px,transparent_8px)]'
                                : 'bg-brand'
                            }`}
                          >
                            <span className="truncate">{timing.duration_days}{timing.duration_is_lower_bound ? '+' : ''}d</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-brand" /> Standard</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-red-500" /> Critical path</span>
              {mode === 'PROVISIONAL' && (
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-amber-400" /> Pending confirmation</span>
              )}
            </div>
          </div>
        </div>

        {workflow.warnings.length > 0 && (
          <details className="bg-white border border-slate-200 rounded-2xl p-4 text-sm">
            <summary className="font-medium text-ink-700 cursor-pointer flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              {workflow.warnings.length} scheduling note{workflow.warnings.length > 1 ? 's' : ''}
            </summary>
            <div className="mt-2 space-y-1.5 text-xs text-slate-500">
              {workflow.warnings.map((w, idx) => (
                <div key={idx}>{w.message}</div>
              ))}
            </div>
          </details>
        )}
      </div>

      {/* Detail side panel */}
      {selectedNode && selectedTiming && (
        <div className="fixed inset-0 z-40 flex justify-end" onClick={() => setSelected(null)}>
          <div className="absolute inset-0 bg-ink-900/20" />
          <div className="relative bg-white w-full max-w-sm h-full shadow-xl p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setSelected(null)} className="absolute top-4 right-4 text-slate-400 hover:text-ink-900">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-semibold text-ink-900 pr-8">{selectedNode.name}</h3>
            <p className="text-xs text-slate-500 mt-1">{selectedNode.authority} · {selectedNode.statute}</p>

            <div className="grid grid-cols-2 gap-3 mt-5">
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-[11px] text-slate-400">Starts on day</div>
                <div className="text-sm font-semibold text-ink-900">{selectedTiming.earliest_start_day}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-[11px] text-slate-400">Finishes by day</div>
                <div className="text-sm font-semibold text-ink-900">{selectedTiming.earliest_finish_day}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-[11px] text-slate-400">Slack</div>
                <div className="text-sm font-semibold text-ink-900">
                  {selectedTiming.slack_days === null ? 'Unknown' : `${selectedTiming.slack_days} days`}
                </div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-[11px] text-slate-400">On critical path</div>
                <div className="text-sm font-semibold text-ink-900">{selectedTiming.on_critical_path ? 'Yes' : 'No'}</div>
              </div>
            </div>

            {selectedTiming.blocked_by.length > 0 && (
              <div className="mt-5">
                <div className="text-xs font-medium text-ink-700 mb-1.5">Waits on</div>
                <div className="space-y-1">
                  {selectedTiming.blocked_by.map((bid) => (
                    <div key={bid} className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 rounded-lg p-2">
                      <ChevronRight className="w-3 h-3 text-slate-400" />
                      {nodeLookup[bid]?.name || bid}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedTiming.blocks.length > 0 && (
              <div className="mt-4">
                <div className="text-xs font-medium text-ink-700 mb-1.5">Unblocks</div>
                <div className="space-y-1">
                  {selectedTiming.blocks.map((bid) => (
                    <div key={bid} className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 rounded-lg p-2">
                      <ArrowRight className="w-3 h-3 text-slate-400" />
                      {nodeLookup[bid]?.name || bid}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedNode.sla.note && (
              <div className="mt-5 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">{selectedNode.sla.note}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};