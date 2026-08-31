import React from 'react';
import { Store, Factory, Building2, ArrowRight } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

interface PersonaCard {
  id: string;
  name: string;
  tagline: string;
  description: string;
  factsPills: string[];
  icon: React.ComponentType<{ className?: string }>;
}

const PERSONAS: PersonaCard[] = [
  {
    id: 'persona_a',
    name: 'Shree Ganesh Bakery',
    tagline: 'Small bakery, municipal area',
    description: '₹40L turnover, 6 workers, no boiler.',
    factsPills: ['₹40L turnover', '6 workers', 'No boiler'],
    icon: Store,
  },
  {
    id: 'persona_b',
    name: 'Sahyadri Foods Pvt Ltd',
    tagline: 'Mid-size food plant, MIDC Ranjangaon',
    description: '₹8Cr turnover, 67 workers, 500L steam boiler.',
    factsPills: ['₹8Cr turnover', '67 workers', '500L boiler'],
    icon: Factory,
  },
  {
    id: 'persona_c',
    name: 'Dairy Chilling Unit',
    tagline: 'Hot-water vessel, boiler-exempt',
    description: '500L vessel at 80°C — below the boiler threshold.',
    factsPills: ['500L vessel', '80°C', 'Boiler-exempt'],
    icon: Building2,
  },
];

export const PersonaSelector: React.FC = () => {
  const { loadPersona, activePersonaId, isLoading } = useAssessment();

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink-900">Try a sample business</h3>
        <span className="text-xs text-slate-500">Loads example details instantly</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {PERSONAS.map((p) => {
          const Icon = p.icon;
          const isActive = activePersonaId === p.id;

          return (
            <button
              key={p.id}
              type="button"
              disabled={isLoading}
              onClick={() => loadPersona(p.id)}
              className={`text-left p-4 rounded-xl border transition group disabled:opacity-50 ${
                isActive
                  ? 'bg-brand-tint border-brand'
                  : 'bg-white border-slate-200 hover:border-brand hover:shadow-card'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? 'bg-brand text-white' : 'bg-slate-100 text-slate-500 group-hover:bg-brand-tint group-hover:text-brand'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                {isLoading && isActive ? (
                  <span className="text-xs text-brand font-medium">Loading…</span>
                ) : (
                  <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-brand transition" />
                )}
              </div>
              <div className="text-sm font-semibold text-ink-900">{p.name}</div>
              <div className="text-xs text-slate-500 mt-0.5">{p.tagline}</div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {p.factsPills.map((pill, i) => (
                  <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                    {pill}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
