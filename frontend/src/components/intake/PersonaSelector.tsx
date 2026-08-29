import React from 'react';
import { UserCheck, Sparkles, Building2, Store, Factory } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

interface PersonaCard {
  id: string;
  badge: string;
  name: string;
  tagline: string;
  description: string;
  factsPills: string[];
  icon: React.ComponentType<{ className?: string }>;
}

const PERSONAS: PersonaCard[] = [
  {
    id: 'persona_a',
    badge: 'Micro Enterprise · Municipal',
    name: 'Persona A: Shree Ganesh Bakery',
    tagline: 'Small Food Processing (Pune Municipal Limits)',
    description: 'Proprietorship with ₹40L turnover, 6 workers, no boiler. Demonstrates basic registration thresholds & non-factory exemption.',
    factsPills: ['₹40L Turnover', '6 Workers', 'No Boiler', 'Municipal Land'],
    icon: Store,
  },
  {
    id: 'persona_b',
    badge: 'Medium Food Plant · MIDC',
    name: 'Persona B: Sahyadri Foods Pvt Ltd',
    tagline: 'Fruit Pulp Processing (MIDC Ranjangaon, Pune)',
    description: 'Pvt Ltd with ₹8 Cr turnover, ₹6 Cr investment, 67 workers, 500L steam boiler at 170°C, 22 contract workers. Canonical demo baseline.',
    factsPills: ['₹8 Cr Turnover', '67 Workers', '500L Steam Boiler', '22 Contract Labour', 'MIDC Estate'],
    icon: Factory,
  },
  {
    id: 'persona_c',
    badge: 'Boiler Edge Case · Statutory Exemption',
    name: 'Persona C: Dairy Chilling Unit',
    tagline: 'Hot Water Generator Unit (80°C Vessel)',
    description: 'Industrial facility with 500L vessel operating at 80°C (<100°C). Demonstrates s.2(b) Hot Water Generator active exclusion.',
    factsPills: ['500L Vessel', '80°C Water Temp', 'HWG Excluded', 'MIDC Estate'],
    icon: Building2,
  },
];

export const PersonaSelector: React.FC = () => {
  const { loadPersona, activePersonaId, isLoading } = useAssessment();

  return (
    <div className="bg-slate-100 border border-slate-300 rounded-md p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-gov-gold" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
            Hackathon Live Evaluation · Preset Personas
          </h3>
        </div>
        <span className="text-[11px] text-slate-500 font-medium">
          Populates authentic fact vectors & triggers live derivation
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PERSONAS.map((p) => {
          const Icon = p.icon;
          const isActive = activePersonaId === p.id;

          return (
            <div
              key={p.id}
              className={`p-3.5 rounded border transition flex flex-col justify-between ${
                isActive
                  ? 'bg-gov-navy text-white border-gov-navy shadow-sm'
                  : 'bg-white text-slate-800 border-slate-300 hover:border-gov-navy hover:shadow-xs'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                      isActive
                        ? 'bg-gov-gold text-gov-navy'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}
                  >
                    {p.badge}
                  </span>
                  <Icon className={`w-4 h-4 ${isActive ? 'text-gov-gold' : 'text-slate-400'}`} />
                </div>

                <h4 className={`text-xs font-bold leading-snug ${isActive ? 'text-white' : 'text-gov-navy'}`}>
                  {p.name}
                </h4>
                <p className={`text-[11px] mt-1 leading-normal ${isActive ? 'text-slate-200' : 'text-slate-600'}`}>
                  {p.description}
                </p>

                <div className="flex flex-wrap gap-1 mt-2.5">
                  {p.factsPills.map((pill, i) => (
                    <span
                      key={i}
                      className={`text-[9.5px] px-1.5 py-0.5 rounded font-mono font-medium ${
                        isActive
                          ? 'bg-gov-navyLight text-slate-200 border border-slate-600'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {pill}
                    </span>
                  ))}
                </div>
              </div>

              <button
                type="button"
                disabled={isLoading}
                onClick={() => loadPersona(p.id)}
                className={`mt-3 w-full py-1.5 px-3 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                  isActive
                    ? 'bg-gov-gold text-gov-navy hover:bg-gov-goldLight font-bold'
                    : 'bg-gov-navy text-white hover:bg-gov-navyLight'
                } disabled:opacity-50`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                {isLoading && isActive ? 'Evaluating...' : `Load & Evaluate ${p.id.replace('persona_', 'Persona ').toUpperCase()}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
