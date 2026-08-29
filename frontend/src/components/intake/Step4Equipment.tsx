import React from 'react';
import { Flame, Zap, Gauge, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Step4Equipment: React.FC = () => {
  const { facts, setFact } = useAssessment();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold text-gov-navy uppercase tracking-wider mb-1 flex items-center gap-2">
          <Flame className="w-4 h-4 text-gov-navyLight" />
          Section 4: Equipment, Boilers, Power & Hazardous Operations
        </h3>
        <p className="text-xs text-slate-600">
          Capture equipment specifications and energy sources. Indian Boiler Regulations (IBR 1950) under the Boilers Act 1923 require registration for steam generation vessels &ge; 25L, &ge; 1 kg/cm&sup2;, and &ge; 100&deg;C.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Electrical Power */}
        <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-md">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={facts.uses_power ?? true}
              onChange={(e) => setFact('uses_power', e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-gov-navy focus:ring-gov-navy w-4 h-4"
            />
            <div>
              <span className="text-xs font-bold text-gov-navy block flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-600" />
                Unit Uses Electrical Power in Manufacturing
              </span>
              <span className="text-[11px] text-slate-600 block mt-0.5">
                Sets the Maharashtra Factories Act threshold to <strong>20 workers</strong> (vs 40 without power).
              </span>
            </div>
          </label>
        </div>

        {/* Boiler Operation Toggle */}
        <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-md">
          <label className="flex items-start gap-3 cursor-pointer">
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
              className="mt-0.5 rounded border-slate-300 text-gov-navy focus:ring-gov-navy w-4 h-4"
            />
            <div>
              <span className="text-xs font-bold text-gov-navy block flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5 text-gov-navyLight" />
                Operates Steam Boiler / Pressure Vessel on Premises
              </span>
              <span className="text-[11px] text-slate-600 block mt-0.5">
                Steam generation for blanching, pasteurisation, sterilization, or process heating.
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* Conditional Boiler Parameters */}
      {facts.boiler_operates && (
        <div className="bg-amber-50/60 border border-amber-200 p-4 rounded-md space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
              <Gauge className="w-4 h-4 text-amber-700" />
              Boiler Technical Specifications (Boilers Act 1923 s.2(b) Composite Criteria)
            </h4>
            <span className="text-[10.5px] text-amber-800 font-semibold bg-white/80 px-2 py-0.5 rounded border border-amber-300">
              Thresholds: &ge; 25L &bull; &ge; 1.0 kg/cm&sup2; &bull; &ge; 100&deg;C
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Volumetric Capacity (Litres) <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                value={facts.boiler_capacity_litres ?? ''}
                onChange={(e) => {
                  const v = e.target.value === '' ? null : Number(e.target.value);
                  setFact('boiler_capacity_litres', v);
                }}
                placeholder="e.g. 500"
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
              />
              <span className="text-[10.5px] text-slate-500 mt-1 block">
                Statutory trigger threshold: &ge; 25 Litres.
              </span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Operating Steam Pressure (kg/cm&sup2;) <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                value={facts.boiler_pressure_kg_cm2 ?? ''}
                onChange={(e) => {
                  const v = e.target.value === '' ? null : Number(e.target.value);
                  setFact('boiler_pressure_kg_cm2', v);
                }}
                placeholder="e.g. 7"
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
              />
              <span className="text-[10.5px] text-slate-500 mt-1 block">
                Statutory trigger threshold: &ge; 1.0 kg/cm&sup2;.
              </span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Working Water Temperature (&deg;C) <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                value={facts.boiler_water_temp_c ?? ''}
                onChange={(e) => {
                  const v = e.target.value === '' ? null : Number(e.target.value);
                  setFact('boiler_water_temp_c', v);
                }}
                placeholder="e.g. 170"
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
              />
              <span className="text-[10.5px] text-slate-500 mt-1 block">
                &lt; 100&deg;C = Hot Water Generator (Actively Excluded).
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Pollution Category Optional Field */}
      <div>
        <label className="block text-xs font-bold text-slate-700 mb-1">
          MPCB Industrial Pollution Category (Optional)
        </label>
        <select
          value={facts.mpcb_category ?? ''}
          onChange={(e) => {
            const v = e.target.value === '' ? null : e.target.value;
            setFact('mpcb_category', v);
          }}
          className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
        >
          <option value="">-- Unspecified (Engine will evaluate Consent to Establish / Operate as UNKNOWN) --</option>
          <option value="Orange">Orange Category (Food processing typical)</option>
          <option value="Red">Red Category (Heavy discharge / large effluent)</option>
          <option value="Green">Green Category (Low pollution small unit / bakery)</option>
          <option value="White">White Category (Non-polluting / intimation only)</option>
        </select>
        <span className="text-[10.5px] text-slate-500 mt-1 block">
          If left unspecified, the engine safely yields <strong>UNKNOWN</strong> with a missing fact prompt, preventing premature consent misclassification.
        </span>
      </div>
    </div>
  );
};
