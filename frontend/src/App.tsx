import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Spin } from "antd";
import AppShell from "./components/AppShell";
import { useAuth } from "./context/AuthContext";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DocumentPoolPage = lazy(() => import("./pages/DocumentPoolPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const FreeChatPage = lazy(() => import("./pages/FreeChatPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const ProjectSpacesPage = lazy(() => import("./pages/ProjectSpacesPage"));
const RequirementAnalysisPage = lazy(() => import("./pages/RequirementAnalysisPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const TestAssetsPage = lazy(() => import("./pages/TestAssetsPage"));
const ValidationPlansPage = lazy(() => import("./pages/ValidationPlansPage"));

function PageLoader() {
  return <Spin fullscreen tip="正在加载页面" />;
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <Spin fullscreen tip="正在恢复登录状态" />;
  }

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/" element={user ? <AppShell /> : <Navigate to="/login" replace />}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectSpacesPage />} />
          <Route path="documents" element={<DocumentPoolPage />} />
          <Route path="requirements" element={<RequirementAnalysisPage />} />
          <Route path="test-assets" element={<TestAssetsPage />} />
          <Route path="validation-plans" element={<ValidationPlansPage />} />
          <Route path="free-chat" element={<FreeChatPage />} />
          <Route path="feedback" element={<FeedbackPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
