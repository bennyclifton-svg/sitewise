import { ArrowLeft, ClipboardCheck, FileText, LayoutList, Table2 } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProjectDetail } from "@/lib/types/project";
import { cn } from "@/lib/utils";

type TenderTab = {
  label: string;
  to: string;
  match: (pathname: string) => boolean;
  icon: ReactNode;
  disabled?: boolean;
};

export function TenderRouteFrame({
  project,
  comparisonId,
  title,
  children,
}: {
  project: ProjectDetail;
  comparisonId: string | null;
  title: string;
  children: ReactNode;
}) {
  const location = useLocation();
  const basePath = `/projects/${project.id}/tender`;
  const comparisonPath = comparisonId ? `${basePath}/${comparisonId}` : null;
  const tabs: TenderTab[] = [
    {
      label: "Comparisons",
      to: basePath,
      match: (pathname) => pathname === basePath,
      icon: <LayoutList className="size-4" aria-hidden />,
    },
    {
      label: "Overview",
      to: comparisonPath ?? basePath,
      match: (pathname) => comparisonPath !== null && pathname === comparisonPath,
      icon: <ClipboardCheck className="size-4" aria-hidden />,
      disabled: !comparisonPath,
    },
    {
      label: "QA",
      to: comparisonPath ? `${comparisonPath}/qa` : basePath,
      match: (pathname) => comparisonPath !== null && pathname === `${comparisonPath}/qa`,
      icon: <FileText className="size-4" aria-hidden />,
      disabled: !comparisonPath,
    },
    {
      label: "Matrix",
      to: comparisonPath ? `${comparisonPath}/matrix` : basePath,
      match: (pathname) => comparisonPath !== null && pathname === `${comparisonPath}/matrix`,
      icon: <Table2 className="size-4" aria-hidden />,
      disabled: !comparisonPath,
    },
    {
      label: "Report",
      to: comparisonPath ? `${comparisonPath}/report` : basePath,
      match: (pathname) => comparisonPath !== null && pathname === `${comparisonPath}/report`,
      icon: <FileText className="size-4" aria-hidden />,
      disabled: !comparisonPath,
    },
  ];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 p-4 lg:p-6">
        <header className="rounded-md border bg-card p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <Button asChild variant="ghost" size="sm" className="-ml-2 mb-3">
                <Link to={`/projects/${project.id}`}>
                  <ArrowLeft className="size-4" aria-hidden />
                  Back to workbench
                </Link>
              </Button>
              <p className="cockpit-eyebrow">Tender comparison</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="mt-1 truncate text-sm text-muted-foreground">
                {project.title} / {project.workspace_path}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{project.phase}</Badge>
              <Badge variant="secondary">{project.status}</Badge>
            </div>
          </div>
          <nav className="mt-4 flex gap-1 overflow-x-auto" aria-label="Tender cockpit">
            {tabs.map((tab) =>
              tab.disabled ? (
                <span
                  key={tab.label}
                  className="inline-flex h-8 shrink-0 cursor-not-allowed items-center gap-1.5 rounded-md px-2.5 text-sm text-muted-foreground opacity-45"
                >
                  {tab.icon}
                  {tab.label}
                </span>
              ) : (
                <Link
                  key={tab.label}
                  to={tab.to}
                  className={cn(
                    "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2.5 text-sm transition-colors",
                    tab.match(location.pathname)
                      ? "bg-secondary font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {tab.icon}
                  {tab.label}
                </Link>
              ),
            )}
          </nav>
        </header>

        {children}
    </div>
  );
}
