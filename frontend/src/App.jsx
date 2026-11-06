import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import StepTracker from './components/StepTracker';
import LoginScreen from './components/LoginScreen';
import ConveningOrderStep from './components/ConveningOrderStep';
import EvidenceAndLawsStep from './components/EvidenceAndLawsStep';
import WitnessStep from './components/WitnessStep';
import PresidingOfficerStep from './components/PresidingOfficerStep';
import CoiDraftStep from './components/CoiDraftStep';
import AllCasesView from './components/AllCasesView';

export default function App() {
  const [user, setUser] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [caseState, setCaseState] = useState(null);

  // Load persisted state on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('coi_user');
    const savedCase = localStorage.getItem('coi_case_state');
    const savedStep = localStorage.getItem('coi_current_step');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
        if (savedCase) setCaseState(JSON.parse(savedCase));
        if (savedStep) setCurrentStep(parseInt(savedStep, 10) || 1);
        // Re-sync with the server on load: the backend is the source of truth,
        // so any server-side fixes (or a case restored after a restart) reach
        // the browser instead of a stale local copy. Offline -> keep local.
        fetch('/api/case/current')
          .then((r) => (r.ok ? r.json() : null))
          .then((srv) => {
            if (srv && srv.case_id) {
              setCaseState(srv);
              localStorage.setItem('coi_case_state', JSON.stringify(srv));
            }
          })
          .catch(() => { /* backend offline: keep the local copy */ });
      } catch (err) {
        console.error('Error loading persisted state:', err);
        localStorage.removeItem('coi_user');
        localStorage.removeItem('coi_case_state');
        localStorage.removeItem('coi_current_step');
      }
    }
  }, []);

  const handleLogin = async (adminUser) => {
    setUser(adminUser);
    // User requirement: "first when i start the dashboard after login everything should be empty"
    try {
      const res = await fetch('/api/case/new', { method: 'POST' });
      if (res.ok) {
        const freshCase = await res.json();
        setCaseState(freshCase);
        // Persist to localStorage
        localStorage.setItem('coi_user', JSON.stringify(adminUser));
        localStorage.setItem('coi_case_state', JSON.stringify(freshCase));
        localStorage.setItem('coi_current_step', '1');
      }
    } catch (err) {
      console.error('Error starting clean case session on login:', err);
    }
    setCurrentStep(1);
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentStep(1);
    setCaseState(null);
    localStorage.removeItem('coi_user');
    localStorage.removeItem('coi_case_state');
    localStorage.removeItem('coi_current_step');
  };

  const handleResetCase = async () => {
    if (window.confirm("Start a new Court of Inquiry? The current session will be safely archived and a clean workspace initialized.")) {
      try {
        const res = await fetch('/api/case/new', { method: 'POST' });
        const freshCase = await res.json();
        setCaseState(freshCase);
        setCurrentStep(1);
        localStorage.setItem('coi_case_state', JSON.stringify(freshCase));
        localStorage.setItem('coi_current_step', '1');
      } catch (err) {
        console.error("Error resetting case:", err);
      }
    }
  };

  const handleSelectCaseFromList = (loadedCase) => {
    setCaseState(loadedCase);
    localStorage.setItem('coi_case_state', JSON.stringify(loadedCase));
    if (loadedCase.coi_draft) {
      setCurrentStep(5);
    } else if (loadedCase.convening_order?.parsed) {
      setCurrentStep(2);
    } else {
      setCurrentStep(1);
    }
    localStorage.setItem('coi_current_step', '1'); // will be updated by the step change below
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNextStep = () => {
    setCurrentStep((prev) => Math.min(prev + 1, 5));
    localStorage.setItem('coi_current_step', String(Math.min(currentStep + 1, 5)));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePrevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
    localStorage.setItem('coi_current_step', String(Math.max(currentStep - 1, 1)));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Save current step whenever it changes
  useEffect(() => {
    if (user) {
      localStorage.setItem('coi_current_step', String(currentStep));
    }
  }, [currentStep, user]);

  // Save caseState whenever it changes
  useEffect(() => {
    if (user && caseState) {
      localStorage.setItem('coi_case_state', JSON.stringify(caseState));
    }
  }, [caseState, user]);

  if (!user) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-[#171b0e] text-[#dfe4c6] flex flex-col font-sans">
      <Navbar
        onLogout={handleLogout}
        onResetCase={handleResetCase}
        onOpenCases={() => setCurrentStep(6)}
      />

      <StepTracker
        currentStep={currentStep}
        caseState={caseState}
        onSelectStep={(step) => {
          setCurrentStep(step);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        {currentStep === 1 && (
          <ConveningOrderStep
            caseState={caseState}
            onUpdateCase={setCaseState}
            onNextStep={handleNextStep}
          />
        )}

        {currentStep === 2 && (
          <EvidenceAndLawsStep
            caseState={caseState}
            onUpdateCase={setCaseState}
            onNextStep={handleNextStep}
            onPrevStep={handlePrevStep}
          />
        )}

        {currentStep === 3 && (
          <WitnessStep
            caseState={caseState}
            onUpdateCase={setCaseState}
            onNextStep={handleNextStep}
            onPrevStep={handlePrevStep}
          />
        )}

        {currentStep === 4 && (
          <PresidingOfficerStep
            caseState={caseState}
            onUpdateCase={setCaseState}
            onNextStep={handleNextStep}
            onPrevStep={handlePrevStep}
            user={user}
          />
        )}

        {currentStep === 5 && (
          <CoiDraftStep
            caseState={caseState}
            onUpdateCase={setCaseState}
            onPrevStep={handlePrevStep}
            onViewAllCases={() => setCurrentStep(6)}
          />
        )}

        {currentStep === 6 && (
          <AllCasesView
            onSelectCase={handleSelectCaseFromList}
            onNewCase={handleResetCase}
          />
        )}
      </main>

      <footer className="border-t border-[#c23a2c] bg-[#10140a] py-3 text-center text-xs text-[#e9ecd4] print:hidden">
        Court of Inquiry Generation &bull; Armed Forces Legal Assistant
      </footer>
    </div>
  );
}
