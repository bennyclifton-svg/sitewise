import { createContext, useContext } from "react";

import type { InstructionItem } from "@/lib/instruction-tray";

export const COCKPIT_LEFT_PANEL_WIDTH_KEY = "clerk.cockpit.left-panel-width";
export const COCKPIT_REPO_PANEL_WIDTH_KEY = "clerk.cockpit.repo-panel-width";

export const COCKPIT_LEFT_PANEL_DEFAULT_WIDTH = 190;
export const COCKPIT_REPO_PANEL_DEFAULT_WIDTH = 368;

export const COCKPIT_LEFT_PANEL_MIN_WIDTH = 160;
export const COCKPIT_LEFT_PANEL_MAX_WIDTH = 560;

export const COCKPIT_REPO_PANEL_MIN_WIDTH = 280;
export const COCKPIT_REPO_PANEL_MAX_WIDTH = 640;

export function readStoredPanelWidth(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function writeStoredPanelWidth(key: string, width: number): void {
  try {
    localStorage.setItem(key, String(width));
  } catch {
    // Ignore quota or private-mode storage failures.
  }
}

export function clampPanelWidth(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Math.round(value)));
}

type CockpitShellResizeContextValue = {
  onResizeLeftPanel?: (deltaX: number) => void;
};

export const CockpitShellResizeContext = createContext<CockpitShellResizeContextValue>({});

export function useCockpitShellResize() {
  return useContext(CockpitShellResizeContext);
}

export type InstructionTraySlot = {
  items: InstructionItem[];
  isApplying: boolean;
  error: string | null;
  onRemove: (id: string) => void;
  onClearAll: () => void;
  onApply: () => void;
};

type InstructionTraySlotContextValue = {
  setTray: (tray: InstructionTraySlot | null) => void;
};

/** Present only inside ProjectShell. The shell renders the tray in the right panel. */
export const InstructionTraySlotContext =
  createContext<InstructionTraySlotContextValue | null>(null);

export function useInstructionTraySlot() {
  return useContext(InstructionTraySlotContext);
}
