import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthGuard } from "@/components/AuthGuard";

const BillingPage = lazy(() => import("@/pages/BillingPage").then(named("BillingPage")));
const ChatPage = lazy(() => import("@/pages/ChatPage").then(named("ChatPage")));
const CockpitPreviewPage = lazy(() =>
  import("@/pages/CockpitPreviewPage").then(named("CockpitPreviewPage")),
);
const HomePage = lazy(() => import("@/pages/HomePage").then(named("HomePage")));
const LoginPage = lazy(() => import("@/pages/LoginPage").then(named("LoginPage")));
const ProjectCockpitPage = lazy(() =>
  import("@/pages/ProjectCockpitPage").then(named("ProjectCockpitPage")),
);
const StyleGenomeDemoPage = lazy(() =>
  import("@/pages/StyleGenomeDemoPage").then(named("StyleGenomeDemoPage")),
);
const TenderCockpitPage = lazy(() =>
  import("@/pages/TenderCockpitPage").then(named("TenderCockpitPage")),
);

function named<T extends Record<K, React.ComponentType>, K extends keyof T>(key: K) {
  return (module: T) => ({ default: module[key] });
}

function pending(element: ReactNode) {
  return <Suspense fallback={null}>{element}</Suspense>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={pending(<LoginPage />)} />
        <Route
          path="/"
          element={
            <AuthGuard>
              {pending(<HomePage />)}
            </AuthGuard>
          }
        />
        <Route
          path="/billing"
          element={
            <AuthGuard>
              {pending(<BillingPage />)}
            </AuthGuard>
          }
        />
        <Route
          path="/chat/:threadId"
          element={
            <AuthGuard>
              {pending(<ChatPage />)}
            </AuthGuard>
          }
        />
        <Route path="/cockpit-preview" element={pending(<CockpitPreviewPage />)} />
        <Route path="/style-genome" element={pending(<StyleGenomeDemoPage />)} />
        <Route
          path="/projects/:projectId"
          element={
            <AuthGuard>
              {pending(<ProjectCockpitPage />)}
            </AuthGuard>
          }
        >
          <Route path="tender" element={pending(<TenderCockpitPage />)} />
          <Route path="tender/:comparisonId" element={pending(<TenderCockpitPage />)} />
          <Route path="tender/:comparisonId/qa" element={pending(<TenderCockpitPage />)} />
          <Route path="tender/:comparisonId/matrix" element={pending(<TenderCockpitPage />)} />
          <Route path="tender/:comparisonId/report" element={pending(<TenderCockpitPage />)} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
