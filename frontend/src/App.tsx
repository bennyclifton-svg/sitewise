import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthGuard } from "@/components/AuthGuard";
import { BillingPage } from "@/pages/BillingPage";
import { ChatPage } from "@/pages/ChatPage";
import { CockpitPreviewPage } from "@/pages/CockpitPreviewPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProjectCockpitPage } from "@/pages/ProjectCockpitPage";
import { TenderCockpitPage } from "@/pages/TenderCockpitPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <AuthGuard>
              <HomePage />
            </AuthGuard>
          }
        />
        <Route
          path="/billing"
          element={
            <AuthGuard>
              <BillingPage />
            </AuthGuard>
          }
        />
        <Route
          path="/chat/:threadId"
          element={
            <AuthGuard>
              <ChatPage />
            </AuthGuard>
          }
        />
        <Route path="/cockpit-preview" element={<CockpitPreviewPage />} />
        <Route
          path="/projects/:projectId"
          element={
            <AuthGuard>
              <ProjectCockpitPage />
            </AuthGuard>
          }
        >
          <Route path="tender" element={<TenderCockpitPage />} />
          <Route path="tender/:comparisonId" element={<TenderCockpitPage />} />
          <Route path="tender/:comparisonId/qa" element={<TenderCockpitPage />} />
          <Route path="tender/:comparisonId/matrix" element={<TenderCockpitPage />} />
          <Route path="tender/:comparisonId/report" element={<TenderCockpitPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
