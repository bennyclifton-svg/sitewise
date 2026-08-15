import {
  AlertCircle,
  FileText,
  FolderOpen,
  LayoutDashboard,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { SitewiseMark } from "@/components/SitewiseMark";
import { Button } from "@/components/ui/button";
import { CreateProjectPanel } from "@/components/project/CreateProjectPanel";
import { ProjectTileMenu } from "@/components/project/ProjectTileMenu";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

function formatApiError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function HomePage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      setProjectsLoading(true);
      setProjectsError(null);
      try {
        const data = await api.listProjects();
        if (!cancelled) setProjects(data);
      } catch (error) {
        if (!cancelled) {
          setProjectsError(formatApiError(error, "Could not load projects."));
        }
      } finally {
        if (!cancelled) setProjectsLoading(false);
      }
    }

    void loadProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleProjectCreated(project: ProjectDetail) {
    setProjects((current) => [project, ...current]);
    navigate(`/projects/${project.id}`);
  }

  async function handleDeleteProject(project: ProjectSummary) {
    const confirmed = window.confirm(
      `Delete “${project.title}”? This cannot be undone.`,
    );
    if (!confirmed || deletingId) return;

    setDeletingId(project.id);
    setProjectsError(null);
    try {
      await api.deleteProject(project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
    } catch (error) {
      setProjectsError(formatApiError(error, "Could not delete the project."));
    } finally {
      setDeletingId(null);
    }
  }

  const backendUnavailable = Boolean(projectsError);

  return (
    <div className="cockpit-page min-h-screen">
      <header className="cockpit-shell-header">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-3">
          <SitewiseMark size={48} variant="full" className="!p-2" />
          <h1 className="truncate font-display text-[1.3rem] font-light leading-[1.05] tracking-tight text-[var(--sw-text-primary)]">
            SiteWise
          </h1>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-5">
        {backendUnavailable ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <div>
                <p className="font-medium">Project catalog API is not reachable.</p>
                <p className="mt-1">
                  Start the FastAPI backend on port 8000 and confirm{" "}
                  <code className="text-xs">VITE_API_BASE_URL</code> in{" "}
                  <code className="text-xs">frontend/.env</code>. Use the cockpit preview
                  only when the backend is genuinely offline.
                </p>
                {projectsError ? (
                  <p className="mt-2 text-xs">{projectsError}</p>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        <CreateProjectPanel onCreated={handleProjectCreated} />

        <section className="rounded-md border border-border bg-card">
          <header className="border-b px-4 py-3">
            <h2 className="text-base font-semibold">Projects</h2>
          </header>

          <div className="p-4">
            {projectsLoading ? (
              <div className="grid gap-3 md:grid-cols-2">
                <SkeletonProject />
                <SkeletonProject />
              </div>
            ) : projects.length === 0 ? (
              <EmptyProjectState backendUnavailable={Boolean(projectsError)} />
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {projects.map((project) => (
                  <li key={project.id}>
                    <div className="flex items-center gap-1 rounded-md border border-border bg-card transition-colors hover:border-[var(--info-border)] hover:bg-[var(--info-bg)]">
                      <Link
                        to={`/projects/${project.id}`}
                        className="flex min-w-0 flex-1 items-center gap-2 p-4 font-medium"
                      >
                        <FolderOpen
                          className="size-4 shrink-0 text-[var(--info-text)]"
                          aria-hidden
                        />
                        <span className="truncate">{project.title}</span>
                      </Link>
                      <div className="pr-2">
                        <ProjectTileMenu
                          title={project.title}
                          disabled={deletingId === project.id}
                          onDelete={() => {
                            void handleDeleteProject(project);
                          }}
                        />
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {projectsError ? (
              <p className="mt-4 text-sm text-destructive" role="alert">
                {projectsError}
              </p>
            ) : null}
          </div>
        </section>
      </main>

      <AppSystemFooter className="fixed bottom-0 left-0 z-50 rounded-tr-md border-l-0 border-b-0" />
    </div>
  );
}

function EmptyProjectState({ backendUnavailable }: { backendUnavailable: boolean }) {
  return (
    <div className="grid gap-4 rounded-md border border-dashed p-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="min-w-0">
        <p className="font-medium">
          {backendUnavailable ? "Project catalog unavailable" : "No projects yet"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {backendUnavailable
            ? "The cockpit shell is ready, but real projects need the FastAPI backend."
            : "Imported SiteWise projects will appear here once the catalog is available."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/cockpit-preview">
              <LayoutDashboard className="size-4" aria-hidden />
              Open cockpit preview
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/cockpit-preview#documents">
              <FileText className="size-4" aria-hidden />
              Preview repository
            </Link>
          </Button>
        </div>
      </div>
      <div className="rounded-md border bg-muted/30 p-3">
        <div className="grid grid-cols-[5rem_1fr] gap-2 text-xs">
          <span className="rounded-md bg-background px-2 py-1 font-medium">Left</span>
          <span className="rounded-md bg-background px-2 py-1">Project nav</span>
          <span className="rounded-md bg-background px-2 py-1 font-medium">Centre</span>
          <span className="rounded-md bg-background px-2 py-1">Workflow workbench</span>
          <span className="rounded-md bg-background px-2 py-1 font-medium">Right</span>
          <span className="rounded-md bg-background px-2 py-1">Document repository</span>
          <span className="rounded-md bg-background px-2 py-1 font-medium">Bottom</span>
          <span className="rounded-md bg-background px-2 py-1">Pi chat bar</span>
        </div>
      </div>
    </div>
  );
}

function SkeletonProject() {
  return (
    <div className="rounded-md border p-4">
      <div className="h-5 w-40 animate-pulse rounded bg-muted" />
    </div>
  );
}
