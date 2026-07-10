import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";

function App() {
  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar />
      <Dashboard />
    </div>
  );
}

export default App;
