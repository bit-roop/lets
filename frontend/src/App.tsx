import React from 'react';
import { AssessmentProvider, useAssessment } from './context/AssessmentContext';
import { Header } from './components/common/Header';
import { Footer } from './components/common/Footer';
import { ErrorBanner } from './components/common/ErrorBanner';
import { HomePage } from './pages/HomePage';
import { IntakeWizardPage } from './pages/IntakeWizardPage';
import { ReviewFactsPage } from './pages/ReviewFactsPage';
import { ResultsPage } from './pages/ResultsPage';

const AppContent: React.FC = () => {
  const { currentStep } = useAssessment();

  return (
    <div className="flex flex-col min-h-screen bg-gov-canvas text-gov-slate">
      <Header />
      <main className="flex-grow">
        <ErrorBanner />
        {currentStep === 0 && <HomePage />}
        {currentStep >= 1 && currentStep <= 4 && <IntakeWizardPage />}
        {currentStep === 5 && <ReviewFactsPage />}
        {currentStep === 6 && <ResultsPage />}
      </main>
      <Footer />
    </div>
  );
};

export function App() {
  return (
    <AssessmentProvider>
      <AppContent />
    </AssessmentProvider>
  );
}

export default App;
