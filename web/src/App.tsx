import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import UploadModal from "./components/UploadModal";
import HookAnalyzer from "./components/HookAnalyzer";

function App() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [hookOpen, setHookOpen] = useState(false);
  // Beim Schliessen eines Modals hochgezaehlt: der key-Wechsel laesst das
  // Dashboard neu mounten und damit seine Daten frisch vom Backend laden
  // (z.B. das gerade hochgeladene Projekt oder die neue Hook-Analyse).
  const [refreshKey, setRefreshKey] = useState(0);

  function closeModals() {
    setUploadOpen(false);
    setHookOpen(false);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar />
      <Dashboard
        key={refreshKey}
        onOpenUpload={() => setUploadOpen(true)}
        onOpenHook={() => setHookOpen(true)}
      />
      {uploadOpen && <UploadModal onClose={closeModals} />}
      {hookOpen && <HookAnalyzer onClose={closeModals} />}
    </div>
  );
}

export default App;
