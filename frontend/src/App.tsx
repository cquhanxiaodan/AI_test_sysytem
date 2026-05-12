import { Navigate, Route, Routes } from "react-router-dom";
import { Spin } from "antd";
import AppShell from "./components/AppShell";
import { useAuth } from "./context/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import DocumentPoolPage from "./pages/DocumentPoolPage";
import LoginPage from "./pages/LoginPage";
import RequirementAnalysisPage from "./pages/RequirementAnalysisPage";
import TestAssetsPage from "./pages/TestAssetsPage";
import ValidationPlansPage from "./pages/ValidationPlansPage";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <Spin fullscreen tip="正在恢复登录状态" />;
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/" element={user ? <AppShell /> : <Navigate to="/login" replace />}>
        <Route index element={<DashboardPage />} />
        <Route path="documents" element={<DocumentPoolPage />} />
        <Route path="requirements" element={<RequirementAnalysisPage />} />
        <Route path="test-assets" element={<TestAssetsPage />} />
        <Route path="validation-plans" element={<ValidationPlansPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
