import { Navigate, useLocation, useOutletContext, useParams } from "react-router-dom";

import { ComparisonList } from "@/components/project/tender/ComparisonList";
import { ComparisonOverview } from "@/components/project/tender/ComparisonOverview";
import { QaConsole } from "@/components/project/tender/QaConsole";
import { TenderMatrix } from "@/components/project/tender/TenderMatrix";
import { TenderReportPanel } from "@/components/project/tender/TenderReportPanel";
import { TenderRouteFrame } from "@/components/project/tender/TenderRouteFrame";
import type { ProjectCockpitOutletContext } from "@/pages/ProjectCockpitPage";

type TenderRouteView = "list" | "overview" | "qa" | "matrix" | "report";

/**
 * Renders the tender comparison cockpit inside the project shell's middle
 * panel. The project is supplied by the parent route via outlet context so the
 * surrounding left nav and document repository stay mounted.
 */
export function TenderCockpitPage() {
  const { projectId, comparisonId } = useParams<{
    projectId: string;
    comparisonId?: string;
  }>();
  const location = useLocation();
  const { project, selectedRepositoryEvidence = [] } =
    useOutletContext<ProjectCockpitOutletContext>();

  if (!projectId) return <Navigate to="/" replace />;
  if (!project) return null;

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
      {view === "list" ? (
        <ComparisonList
          projectId={projectId}
          selectedEvidence={selectedRepositoryEvidence}
        />
      ) : null}
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
