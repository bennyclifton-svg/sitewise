import { AlertCircle, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";

import { ComparisonList } from "@/components/project/tender/ComparisonList";
import { ComparisonOverview } from "@/components/project/tender/ComparisonOverview";
import { QaConsole } from "@/components/project/tender/QaConsole";
import { TenderMatrix } from "@/components/project/tender/TenderMatrix";
import { TenderReportPanel } from "@/components/project/tender/TenderReportPanel";
import { TenderRouteFrame } from "@/components/project/tender/TenderRouteFrame";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProjectDetail } from "@/lib/types/project";

type TenderRouteView = "list" | "overview" | "qa" | "matrix" | "report";

export function TenderCockpitPage() {
  const { projectId, comparisonId } = useParams<{
    projectId: string;
    comparisonId?: string;
  }>();
  const location = useLocation();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    const id = projectId;
    let cancelled = false;

    async function loadProject() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getProject(id);
        if (!cancelled) setProject(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load this project.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadProject();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (!projectId) return <Navigate to="/" replace />;

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
        Loading tender cockpit
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6 text-center">
        <div>
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">
            {error ?? "Project not found."}
          </p>
        </div>
      </div>
    );
  }

  const view = routeView(location.pathname);
  if (view !== "list" && !comparisonId) {
    return <Navigate to={`/projects/${projectId}/tender`} replace />;
  }

  return (
    <TenderRouteFrame
      project={project}
      comparisonId={comparisonId ?? null}
      title={viewTitle(view)}
    >
      {view === "list" ? <ComparisonList projectId={projectId} /> : null}
      {view === "overview" && comparisonId ? (
        <ComparisonOverview projectId={projectId} comparisonId={comparisonId} />
      ) : null}
      {view === "qa" && comparisonId ? <QaConsole comparisonId={comparisonId} /> : null}
      {view === "matrix" && comparisonId ? (
        <TenderMatrix comparisonId={comparisonId} />
      ) : null}
      {view === "report" && comparisonId ? (
        <TenderReportPanel projectId={projectId} comparisonId={comparisonId} />
      ) : null}
    </TenderRouteFrame>
  );
}

function routeView(pathname: string): TenderRouteView {
  if (pathname.endsWith("/qa")) return "qa";
  if (pathname.endsWith("/matrix")) return "matrix";
  if (pathname.endsWith("/report")) return "report";
  if (/\/tender\/[^/]+$/.test(pathname)) return "overview";
  return "list";
}

function viewTitle(view: TenderRouteView): string {
  if (view === "overview") return "Tender overview";
  if (view === "qa") return "QA console";
  if (view === "matrix") return "Comparison matrix";
  if (view === "report") return "Report preview";
  return "Tender comparisons";
}
