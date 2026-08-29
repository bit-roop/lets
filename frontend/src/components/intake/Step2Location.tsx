import React from 'react';
import { MapPin, Building2, Ruler } from 'lucide-react';
import { useAssessment } from '../../context/AssessmentContext';

export const Step2Location: React.FC = () => {
  const { facts, setFact } = useAssessment();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold text-gov-navy uppercase tracking-wider mb-1 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-gov-navyLight" />
          Section 2: Site Location, Planning Authority & Land Tenure
        </h3>
        <p className="text-xs text-slate-600">
          Declare the geographical jurisdiction and land classification. Maharashtra establishes distinct planning authorities for MIDC industrial estates versus municipal corporation zones.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Planning Authority */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Planning & Location Authority <span className="text-rose-500">*</span>
          </label>
          <select
            value={facts.location_authority || 'MIDC'}
            onChange={(e) => setFact('location_authority', e.target.value)}
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          >
            <option value="MIDC">MIDC (Maharashtra Industrial Development Corporation)</option>
            <option value="Municipal_Corporation">Municipal Corporation (PMC / PCMC / MCGM / etc.)</option>
            <option value="Grampanchayat">Grampanchayat / PMRDA / Rural Collectorate</option>
          </select>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Controls factory building plan approvals and local trade licensing routes.
          </span>
        </div>

        {/* Land Classification */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Land Classification & Zoning <span className="text-rose-500">*</span>
          </label>
          <select
            value={facts.land_classification || 'midc_industrial'}
            onChange={(e) => setFact('land_classification', e.target.value)}
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          >
            <option value="midc_industrial">MIDC Industrial Allotted Plot</option>
            <option value="non_agricultural">Non-Agricultural (NA Converted) Private Plot</option>
            <option value="agricultural">Agricultural Land (Requires NA Permission)</option>
          </select>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            MIDC allotted land carries deemed-NA conversion status under MLRC amendments.
          </span>
        </div>

        {/* Built-up Area */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Total Factory Built-up Area (Sq. Meters)
          </label>
          <div className="relative">
            <input
              type="number"
              value={facts.builtup_area_sqm ?? ''}
              onChange={(e) => {
                const v = e.target.value === '' ? null : Number(e.target.value);
                setFact('builtup_area_sqm', v);
              }}
              placeholder="e.g. 4200"
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white font-mono"
            />
          </div>
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Total covered floor area across all processing sheds and storage bays.
          </span>
        </div>

        {/* District & Taluka Reference */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">
            Industrial Cluster / Estate Reference
          </label>
          <input
            type="text"
            value={facts.midc_estate || 'MIDC Ranjangaon, Pune'}
            onChange={(e) => setFact('midc_estate', e.target.value)}
            placeholder="e.g. Ranjangaon, Pune / Chakan / Butibori"
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded focus:ring-1 focus:ring-gov-navy focus:border-gov-navy bg-white"
          />
          <span className="text-[10.5px] text-slate-500 mt-1 block">
            Designates the competent regional office for DISH, MPCB, and local health officers.
          </span>
        </div>
      </div>
    </div>
  );
};
