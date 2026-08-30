import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, ApiError } from '../api/client';
import { EvaluationResponse, HealthResponse } from '../types/engine';
import { ApplicantFacts } from '../types/facts';

export const INITIAL_FACTS: ApplicantFacts = {
  stage: 'new_setup',
  entity_type: 'private_limited',
  entity_name: '',
  location_authority: 'MIDC',
  land_classification: 'midc_industrial',
  builtup_area_sqm: null,
  is_food_business: true,
  annual_turnover: null,
  investment_plant_machinery: null,
  employees_total: null,
  workers_for_threshold: null,
  uses_power: true,
  contract_labourers: 0,
  food_handlers: 0,
  boiler_operates: false,
  boiler_capacity_litres: null,
  boiler_pressure_kg_cm2: null,
  boiler_water_temp_c: null,
  export: false,
  multi_state_operation: false,
  mpcb_category: null,
  in_esic_implemented_area: null,
  notified_industry_category: [],
};

interface AssessmentContextType {
  facts: ApplicantFacts;
  asOfDate: string;
  activePersonaId: string | null;
  activeApplicationId: string | null;
  currentStep: number;
  evaluationResult: EvaluationResponse | null;
  isLoading: boolean;
  error: string | null;
  health: HealthResponse | null;
  catalogue: Record<string, any>;
  sources: Record<string, any>;
  setFact: (key: string, value: any) => void;
  setFacts: (facts: Partial<ApplicantFacts>) => void;
  setAsOfDate: (date: string) => void;
  setActiveApplicationId: (id: string | null) => void;
  loadPersona: (personaId: string) => Promise<void>;
  runEvaluation: (customFacts?: ApplicantFacts) => Promise<EvaluationResponse | null>;
  resetAssessment: () => void;
  goToStep: (step: number) => void;
  clearError: () => void;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export const AssessmentProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [facts, setFactsState] = useState<ApplicantFacts>(INITIAL_FACTS);
  const [asOfDate, setAsOfDate] = useState<string>('2026-08-29');
  const [activePersonaId, setActivePersonaId] = useState<string | null>(null);
  const [activeApplicationId, setActiveApplicationId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0); // 0: Home, 1: Step 1, 2: Step 2, 3: Step 3, 4: Step 4, 5: Review, 6: Results, 7: Dashboard
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [catalogue, setCatalogue] = useState<Record<string, any>>({});
  const [sources, setSources] = useState<Record<string, any>>({});

  useEffect(() => {
    // Initial system discovery load
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.warn('Could not load health info:', err.message));

    api.getCatalogue()
      .then(setCatalogue)
      .catch((err) => console.warn('Could not load catalogue:', err.message));

    api.getSources()
      .then(setSources)
      .catch((err) => console.warn('Could not load sources:', err.message));
  }, []);

  const setFact = (key: string, value: any) => {
    setFactsState((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const setFacts = (newFacts: Partial<ApplicantFacts>) => {
    setFactsState((prev) => ({
      ...prev,
      ...newFacts,
    }));
  };

  const loadPersona = async (personaId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const personaFacts = await api.getPersonaById(personaId);
      setFactsState(personaFacts);
      setActivePersonaId(personaId);
      // Auto-evaluate loaded persona
      const result = await api.evaluate(personaFacts, asOfDate);
      setEvaluationResult(result);
      setCurrentStep(6); // Jump straight to results
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : 'Failed to load persona.');
    } finally {
      setIsLoading(false);
    }
  };

  const runEvaluation = async (customFacts?: ApplicantFacts): Promise<EvaluationResponse | null> => {
    setIsLoading(true);
    setError(null);
    const factsToEvaluate = customFacts || facts;
    try {
      const result = await api.evaluate(factsToEvaluate, asOfDate);
      setEvaluationResult(result);
      setCurrentStep(6);
      return result;
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : 'Evaluation failed. Please check backend connectivity.');
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const resetAssessment = () => {
    setFactsState(INITIAL_FACTS);
    setActivePersonaId(null);
    setActiveApplicationId(null);
    setEvaluationResult(null);
    setError(null);
    setCurrentStep(0);
  };

  const goToStep = (step: number) => {
    setError(null);
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const clearError = () => setError(null);

  return (
    <AssessmentContext.Provider
      value={{
        facts,
        asOfDate,
        activePersonaId,
        activeApplicationId,
        currentStep,
        evaluationResult,
        isLoading,
        error,
        health,
        catalogue,
        sources,
        setFact,
        setFacts,
        setAsOfDate,
        setActiveApplicationId,
        loadPersona,
        runEvaluation,
        resetAssessment,
        goToStep,
        clearError,
      }}
    >
      {children}
    </AssessmentContext.Provider>
  );
};

export const useAssessment = (): AssessmentContextType => {
  const context = useContext(AssessmentContext);
  if (!context) {
    throw new Error('useAssessment must be used within an AssessmentProvider');
  }
  return context;
};
