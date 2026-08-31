import React from 'react';
import { Flame, Zap, Gauge } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Step4Equipment: React.FC<{ invalidFields?: string[] }> = ({ invalidFields = [] }) => {
  const { facts, setFact } = useAssessment();
  const isInvalid = (field: string) => invalidFields.includes(field);
  const errClass = (field: string) => (isInvalid(field) ? 'border-red-400 ring-2 ring-red-100' : '');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-brand-tint flex items-center justify-center">
          <Flame className="w-4 h-4 text-brand" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-ink-900">Equipment & utilities</h3>
          <p className="text-sm text-slate-500">Boilers of 25L / 1 kg/cm² / 100°C or above need registration.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
          <input
            type="checkbox"
            checked={facts.uses_power ?? true}
            onChange={(e) => setFact('uses_power', e.target.checked)}
            className="mt-0.5 rounded border-slate-300 text-brand focus:ring-brand w-4 h-4"
          />
          <div>
            <span className="text-sm font-medium text-ink-900 block flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              We use electrical power
            </span>
            <span className="text-xs text-slate-500">Sets the factory-licence worker threshold to 20 (vs. 40 without power).</span>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
          <input
            type="checkbox"
            checked={facts.boiler_operates ?? false}
            onChange={(e) => {
              const checked = e.target.checked;
              setFact('boiler_operates', checked);
              if (!checked) {
                setFact('boiler_capacity_litres', null);
                setFact('boiler_pressure_kg_cm2', null);
                setFact('boiler_water_temp_c', null);
              } else if (facts.boiler_capacity_litres === null) {
                setFact('boiler_capacity_litres', 500);
                setFact('boiler_pressure_kg_cm2', 7);
                setFact('boiler_water_temp_c', 170);
              }
            }}
            className="mt-0.5 rounded border-slate-300 text-brand focus:ring-brand w-4 h-4"
          />
          <div>
            <span className="text-sm font-medium text-ink-900 block flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-brand" />
              We run a steam boiler
            </span>
            <span className="text-xs text-slate-500">For blanching, pasteurising, sterilising, or process heating.</span>
          </div>
        </label>
      </div>

      {facts.boiler_operates && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-4">
          <h4 className="text-sm font-medium text-amber-900">Boiler details</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="field-label">Capacity (litres) <span className="text-red-500">*</span></label>
              <input
                id="boiler-capacity-litres"
                data-field-label="Volumetric Capacity"
                type="number"
                required
                value={facts.boiler_capacity_litres ?? ''}
                onChange={(e) => setFact('boiler_capacity_litres', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="e.g. 500"
                className={`field-input ${errClass('boiler_capacity_litres')}`}
              />
              <p className="field-help">Threshold: 25L</p>
            </div>
            <div>
              <label className="field-label">Pressure (kg/cm²) <span className="text-red-500">*</span></label>
              <input
                id="boiler-pressure"
                data-field-label="Operating Steam Pressure"
                type="number"
                step="0.1"
                required
                value={facts.boiler_pressure_kg_cm2 ?? ''}
                onChange={(e) => setFact('boiler_pressure_kg_cm2', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="e.g. 7"
                className={`field-input ${errClass('boiler_pressure_kg_cm2')}`}
              />
              <p className="field-help">Threshold: 1.0 kg/cm²</p>
            </div>
            <div>
              <label className="field-label">Water temperature (°C) <span className="text-red-500">*</span></label>
              <input
                id="boiler-water-temperature"
                data-field-label="Working Water Temperature"
                type="number"
                required
                value={facts.boiler_water_temp_c ?? ''}
                onChange={(e) => setFact('boiler_water_temp_c', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="e.g. 170"
                className={`field-input ${errClass('boiler_water_temp_c')}`}
              />
              <p className="field-help">Below 100°C = hot-water generator (exempt)</p>
            </div>
          </div>
        </div>
      )}

      <div>
        <label className="field-label">Pollution category (if known)</label>
        <select
          value={facts.mpcb_category ?? ''}
          onChange={(e) => setFact('mpcb_category', e.target.value === '' ? null : e.target.value)}
          className="field-input"
        >
          <option value="">Not sure — leave blank</option>
          <option value="Orange">Orange (typical for food processing)</option>
          <option value="Red">Red (heavy discharge / large effluent)</option>
          <option value="Green">Green (low pollution, small unit)</option>
          <option value="White">White (non-polluting)</option>
        </select>
        <p className="field-help">Leaving this blank is fine — we'll flag it as something to confirm rather than guess.</p>
      </div>
    </div>
  );
};
