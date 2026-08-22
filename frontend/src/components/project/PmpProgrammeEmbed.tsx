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
import { Info } from "lucide-react";

import { ProgramGantt } from "@/components/project/ProgramGantt";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import {
  PROGRAMME_HEADINGS,
  type ProgrammeScale,
  type ProgrammeState,
} from "@/lib/programme";

type ProgrammeContextValue = {
  state: ProgrammeState | null;
  setVisible: (visible: boolean) => Promise<void>;
  setScale: (scale: ProgrammeScale) => Promise<void>;
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
      setScale: async (view_scale: ProgrammeScale) => {
        if (!state) return;
        setState(
          await api.setProgrammeView(projectId, state.version, {
            view_scale,
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

export function PmpProgrammeFigure({
  host,
  contentKey,
}: {
  host: HTMLElement | null;
  contentKey?: string;
}) {
  const context = useContext(ProgrammeContext);
  const state = context?.state ?? null;
  const [figureMount, setFigureMount] = useState<HTMLElement | null>(null);
  const [iconMount, setIconMount] = useState<HTMLElement | null>(null);

  useLayoutEffect(() => {
    if (!host) return;
    const apply = () => {
      const heading = findProgrammeHeading(host);
      if (heading) hideProgrammeSectionBody(heading);
    };
    apply();
    const observer = new MutationObserver(apply);
    observer.observe(host, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [host, contentKey]);

  useLayoutEffect(() => {
    if (!host || !state) {
      setFigureMount(null);
      setIconMount(null);
      return;
    }
    const heading = findProgrammeHeading(host);
    if (!heading) {
      setFigureMount(null);
      setIconMount(null);
      return;
    }
    const section = programmeSectionRoot(heading);
    const iconNode = document.createElement("div");
    iconNode.dataset.programmeToggle = "true";
    iconNode.className = "print:hidden shrink-0";
    if (heading.parentElement === section) {
      section.append(iconNode);
    } else {
      heading.after(iconNode);
    }
    setIconMount(iconNode);

    let figureNode: HTMLElement | null = null;
    if (state.pmp_embed_visible) {
      figureNode = document.createElement("div");
      figureNode.dataset.programmeFigure = "true";
      section.after(figureNode);
      setFigureMount(figureNode);
    } else {
      setFigureMount(null);
    }

    return () => {
      iconNode.remove();
      figureNode?.remove();
      setIconMount(null);
      setFigureMount(null);
    };
  }, [host, contentKey, state, state?.pmp_embed_visible, state?.version]);

  if (!state) return null;
  return (
    <>
      {iconMount
        ? createPortal(
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              className="text-muted-foreground hover:text-foreground"
              aria-label={
                state.pmp_embed_visible
                  ? "Hide programme from PMP"
                  : "Show programme in PMP"
              }
              aria-pressed={state.pmp_embed_visible}
              onClick={() => void context?.setVisible(!state.pmp_embed_visible)}
            >
              <Info className="size-3.5" aria-hidden />
            </Button>,
            iconMount,
          )
        : null}
      {state.pmp_embed_visible && figureMount
        ? createPortal(
            <div className="my-4 min-w-0">
              <ProgramGantt
                state={state}
                mode="figure"
                onScaleChange={(scale) => void context?.setScale(scale)}
              />
            </div>,
            figureMount,
          )
        : null}
    </>
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

function programmeSectionRoot(heading: HTMLElement): HTMLElement {
  const parent = heading.parentElement;
  if (
    parent &&
    parent.tagName === "DIV" &&
    parent.querySelector(":scope > h2") === heading
  ) {
    return parent;
  }
  return heading;
}

function isPmpSectionHeadingRoot(node: HTMLElement): boolean {
  if (node.matches("h2.pmp-section-heading, h2")) return true;
  return node.querySelector(":scope > h2.pmp-section-heading, :scope > h2") !== null;
}

function hideProgrammeSectionBody(heading: HTMLElement): () => void {
  const section = programmeSectionRoot(heading);
  const hidden: HTMLElement[] = [];
  let node = section.nextElementSibling;
  while (node instanceof HTMLElement) {
    const next = node.nextElementSibling;
    if (node.dataset.programmeFigure === "true") {
      node = next;
      continue;
    }
    if (isPmpSectionHeadingRoot(node)) break;
    node.hidden = true;
    node.setAttribute("data-programme-body-hidden", "true");
    hidden.push(node);
    node = next;
  }
  return () => {
    for (const item of hidden) {
      item.hidden = false;
      item.removeAttribute("data-programme-body-hidden");
    }
  };
}
