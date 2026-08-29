import React from 'react';
import { Building, IndianRupee, Layers, Briefcase } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Step1Business: React.FC = () => {
  const { facts, setFact } = useAssessment();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold text-gov-navy uppercase tracking-wider mb-1 flex items-center gap-2">
          <Building className="w-4 h-4 text-gov-navyLight" />
          Section 1: Enterprise Profile & Legal Constitution
        </h3>
        <p className="text-xs text-slate-600">
          Declare the legal form and initial project stage. This establishes the statutory jurisdiction (Companies Act / Partnership Act) and baseline MSME thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Entity Name */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Enterprise / Unit Legal Name <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            value={facts._name || facts.entity_name || ''}
            onChange={(e) => {
              setFact('_name', e.target.value);
              setFact('entity_name', e.target.value);
            }}
            placeholder="e.g. Sahyadri Foods Private Limited"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Used as the applicant entity identifier across certificates and licenses.
          </span>
        </div>

        {/* Project Stage */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Project Lifecycle Stage <span className="text-rose-500">*</span>
          </label>
          <select
            value={facts.stage || 'new_setup'}
            onChange={(e) => setFact('stage', e.target.value)}
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          >
            <option value="new_setup">New Greenfield Industrial Setup</option>
            <option value="expansion">Brownfield Expansion / Capacity Addition</option>
            <option value="renewal">Periodic Licence & Consent Renewal</option>
          </select>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Determines whether prior clearances (CTE, building permissions) are required.
          </span>
        </div>

        {/* Legal Constitution */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Legal Form of Entity <span className="text-rose-500">*</span>
          </label>
          <select
            value={facts.entity_type || 'private_limited'}
            onChange={(e) => setFact('entity_type', e.target.value)}
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          >
            <option value="private_limited">Private Limited Company (MCA Incorporated)</option>
            <option value="proprietorship">Sole Proprietorship</option>
            <option value="partnership">Registered Partnership Firm</option>
            <option value="llp">Limited Liability Partnership (LLP)</option>
            <option value="public_limited">Public Limited Company</option>
          </select>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Drives entity-level registration paths and board resolution requirements.
          </span>
        </div>

        {/* Plant & Machinery Investment */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Investment in Plant & Machinery (INR ₹) <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
              ₹
            </div>
            <input
              type="number"
              value={facts.investment_plant_machinery ?? ''}
              onChange={(e) => {
                const v = e.target.value === '' ? null : Number(e.target.value);
                setFact('investment_plant_machinery', v);
              }}
              placeholder="e.g. 60000000 (for ₹6.00 Crores)"
              className="w-full text-xs pl-7 pr-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
            />
          </div>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Evaluated for Udyam MSME classification (Notification S.O. 1364(E)). Ceiling: ₹125 Cr.
          </span>
        </div>
      </div>
    </div>
  );
};
