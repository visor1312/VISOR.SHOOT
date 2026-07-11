import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import UploadModal from "./components/UploadModal";
import HookAnalyzer from "./components/HookAnalyzer";

function App() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [hookOpen, setHookOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar />
      <Dashboard
        onOpenUpload={() => setUploadOpen(true)}
        onOpenHook={() => setHookOpen(true)}
      />
      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} />}
      {hookOpen && <HookAnalyzer onClose={() => setHookOpen(false)} />}
    </div>
  );
}

export default App;
