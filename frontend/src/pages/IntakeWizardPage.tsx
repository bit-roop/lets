import React from 'react';
import { ArrowLeft, ArrowRight, Check, Building, MapPin, Utensils, Flame, Sparkles } from 'lucide-react';
import { useAssessment } from '../context/AssessmentContext';
import { Step1Business } from '../components/intake/Step1Business';
import { Step2Location } from '../components/intake/Step2Location';
import { Step3Operations } from '../components/intake/Step3Operations';
import { Step4Equipment } from '../components/intake/Step4Equipment';
import { ConstraintAlert } from '../components/intake/ConstraintAlert';
import { Breadcrumb } from '../components/common/Breadcrumb';

const STEPS = [
  { id: 1, title: 'Enterprise Profile', icon: Building },
  { id: 2, title: 'Location & Land', icon: MapPin },
  { id: 3, title: 'Operations & Labour', icon: Utensils },
  { id: 4, title: 'Equipment & Boilers', icon: Flame },
];

export const IntakeWizardPage: React.FC = () => {
  const { currentStep, goToStep, facts } = useAssessment();

  const handleNext = () => {
    if (currentStep < 4) {
      goToStep(currentStep + 1);
    } else {
      goToStep(5); // Proceed to review
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      goToStep(currentStep - 1);
    } else {
      goToStep(0); // Return home
    }
  };

  return (
    <div>
      <Breadcrumb
        items={[
          { label: 'Intake Assessment', step: 1 },
          { label: STEPS[currentStep - 1]?.title || 'Step' },
        ]}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Step Indicator Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between relative">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-slate-200 w-full -z-0"></div>

            {STEPS.map((step) => {
              const isCompleted = currentStep > step.id;
              const isCurrent = currentStep === step.id;
              const Icon = step.icon;

              return (
                <div
                  key={step.id}
                  onClick={() => goToStep(step.id)}
                  className="flex flex-col items-center cursor-pointer relative z-10 group"
                >
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition border-2 ${
                      isCurrent
                        ? 'bg-gov-navy text-white border-gov-gold ring-4 ring-gov-gold/20'
                        : isCompleted
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-white text-slate-500 border-slate-300 group-hover:border-gov-navy'
                    }`}
                  >
                    {isCompleted ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  </div>
                  <span
                    className={`text-[11px] mt-1.5 font-bold uppercase tracking-wider hidden sm:block ${
                      isCurrent ? 'text-gov-navy' : isCompleted ? 'text-emerald-700' : 'text-slate-400'
                    }`}
                  >
                    {step.title}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live Constraint Guard */}
        <ConstraintAlert facts={facts} />

        {/* Wizard Form Card */}
        <div className="bg-white rounded-lg border border-slate-300 shadow-sm p-6 sm:p-8">
          {currentStep === 1 && <Step1Business />}
          {currentStep === 2 && <Step2Location />}
          {currentStep === 3 && <Step3Operations />}
          {currentStep === 4 && <Step4Equipment />}

          {/* Navigation Controls */}
          <div className="mt-8 pt-5 border-t border-slate-200 flex items-center justify-between">
            <button
              type="button"
              onClick={handleBack}
              className="px-4 py-2 rounded text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 transition flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              {currentStep === 1 ? 'Back to Gateway' : 'Previous Section'}
            </button>

            <button
              type="button"
              onClick={handleNext}
              className="px-5 py-2 rounded text-xs font-bold text-white bg-gov-navy hover:bg-gov-navyLight transition shadow flex items-center gap-1.5"
            >
              {currentStep === 4 ? 'Review Declared Profile' : 'Next Section'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
