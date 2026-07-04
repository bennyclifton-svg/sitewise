import { type ReactNode } from "react";

import { CockpitShellResizeContext } from "@/components/project/cockpitShellLayout";

export function CockpitShellResizeProvider({
  onResizeLeftPanel,
  children,
}: {
  onResizeLeftPanel?: (deltaX: number) => void;
  children: ReactNode;
}) {
  return (
    <CockpitShellResizeContext.Provider value={{ onResizeLeftPanel }}>
      {children}
    </CockpitShellResizeContext.Provider>
  );
}
