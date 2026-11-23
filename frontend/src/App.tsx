import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./routes/ProtectedRoute";
import { ForgotPasswordPage, GoogleCallbackPage, LoginPage, RegisterPage, ResetPasswordPage } from "./pages/AuthPages";
import Dashboard from "./pages/Dashboard";
import Problems from "./pages/Problems";
import ProblemDetail from "./pages/ProblemDetail";
import Revisions from "./pages/Revisions";
import Analytics from "./pages/Analytics";
import Topics from "./pages/Topics";
import Goals from "./pages/Goals";
import Companies from "./pages/Companies";
import AICoach from "./pages/AICoach";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/auth/callback" element={<GoogleCallbackPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="problems" element={<Problems />} />
          <Route path="problems/:id" element={<ProblemDetail />} />
          <Route path="revisions" element={<Revisions />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="topics" element={<Topics />} />
          <Route path="goals" element={<Goals />} />
          <Route path="companies" element={<Companies />} />
          <Route path="ai" element={<AICoach />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<Admin />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
