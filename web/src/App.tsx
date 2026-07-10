import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import UploadModal from "./components/UploadModal";

function App() {
  const [uploadOpen, setUploadOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar />
      <Dashboard onOpenUpload={() => setUploadOpen(true)} />
      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} />}
    </div>
  );
}

export default App;
