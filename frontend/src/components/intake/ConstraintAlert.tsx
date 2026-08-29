import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import { ApplicantFacts } from '../../types/facts';

export const ConstraintAlert: React.FC<{ facts: ApplicantFacts }> = ({ facts }) => {
  const issues: { type: 'error' | 'warning' | 'info'; title: string; message: string; fix?: string }[] = [];

  // Contradiction 1: MIDC vs Municipal Corporation planning
  if (facts.location_authority === 'MIDC' && facts.land_classification === 'agricultural') {
    issues.push({
      type: 'error',
      title: 'Planning Authority & Zoning Inconsistency',
      message: 'MIDC estates are notified industrial areas. An MIDC plot cannot be classified as agricultural.',
      fix: 'Select "MIDC Industrial Land" or change Planning Authority to Local Collector / Grampanchayat.',
    });
  }

  // Contradiction 2: Municipal Authority vs MIDC Industrial land
  if (facts.location_authority === 'Municipal_Corporation' && facts.land_classification === 'midc_industrial') {
    issues.push({
      type: 'error',
      title: 'Planning Authority & Jurisdiction Conflict',
      message: 'MIDC industrial land falls under MIDC planning jurisdiction under the MID Act 1961, not the Municipal Corporation.',
      fix: 'Set Location Authority to "MIDC" or select Non-Agricultural municipal land.',
    });
  }

  // Contradiction 3: Headcount inconsistency
  if (
    facts.workers_for_threshold !== null &&
    facts.employees_total !== null &&
    facts.workers_for_threshold !== undefined &&
    facts.employees_total !== undefined &&
    Number(facts.workers_for_threshold) < Number(facts.employees_total) - 20
  ) {
    issues.push({
      type: 'warning',
      title: 'Headcount Definition Notice',
      message: 'Under the Maharashtra Factories Rules, total workers for factory licensing includes contract workers and plant operators.',
    });
  }

  // Informational: Boiler Hot Water Generator nuance
  if (
    facts.boiler_operates &&
    facts.boiler_water_temp_c !== null &&
    facts.boiler_water_temp_c !== undefined &&
    Number(facts.boiler_water_temp_c) < 100
  ) {
    issues.push({
      type: 'info',
      title: 'Hot Water Generator Statutory Exemption (s.2(b))',
      message: 'Vessels heating water below 100°C are classified as Hot Water Generators under the Boilers Act 1923 and are exempt from boiler registration.',
    });
  }

  if (issues.length === 0) return null;

  return (
    <div className="space-y-3 mb-6">
      {issues.map((issue, idx) => {
        const isErr = issue.type === 'error';
        const isWarn = issue.type === 'warning';
        const bg = isErr ? 'bg-rose-50 border-rose-500' : isWarn ? 'bg-amber-50 border-amber-500' : 'bg-blue-50 border-blue-500';
        const textColor = isErr ? 'text-rose-900' : isWarn ? 'text-amber-900' : 'text-blue-900';
        const icon = isErr || isWarn ? (
          <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${isErr ? 'text-rose-600' : 'text-amber-600'}`} />
        ) : (
          <Info className="w-5 h-5 shrink-0 mt-0.5 text-blue-600" />
        );

        return (
          <div key={idx} className={`border-l-4 p-3.5 rounded-r shadow-xs ${bg}`}>
            <div className="flex items-start gap-3">
              {icon}
              <div className="text-xs">
                <div className={`font-bold ${textColor}`}>{issue.title}</div>
                <div className={`${textColor} mt-0.5 opacity-90`}>{issue.message}</div>
                {issue.fix && (
                  <div className="mt-1 text-[11px] font-semibold text-slate-700 bg-white/70 px-2 py-0.5 rounded border border-slate-300 inline-block">
                    Recommended Correction: {issue.fix}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
