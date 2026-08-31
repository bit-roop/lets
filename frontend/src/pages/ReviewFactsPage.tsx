import React from 'react';
import { ArrowLeft, ArrowRight, Pencil, Calendar, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { ConstraintAlert } from '../components/intake/ConstraintAlert';
import { getAllErrors, STEP_TITLES } from '../utils/validation';

const Row: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="flex justify-between py-2 text-sm">
    <span className="text-slate-500">{label}</span>
    <span className="font-medium text-ink-900 text-right">{value}</span>
  </div>
);

const Section: React.FC<{ title: string; step: number; onEdit: (s: number) => void; children: React.ReactNode }> = ({
  title,
  step,
  onEdit,
  children,
}) => (
  <div className="bg-white rounded-2xl border border-slate-200 p-5">
    <div className="flex items-center justify-between pb-2.5 mb-1 border-b border-slate-100">
      <h3 className="text-sm font-semibold text-ink-900">{title}</h3>
      <button onClick={() => onEdit(step)} className="text-xs text-brand hover:underline flex items-center gap-1 font-medium">
        <Pencil className="w-3 h-3" /> Edit
      </button>
    </div>
    <dl className="divide-y divide-slate-50">{children}</dl>
  </div>
);

export const ReviewFactsPage: React.FC = () => {
  const { facts, asOfDate, setAsOfDate, goToStep, runEvaluation, isLoading } = useAssessment();
  const allErrors = getAllErrors(facts);
  const hasErrors = allErrors.length > 0;

  return (
    <div>
      <Breadcrumb items={[{ label: 'Compliance check', step: 1 }, { label: 'Review' }]} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink-900">Review your answers</h2>
            <p className="text-sm text-slate-500">Make sure everything below is correct before we check the rules.</p>
          </div>
          <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-xl border border-slate-200 text-sm">
            <Calendar className="w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="text-sm font-medium border-0 focus:ring-0 p-0 text-ink-900 bg-transparent cursor-pointer"
            />
          </div>
        </div>

        <ConstraintAlert facts={facts} />

        {hasErrors && (
          <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-xl p-3.5 text-sm text-red-700">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="space-y-1">
              <div className="font-medium">A few required details are still missing:</div>
              {allErrors.map(({ step, errors }) => (
                <div key={step}>
                  <button onClick={() => goToStep(step)} className="underline font-medium">
                    {STEP_TITLES[step]}
                  </button>
                  {': '}
                  {errors.map((e) => e.label).join(', ')}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Business" step={1} onEdit={goToStep}>
            <Row label="Name" value={facts._name || facts.entity_name || 'Not entered'} />
            <Row label="Stage" value={facts.stage} />
            <Row label="Structure" value={facts.entity_type} />
            <Row
              label="Investment"
              value={
                facts.investment_plant_machinery != null
                  ? `₹${Number(facts.investment_plant_machinery).toLocaleString('en-IN')}`
                  : 'Not entered'
              }
            />
          </Section>

          <Section title="Location" step={2} onEdit={goToStep}>
            <Row label="Authority" value={facts.location_authority} />
            <Row label="Land type" value={facts.land_classification} />
            <Row label="Built-up area" value={facts.builtup_area_sqm ? `${facts.builtup_area_sqm} sq.m` : 'Not entered'} />
            <Row label="Estate" value={facts.midc_estate || 'Not entered'} />
          </Section>

          <Section title="Operations" step={3} onEdit={goToStep}>
            <Row
              label="Turnover"
              value={facts.annual_turnover != null ? `₹${Number(facts.annual_turnover).toLocaleString('en-IN')}` : 'Not entered'}
            />
            <Row label="Employees / workers" value={`${facts.employees_total ?? 0} / ${facts.workers_for_threshold ?? 0}`} />
            <Row label="Contract labour" value={facts.contract_labourers ?? 0} />
            <Row label="Food handlers" value={facts.food_handlers ?? 0} />
          </Section>

          <Section title="Equipment" step={4} onEdit={goToStep}>
            <Row label="Uses power" value={facts.uses_power ? 'Yes' : 'No'} />
            <Row label="Boiler" value={facts.boiler_operates ? 'Yes' : 'No'} />
            {facts.boiler_operates && (
              <Row
                label="Boiler specs"
                value={`${facts.boiler_capacity_litres}L · ${facts.boiler_pressure_kg_cm2}kg/cm² · ${facts.boiler_water_temp_c}°C`}
              />
            )}
            <Row label="Pollution category" value={facts.mpcb_category || 'Not specified'} />
          </Section>
        </div>

        <div className="bg-brand rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              {hasErrors ? 'Almost there' : 'Ready to check'}
            </h3>
            <p className="text-sm text-white/80 mt-0.5">
              {hasErrors ? 'Fill in the missing details above to continue.' : "We'll match these details against every applicable rule."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => goToStep(4)}
              className="px-4 py-2.5 rounded-full text-sm font-medium text-white/90 hover:bg-white/10 transition"
            >
              <ArrowLeft className="w-4 h-4 inline mr-1" />
              Back
            </button>
            <button
              disabled={isLoading || hasErrors}
              onClick={() => runEvaluation()}
              className="px-6 py-2.5 rounded-full text-sm font-semibold text-brand-dark bg-white hover:bg-slate-50 transition shadow-card flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Checking…
                </>
              ) : (
                <>
                  Run check
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
