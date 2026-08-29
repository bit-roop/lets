import React from 'react';
import { Utensils, Users, TrendingUp, Globe2, AlertCircle } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Step3Operations: React.FC = () => {
  const { facts, setFact } = useAssessment();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold text-gov-navy uppercase tracking-wider mb-1 flex items-center gap-2">
          <Utensils className="w-4 h-4 text-gov-navyLight" />
          Section 3: Operations, Turnover & Workforce Structure
        </h3>
        <p className="text-xs text-slate-600">
          Declare operational scale, projected turnover, and employee staffing. These facts determine FSSAI licensing tier (Registration vs State vs Central), Factory Act coverage (20/40 rule), and labour welfare registrations.
        </p>
      </div>

      <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-md mb-2">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={facts.is_food_business ?? true}
            onChange={(e) => setFact('is_food_business', e.target.checked)}
            className="mt-0.5 rounded border-slate-300 text-gov-navy focus:ring-gov-navy w-4 h-4"
          />
          <div>
            <span className="text-xs font-bold text-gov-navy block">
              Food Business Operator (FBO) Confirmation <span className="text-rose-500">*</span>
            </span>
            <span className="text-[11px] text-slate-600">
              Unit engages in manufacturing, processing, packaging, storage, or distribution of food or beverage articles.
            </span>
          </div>
        </label>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Annual Turnover */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Annual Projected Turnover (INR ₹) <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
              ₹
            </div>
            <input
              type="number"
              value={facts.annual_turnover ?? ''}
              onChange={(e) => {
                const v = e.target.value === '' ? null : Number(e.target.value);
                setFact('annual_turnover', v);
              }}
              placeholder="e.g. 80000000 (for ₹8.00 Crores)"
              className="w-full text-xs pl-7 pr-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
            />
          </div>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            <strong>FSSAI 2026 Slabs:</strong> &le; ₹1.5 Cr: Registration | ₹1.5 Cr &ndash; ₹50 Cr: State Licence | &gt; ₹50 Cr: Central Licence.
          </span>
        </div>

        {/* Total Employees */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Total Headcount on Premises <span className="text-rose-500">*</span>
          </label>
          <input
            type="number"
            value={facts.employees_total ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : Number(e.target.value);
              setFact('employees_total', v);
            }}
            placeholder="e.g. 45"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Triggers POSH Internal Committee (&ge; 10) and EPFO registration (&ge; 20 employees).
          </span>
        </div>

        {/* Factory Workers */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Total Manufacturing / Floor Workers <span className="text-rose-500">*</span>
          </label>
          <input
            type="number"
            value={facts.workers_for_threshold ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : Number(e.target.value);
              setFact('workers_for_threshold', v);
            }}
            placeholder="e.g. 67"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            <strong>Maharashtra Factories Act Threshold:</strong> &ge; 20 workers with power / &ge; 40 without power.
          </span>
        </div>

        {/* Contract Labourers */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Contract Labourers Engaged
          </label>
          <input
            type="number"
            value={facts.contract_labourers ?? 0}
            onChange={(e) => {
              const v = e.target.value === '' ? 0 : Number(e.target.value);
              setFact('contract_labourers', v);
            }}
            placeholder="e.g. 22"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Contract Labour (R&A) Act registration required if &ge; 20 contract workers.
          </span>
        </div>

        {/* Food Handlers */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Active Food Handlers
          </label>
          <input
            type="number"
            value={facts.food_handlers ?? 0}
            onChange={(e) => {
              const v = e.target.value === '' ? 0 : Number(e.target.value);
              setFact('food_handlers', v);
            }}
            placeholder="e.g. 30"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            FSSAI FoSTaC ratio formula: <code>ceil(food_handlers / 25)</code> trained supervisors.
          </span>
        </div>

        {/* Trade Attributes */}
        <div className="flex flex-col justify-center space-y-3 pt-2">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={facts.export ?? false}
              onChange={(e) => setFact('export', e.target.checked)}
              className="rounded border-slate-300 text-gov-navy focus:ring-gov-navy w-4 h-4"
            />
            <span className="text-xs font-semibold text-slate-700">
              100% Export-Oriented / Direct Food Exporting (Triggers Central Licence)
            </span>
          </label>

          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={facts.multi_state_operation ?? false}
              onChange={(e) => setFact('multi_state_operation', e.target.checked)}
              className="rounded border-slate-300 text-gov-navy focus:ring-gov-navy w-4 h-4"
            />
            <span className="text-xs font-semibold text-slate-700">
              Multi-State Headquartered Unit (Triggers Central Licence)
            </span>
          </label>
        </div>
      </div>
    </div>
  );
};
