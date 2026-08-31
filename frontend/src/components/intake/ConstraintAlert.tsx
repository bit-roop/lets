import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import { ApplicantFacts } from '../../types/facts';

export const ConstraintAlert: React.FC<{ facts: ApplicantFacts }> = ({ facts }) => {
  const issues: { type: 'error' | 'warning' | 'info'; title: string; message: string; fix?: string }[] = [];

  if (facts.location_authority === 'MIDC' && facts.land_classification === 'agricultural') {
    issues.push({
      type: 'error',
      title: "That combination doesn't match",
      message: 'MIDC plots are already-notified industrial land — they can\'t also be agricultural.',
      fix: 'Change the land type to "MIDC industrial plot", or change the location authority.',
    });
  }

  if (facts.location_authority === 'Municipal_Corporation' && facts.land_classification === 'midc_industrial') {
    issues.push({
      type: 'error',
      title: "That combination doesn't match",
      message: 'MIDC industrial land is governed by MIDC, not the Municipal Corporation.',
      fix: 'Set location authority to "MIDC", or pick a non-agricultural municipal plot.',
    });
  }

  if (
    facts.workers_for_threshold !== null &&
    facts.employees_total !== null &&
    facts.workers_for_threshold !== undefined &&
    facts.employees_total !== undefined &&
    Number(facts.workers_for_threshold) < Number(facts.employees_total) - 20
  ) {
    issues.push({
      type: 'warning',
      title: 'Double-check your worker count',
      message: 'For factory licensing, "workers" usually includes contract staff and machine operators too — not just permanent employees.',
    });
  }

  if (
    facts.boiler_operates &&
    facts.boiler_water_temp_c !== null &&
    facts.boiler_water_temp_c !== undefined &&
    Number(facts.boiler_water_temp_c) < 100
  ) {
    issues.push({
      type: 'info',
      title: 'Good news — this looks exempt',
      message: 'Vessels heating water below 100°C count as hot-water generators, not boilers, so boiler registration isn\'t required.',
    });
  }

  if (issues.length === 0) return null;

  return (
    <div className="space-y-2.5 mb-6">
      {issues.map((issue, idx) => {
        const isErr = issue.type === 'error';
        const isWarn = issue.type === 'warning';
        const styles = isErr
          ? { bg: 'bg-red-50 border-red-200', text: 'text-red-800', icon: 'text-red-500' }
          : isWarn
          ? { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-800', icon: 'text-amber-500' }
          : { bg: 'bg-brand-tint border-brand-border', text: 'text-brand-darker', icon: 'text-brand' };
        const Icon = isErr || isWarn ? AlertTriangle : Info;

        return (
          <div key={idx} className={`flex items-start gap-3 rounded-xl border p-3.5 ${styles.bg}`}>
            <Icon className={`w-4.5 h-4.5 shrink-0 mt-0.5 ${styles.icon}`} />
            <div className="text-sm">
              <div className={`font-medium ${styles.text}`}>{issue.title}</div>
              <div className={`${styles.text} opacity-90 mt-0.5`}>{issue.message}</div>
              {issue.fix && (
                <div className="mt-1.5 text-xs font-medium text-ink-700 bg-white/70 px-2 py-1 rounded-lg inline-block">
                  {issue.fix}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
