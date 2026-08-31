import React, { useMemo, useState } from 'react';
import { BookOpen, ExternalLink, Search, Landmark, Clock, RefreshCw } from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { ConfidenceTag } from '../components/common/ConfidenceTag';

interface CatalogueEntry {
  name: string;
  requirement_type: string;
  authority: string;
  department: string;
  statute: string;
  sla_days: number | null;
  validity_years: number | null;
  renewal_lead_days: number | null;
}

interface SourceEntry {
  source_type: string;
  authority: string;
  document_title: string;
  source_url: string;
  section?: string;
  verification_status: 'VERIFIED' | 'SECONDARY' | 'UNVERIFIED';
  verified_at?: string;
  verified_by?: string;
  note?: string;
}

export const RegulatoryLibraryPage: React.FC = () => {
  const { catalogue, sources } = useAssessment();
  const [query, setQuery] = useState('');
  const [deptFilter, setDeptFilter] = useState<string>('ALL');

  const entries = catalogue as Record<string, CatalogueEntry>;
  const sourceEntries = sources as Record<string, SourceEntry>;

  const departments = useMemo(() => {
    const set = new Set<string>();
    Object.values(entries || {}).forEach((e) => e.department && set.add(e.department));
    return ['ALL', ...Array.from(set).sort()];
  }, [entries]);

  const filtered = useMemo(() => {
    return Object.entries(entries || {}).filter(([id, e]) => {
      const matchesDept = deptFilter === 'ALL' || e.department === deptFilter;
      const q = query.toLowerCase();
      const matchesQuery =
        !q ||
        e.name.toLowerCase().includes(q) ||
        e.statute?.toLowerCase().includes(q) ||
        e.authority?.toLowerCase().includes(q) ||
        id.toLowerCase().includes(q);
      return matchesDept && matchesQuery;
    });
  }, [entries, query, deptFilter]);

  const sourcesForAuthority = (authority: string) =>
    Object.entries(sourceEntries || {}).filter(([, s]) => s.authority === authority);

  return (
    <div>
      <Breadcrumb items={[{ label: 'Regulatory library' }]} />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink-900 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand" />
            Regulatory library
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Every approval type this checker knows about, and the official source behind each one — independent of any specific business.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, statute, or authority…"
              className="field-input pl-10"
            />
          </div>
          <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="field-input sm:w-56">
            {departments.map((d) => (
              <option key={d} value={d}>{d === 'ALL' ? 'All departments' : d}</option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-400">{filtered.length} of {Object.keys(entries || {}).length} approval types</div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(([id, entry]) => {
            const relatedSources = sourcesForAuthority(entry.authority);
            return (
              <div key={id} className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-ink-900">{entry.name}</h3>
                  <span className="text-[11px] font-mono text-brand bg-brand-tint px-1.5 py-0.5 rounded shrink-0">{id}</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">{entry.statute}</p>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 mt-3">
                  <span className="flex items-center gap-1.5"><Landmark className="w-3 h-3 text-slate-400" />{entry.authority}</span>
                  {entry.sla_days != null && (
                    <span className="flex items-center gap-1.5"><Clock className="w-3 h-3 text-slate-400" />{entry.sla_days} day turnaround</span>
                  )}
                  {entry.validity_years != null && (
                    <span className="flex items-center gap-1.5"><RefreshCw className="w-3 h-3 text-slate-400" />Valid {entry.validity_years} yr, renew {entry.renewal_lead_days}d before</span>
                  )}
                </div>

                {relatedSources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5">
                    {relatedSources.slice(0, 2).map(([sid, src]) => (
                      <a
                        key={sid}
                        href={src.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between text-xs bg-slate-50 hover:bg-slate-100 rounded-lg p-2 transition"
                      >
                        <span className="text-ink-700 truncate pr-2">{src.document_title}</span>
                        <span className="flex items-center gap-1.5 shrink-0">
                          <ConfidenceTag status={src.verification_status} showLabel={false} />
                          <ExternalLink className="w-3 h-3 text-slate-400" />
                        </span>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div className="p-10 text-center bg-white rounded-2xl border border-slate-200 text-sm text-slate-500">
            Nothing matches that search.
          </div>
        )}
      </div>
    </div>
  );
};