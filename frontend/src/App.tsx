import React from 'react';
import { AssessmentProvider, useAssessment } from './context/AssessmentContext';
import { Header } from './components/common/Header';
import { Footer } from './components/common/Footer';
import { ErrorBanner } from './components/common/ErrorBanner';
import { HomePage } from './pages/HomePage';
import { IntakeWizardPage } from './pages/IntakeWizardPage';
import { ReviewFactsPage } from './pages/ReviewFactsPage';
import { ResultsPage } from './pages/ResultsPage';
import { ApplicantDashboardPage } from './pages/ApplicantDashboardPage';
import { DepartmentPortalPage } from './pages/DepartmentPortalPage';
import { RoadmapPage } from './pages/RoadmapPage';
import { RegulatoryLibraryPage } from './pages/RegulatoryLibraryPage';

const AppContent: React.FC = () => {
  const { currentStep, activeApplicationId } = useAssessment();

  return (
    <div className="flex flex-col min-h-screen bg-gov-canvas text-gov-slate">
      <Header />
      <main className="flex-grow">
        <ErrorBanner />
        {currentStep === 0 && <HomePage />}
        {currentStep >= 1 && currentStep <= 4 && <IntakeWizardPage />}
        {currentStep === 5 && <ReviewFactsPage />}
        {currentStep === 6 && <ResultsPage />}
        {currentStep === 7 && <ApplicantDashboardPage initialApplicationId={activeApplicationId} />}
        {currentStep === 8 && <DepartmentPortalPage />}
        {currentStep === 9 && <RoadmapPage />}
        {currentStep === 10 && <RegulatoryLibraryPage />}
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