import React from 'react';
import {
  FileCheck2,
  ArrowLeft,
  ArrowRight,
  Edit2,
  Calendar,
  Sparkles,
  RefreshCw,
  Landmark,
} from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Breadcrumb } from '../components/common/Breadcrumb';
import { ConstraintAlert } from '../components/intake/ConstraintAlert';

export const ReviewFactsPage: React.FC = () => {
  const { facts, asOfDate, setAsOfDate, goToStep, runEvaluation, isLoading } = useAssessment();

  const handleSubmit = async () => {
    await runEvaluation();
  };

  return (
    <div>
      <Breadcrumb
        items={[
          { label: 'Intake Assessment', step: 1 },
          { label: 'Review Declared Profile' },
        ]}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-gov-navy flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-gov-navyLight" />
              Pre-Assessment Profile Verification
            </h2>
            <p className="text-xs text-slate-600">
              Verify all declared enterprise attributes before executing the deterministic regulatory reasoning engine.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded border border-slate-300 text-xs">
            <Calendar className="w-4 h-4 text-gov-navy" />
            <label className="font-bold text-slate-700">Evaluation Date:</label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="text-xs font-mono font-medium border-0 focus:ring-0 p-0 text-gov-navy cursor-pointer"
            />
          </div>
        </div>

        {/* Live Constraint Guard */}
        <ConstraintAlert facts={facts} />

        {/* Facts Summary Tables */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Section 1: Business */}
          <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                1. Enterprise Legal Profile
              </h3>
              <button
                onClick={() => goToStep(1)}
                className="text-[11px] text-gov-navy hover:underline flex items-center gap-1 font-semibold"
              >
                <Edit2 className="w-3 h-3" /> Edit
              </button>
            </div>
            <dl className="text-xs divide-y divide-slate-100">
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Unit Name:</dt>
                <dd className="font-semibold text-slate-800">{facts._name || facts.entity_name || 'Not Declared'}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Stage:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.stage}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Legal Constitution:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.entity_type}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Plant & Machinery Investment:</dt>
                <dd className="font-mono font-bold text-gov-navy">
                  {facts.investment_plant_machinery !== null && facts.investment_plant_machinery !== undefined
                    ? `₹${Number(facts.investment_plant_machinery).toLocaleString('en-IN')}`
                    : '<MISSING>'}
                </dd>
              </div>
            </dl>
          </div>

          {/* Section 2: Location */}
          <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                2. Location & Planning
              </h3>
              <button
                onClick={() => goToStep(2)}
                className="text-[11px] text-gov-navy hover:underline flex items-center gap-1 font-semibold"
              >
                <Edit2 className="w-3 h-3" /> Edit
              </button>
            </div>
            <dl className="text-xs divide-y divide-slate-100">
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Planning Authority:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.location_authority}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Land Classification:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.land_classification}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Built-up Area:</dt>
                <dd className="font-mono font-semibold text-slate-800">
                  {facts.builtup_area_sqm ? `${facts.builtup_area_sqm} sq.m` : 'Unspecified'}
                </dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Estate / Cluster:</dt>
                <dd className="font-semibold text-slate-800">{facts.midc_estate || 'N/A'}</dd>
              </div>
            </dl>
          </div>

          {/* Section 3: Operations */}
          <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                3. Operations & Workforce
              </h3>
              <button
                onClick={() => goToStep(3)}
                className="text-[11px] text-gov-navy hover:underline flex items-center gap-1 font-semibold"
              >
                <Edit2 className="w-3 h-3" /> Edit
              </button>
            </div>
            <dl className="text-xs divide-y divide-slate-100">
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Annual Turnover:</dt>
                <dd className="font-mono font-bold text-gov-navy">
                  {facts.annual_turnover !== null && facts.annual_turnover !== undefined
                    ? `₹${Number(facts.annual_turnover).toLocaleString('en-IN')}`
                    : '<MISSING>'}
                </dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Total Workforce / Factory Workers:</dt>
                <dd className="font-mono font-semibold text-slate-800">
                  {facts.employees_total ?? 0} employees / {facts.workers_for_threshold ?? 0} workers
                </dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Contract Labourers:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.contract_labourers ?? 0}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Food Handlers:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.food_handlers ?? 0}</dd>
              </div>
            </dl>
          </div>

          {/* Section 4: Equipment */}
          <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gov-navy">
                4. Equipment & Utilities
              </h3>
              <button
                onClick={() => goToStep(4)}
                className="text-[11px] text-gov-navy hover:underline flex items-center gap-1 font-semibold"
              >
                <Edit2 className="w-3 h-3" /> Edit
              </button>
            </div>
            <dl className="text-xs divide-y divide-slate-100">
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Electrical Power Usage:</dt>
                <dd className="font-semibold text-slate-800">{facts.uses_power ? 'Yes (Power-operated)' : 'No Power'}</dd>
              </div>
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">Boiler Operated:</dt>
                <dd className="font-semibold text-slate-800">{facts.boiler_operates ? 'Yes' : 'No Boiler'}</dd>
              </div>
              {facts.boiler_operates && (
                <>
                  <div className="py-1.5 flex justify-between">
                    <dt className="text-slate-500">Boiler Specs (Cap / Press / Temp):</dt>
                    <dd className="font-mono font-bold text-gov-navy">
                      {facts.boiler_capacity_litres}L &bull; {facts.boiler_pressure_kg_cm2} kg/cm&sup2; &bull; {facts.boiler_water_temp_c}&deg;C
                    </dd>
                  </div>
                </>
              )}
              <div className="py-1.5 flex justify-between">
                <dt className="text-slate-500">MPCB Category:</dt>
                <dd className="font-mono font-semibold text-slate-800">{facts.mpcb_category || 'Unspecified (UNKNOWN)'}</dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Submit Execution Card */}
        <div className="bg-gov-navy text-white p-6 rounded-lg shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-gov-gold" />
              Execute Deterministic Regulatory Derivation
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Dispatches the fact vector to the backend <code>/api/evaluate</code> endpoint. Resolves requirements, exclusions, quantities, and statutory citations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => goToStep(4)}
              className="px-4 py-2 rounded text-xs font-semibold text-slate-300 bg-gov-navyLight/60 hover:bg-gov-navyLight border border-slate-600 transition"
            >
              <ArrowLeft className="w-4 h-4 inline mr-1" />
              Back
            </button>

            <button
              type="button"
              disabled={isLoading}
              onClick={handleSubmit}
              className="px-6 py-2.5 rounded text-xs font-bold text-gov-navy bg-gov-gold hover:bg-gov-goldLight transition shadow flex items-center gap-2 uppercase tracking-wider disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Deriving Requirements...
                </>
              ) : (
                <>
                  Run Assessment
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
