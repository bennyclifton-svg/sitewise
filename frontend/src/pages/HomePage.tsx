import {
  AlertCircle,
  Bot,
  CreditCard,
  FileText,
  FolderOpen,
  Globe,
  LayoutDashboard,
  MessageCircle,
  Plus,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreateProjectPanel } from "@/components/project/CreateProjectPanel";
import { api } from "@/lib/api";
import { signOut } from "@/lib/auth";
import { ApiError } from "@/lib/http";
import { supabase } from "@/lib/supabase";
import type { ChatThread } from "@/lib/types/chat";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

type MeResponse = {
  id: string;
  email: string;
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatApiError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function HomePage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState<string | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    void supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadThreads() {
      setThreadsLoading(true);
      setThreadsError(null);
      try {
        const data = await api.listThreads();
        if (!cancelled) setThreads(data);
      } catch (error) {
        if (!cancelled) {
          setThreadsError(formatApiError(error, "Could not load conversations."));
        }
      } finally {
        if (!cancelled) setThreadsLoading(false);
      }
    }

    void loadThreads();
    return () => {
      cancelled = true;
    };
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
    setThreads([]);
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

  async function handleNewChat() {
    setIsCreating(true);
    setThreadsError(null);
    try {
      const thread = await api.createThread();
      setThreads((current) => [thread, ...current]);
      navigate(`/chat/${thread.id}`);
    } catch (error) {
      setThreadsError(formatApiError(error, "Could not create a new conversation."));
    } finally {
      setIsCreating(false);
    }
  }

  function handleProjectCreated(project: ProjectDetail) {
    setProjects((current) => [project, ...current]);
    navigate(`/projects/${project.id}`);
  }

  const backendUnavailable = Boolean(projectsError);
  const conversationsUnavailable = Boolean(threadsError);

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background">
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <LayoutDashboard className="size-5 text-muted-foreground" aria-hidden />
              <h1 className="text-2xl font-semibold tracking-tight">Clerk Cockpit</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Project workspaces, evidence, workflow drafts, and grounded chat.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={backendUnavailable ? "outline" : "secondary"}>
              {backendUnavailable ? "Projects API offline" : "Backend connected"}
            </Badge>
            <Button asChild variant="secondary">
              {/* Static marketing page outside the SPA router — must be a full page load. */}
              <a href="/landing.html">
                <Globe className="size-4" aria-hidden />
                Landing page
              </a>
            </Button>
            <Button asChild variant="secondary">
              <Link to="/billing">
                <CreditCard className="size-4" aria-hidden />
                Billing
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link to="/cockpit-preview">
                <LayoutDashboard className="size-4" aria-hidden />
                Open cockpit preview
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
          ) : conversationsUnavailable ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-medium">Projects are connected, but conversations could not load.</p>
              <p className="mt-1 text-xs">
                The cockpit and project catalog are working. Global chat history is unavailable
                until the chat API responds.
              </p>
              {threadsError ? <p className="mt-2 text-xs">{threadsError}</p> : null}
            </div>
          ) : null}

          <CreateProjectPanel onCreated={handleProjectCreated} />

          <section className="rounded-md border bg-background">
            <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
              <div>
                <h2 className="text-base font-semibold">Project workspaces</h2>
                <p className="text-sm text-muted-foreground">
                  Open a hosted SiteWise cockpit with documents, workflows, drafts, and chat.
                </p>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to="/cockpit-preview">
                  <FolderOpen className="size-4" aria-hidden />
                  Preview shell
                </Link>
              </Button>
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
                        className="block rounded-md border p-4 transition-colors hover:bg-muted/50"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="min-w-0">
                            <span className="flex items-center gap-2 font-medium">
                              <FolderOpen className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                              <span className="truncate">{project.title}</span>
                            </span>
                            <span className="mt-1 block break-all text-sm text-muted-foreground">
                              {project.workspace_path}
                            </span>
                          </span>
                        </div>
                        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                          <ProjectMeta label="Phase" value={project.phase} />
                          <ProjectMeta label="Status" value={project.status} />
                        </div>
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

          <section className="grid gap-4 md:grid-cols-2">
            <CapabilityTile
              icon={FileText}
              label="Document repository"
              value="Evidence panel"
            />
            <CapabilityTile
              icon={Bot}
              label="Workflow drafts"
              value="Create PMP first"
            />
          </section>
        </section>

        <aside className="space-y-4">
          <section className="rounded-md border bg-background">
            <header className="border-b px-4 py-3">
              <h2 className="text-base font-semibold">Recent conversations</h2>
              <p className="text-sm text-muted-foreground">
                Chat remains available, but the cockpit is the main workspace.
              </p>
            </header>
            <div className="space-y-4 p-4">
              <Button onClick={() => void handleNewChat()} disabled={isCreating}>
                {!isCreating ? <Plus className="size-4" aria-hidden /> : null}
                {isCreating ? "Creating..." : "New chat"}
              </Button>

              {threadsLoading ? (
                <p className="text-sm text-muted-foreground" role="status">
                  Loading conversations...
                </p>
              ) : threads.length === 0 ? (
                <div className="rounded-md border border-dashed p-4 text-sm">
                  <p className="font-medium">No conversations yet</p>
                  <p className="mt-1 text-muted-foreground">
                    Project chat opens inside each cockpit once the backend is available.
                  </p>
                </div>
              ) : (
                <ul className="divide-y rounded-md border">
                  {threads.map((thread) => (
                    <li key={thread.id}>
                      <Link
                        to={`/chat/${thread.id}`}
                        className="block px-3 py-3 text-sm hover:bg-muted/50"
                      >
                        <span className="block truncate font-medium">
                          {thread.title ?? "Untitled chat"}
                        </span>
                        <span className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                          <MessageCircle className="size-3" aria-hidden />
                          {dateFormatter.format(new Date(thread.updated_at))}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}

              {threadsError ? (
                <p className="text-sm text-destructive" role="alert">
                  {threadsError}
                </p>
              ) : null}
            </div>
          </section>

          <section className="rounded-md border bg-background">
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

function ProjectMeta({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-md bg-muted px-2 py-1">
      <span className="block text-muted-foreground">{label}</span>
      <span className="block truncate font-medium">{value}</span>
    </span>
  );
}

function CapabilityTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FileText;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border bg-background p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="size-4" aria-hidden />
        {label}
      </div>
      <p className="mt-2 text-sm font-medium">{value}</p>
    </div>
  );
}

function SkeletonProject() {
  return (
    <div className="rounded-md border p-4">
      <div className="h-5 w-40 animate-pulse rounded bg-muted" />
      <div className="mt-3 h-4 w-full animate-pulse rounded bg-muted" />
      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="h-10 animate-pulse rounded bg-muted" />
        <div className="h-10 animate-pulse rounded bg-muted" />
        <div className="h-10 animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}
