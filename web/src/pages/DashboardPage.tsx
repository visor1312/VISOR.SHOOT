import { useNavigate } from "react-router-dom";
import Dashboard from "../components/Dashboard";
import { useApp } from "../components/app-context";

/** Duenne Routen-Huelle um das bestehende Dashboard: "Hook analysieren"
 * fuehrt jetzt zur Hook-Seite, "Reel erstellen" oeffnet den Assistenten. */
export default function DashboardPage() {
  const { user, openWizard, refreshKey } = useApp();
  const navigate = useNavigate();
  return (
    <Dashboard
      key={refreshKey}
      user={user}
      onOpenHook={() => navigate("/hook")}
      onOpenWizard={openWizard}
    />
  );
}
