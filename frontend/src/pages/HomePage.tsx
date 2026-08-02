import {
  AlertCircle,
  CreditCard,
  FileText,
  FolderOpen,
  Globe,
  LayoutDashboard,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { Button } from "@/components/ui/button";
import { CreateProjectPanel } from "@/components/project/CreateProjectPanel";
import { api } from "@/lib/api";
import { signOut } from "@/lib/auth";
import { ApiError } from "@/lib/http";
import { supabase } from "@/lib/supabase";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

type MeResponse = {
  id: string;
  email: string;
};

function formatApiError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function HomePage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState<string | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  useEffect(() => {
    void supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
  }, []);

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

  async function handleSignOut() {
    await signOut();
    setMe(null);
    setMeError(null);
    setEmail(null);
  }

  async function handleCheckBackendAuth() {
    setIsCheckingAuth(true);
    setMeError(null);
    setMe(null);

    try {
      const payload = await api.get<MeResponse>("/auth/me");
      setMe(payload);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.isNetworkError) {
          setMeError("Could not reach the backend. Is it running on port 8000?");
        } else if (error.status === 401) {
          setMeError("Session expired or invalid. Sign in again.");
        } else {
          setMeError(error.message);
        }
      } else {
        setMeError("Unexpected error checking backend auth.");
      }
    } finally {
      setIsCheckingAuth(false);
    }
  }

  function handleProjectCreated(project: ProjectDetail) {
    setProjects((current) => [project, ...current]);
    navigate(`/projects/${project.id}`);
  }

  const backendUnavailable = Boolean(projectsError);

  return (
    <div className="cockpit-page min-h-screen bg-[var(--bg-app)]">
      <header className="cockpit-shell-header">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-5">
            <span
              className="cockpit-sitewise-mark relative inline-flex shrink-0 items-center justify-center"
              aria-hidden
            >
              <span className="text-center text-[1.04rem] font-semibold lowercase leading-[1.05] tracking-tight text-black">
                site
                <br />
                wise
              </span>
            </span>
            <div className="flex min-w-0 flex-col gap-0.5 pl-2">
              <h1 className="truncate text-[1.3rem] font-semibold leading-[1.05] tracking-tight text-[var(--cockpit-sitewise-surface)]">
                SiteWise
              </h1>
              <p className="truncate text-sm font-medium leading-snug tracking-tight text-[var(--cockpit-sitewise-surface)]/90">
                Project workspaces, evidence, workflow drafts, and grounded chat.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button asChild variant="outline">
              {/* Static marketing page outside the SPA router — must be a full page load. */}
              <a href="/landing.html">
                <Globe className="size-4" aria-hidden />
                Landing page
              </a>
            </Button>
            <Button asChild variant="outline">
              <Link to="/billing">
                <CreditCard className="size-4" aria-hidden />
                Billing
              </Link>
            </Button>
            <Button variant="outline" onClick={() => void handleSignOut()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl gap-4 px-4 py-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section className="min-w-0 space-y-4">
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
                      <Link
                        to={`/projects/${project.id}`}
                        className="flex items-center gap-2 rounded-md border border-border bg-card p-4 font-medium transition-colors hover:border-[var(--info-border)] hover:bg-[var(--info-bg)]"
                      >
                        <FolderOpen
                          className="size-4 shrink-0 text-[var(--info-text)]"
                          aria-hidden
                        />
                        <span className="truncate">{project.title}</span>
                      </Link>
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

        </section>

        <aside className="space-y-4">
          <section className="rounded-md border border-border bg-card">
            <header className="border-b px-4 py-3">
              <h2 className="text-base font-semibold">Session</h2>
              <p className="text-sm text-muted-foreground">
                {email ?? "Loading your session..."}
              </p>
            </header>
            <div className="space-y-4 p-4">
              <Button
                onClick={() => void handleCheckBackendAuth()}
                disabled={isCheckingAuth}
                variant="secondary"
              >
                {isCheckingAuth ? "Checking..." : "Verify backend auth"}
              </Button>
              {me ? (
                <p className="text-sm">
                  Backend confirmed <strong>{me.email}</strong> ({me.id}).
                </p>
              ) : null}
              {meError ? (
                <p className="text-sm text-destructive" role="alert">
                  {meError}
                </p>
              ) : null}
            </div>
          </section>
        </aside>
      </main>

      <AppSystemFooter className="fixed bottom-0 left-0 z-50 rounded-tr-md border-l-0 border-b-0 shadow-sm" />
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
          <span className="rounded-md bg-background px-2 py-1">Clerk chat bar</span>
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
