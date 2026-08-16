/* eslint-disable react-hooks/set-state-in-effect */
import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { GanttChart } from "lucide-react";

import { ProgramGantt } from "@/components/project/ProgramGantt";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProgrammeState } from "@/lib/programme";

const PROGRAMME_HEADINGS = new Set([
  "programme",
  "programme of services",
  "programme and staging regime",
]);

type ProgrammeContextValue = {
  state: ProgrammeState | null;
  setVisible: (visible: boolean) => Promise<void>;
};

const ProgrammeContext = createContext<ProgrammeContextValue | null>(null);

export function PmpProgrammeProvider({
  projectId,
  children,
}: {
  projectId: string;
  children: ReactNode;
}) {
  const [state, setState] = useState<ProgrammeState | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api.getProgrammeState(projectId).then(
      (value) => {
        if (!cancelled) setState(value);
      },
      (error) => {
        if (!cancelled && error instanceof ApiError && error.status === 404) {
          setState(null);
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const value = useMemo<ProgrammeContextValue>(
    () => ({
      state,
      setVisible: async (pmp_embed_visible: boolean) => {
        if (!state) return;
        setState(
          await api.setProgrammeView(projectId, state.version, {
            pmp_embed_visible,
          }),
        );
      },
    }),
    [projectId, state],
  );

  return (
    <ProgrammeContext.Provider value={value}>{children}</ProgrammeContext.Provider>
  );
}

export function PmpProgrammeToolbar() {
  const context = useContext(ProgrammeContext);
  if (!context?.state) return null;
  const visible = context.state.pmp_embed_visible;
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="print:hidden size-10 text-muted-foreground hover:text-foreground"
      aria-label={visible ? "Hide programme from PMP" : "Show programme in PMP"}
      aria-pressed={visible}
      onClick={() => void context.setVisible(!visible)}
    >
      <GanttChart className="size-5" aria-hidden />
    </Button>
  );
}

export function PmpProgrammeFigure({
  host,
  onOpenProgram,
}: {
  host: HTMLElement | null;
  onOpenProgram?: () => void;
}) {
  const context = useContext(ProgrammeContext);
  const state = context?.state ?? null;
  const [mount, setMount] = useState<HTMLElement | null>(null);

  useLayoutEffect(() => {
    if (!host || !state?.pmp_embed_visible) {
      setMount(null);
      return;
    }
    const heading = findProgrammeHeading(host);
    if (!heading) {
      setMount(null);
      return;
    }
    const node = document.createElement("div");
    node.dataset.programmeFigure = "true";
    heading.after(node);
    setMount(node);
    return () => {
      node.remove();
      setMount(null);
    };
  }, [host, state?.pmp_embed_visible, state?.version, state?.view_scale]);

  if (!state?.pmp_embed_visible || !mount) return null;
  return createPortal(
    <div className="my-4">
      <ProgramGantt state={state} mode="figure" onOpenProgram={onOpenProgram} />
    </div>,
    mount,
  );
}

function findProgrammeHeading(host: HTMLElement): HTMLElement | null {
  const headings = host.querySelectorAll("h2");
  for (const heading of headings) {
    if (PROGRAMME_HEADINGS.has(heading.textContent?.trim().toLowerCase() ?? "")) {
      return heading;
    }
  }
  return null;
}
