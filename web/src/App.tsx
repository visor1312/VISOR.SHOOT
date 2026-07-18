import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import HookAnalyzer from "./components/HookAnalyzer";
import CreateReelWizard from "./components/CreateReelWizard";

function App() {
  const [hookOpen, setHookOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  // Beim Schliessen eines Modals hochgezaehlt: der key-Wechsel laesst das
  // Dashboard neu mounten und damit seine Daten frisch vom Backend laden.
  const [refreshKey, setRefreshKey] = useState(0);

  function closeModals() {
    setHookOpen(false);
    setWizardOpen(false);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar />
      <Dashboard
        key={refreshKey}
        onOpenHook={() => setHookOpen(true)}
        onOpenWizard={() => setWizardOpen(true)}
      />
      {hookOpen && <HookAnalyzer onClose={closeModals} />}
      {wizardOpen && <CreateReelWizard onClose={closeModals} />}
    </div>
  );
}

export default App;
