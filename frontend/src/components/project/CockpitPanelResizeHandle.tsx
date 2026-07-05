import { useRef, type PointerEvent as ReactPointerEvent } from "react";

import { cn } from "@/lib/utils";

type CockpitPanelResizeHandleProps = {
  ariaLabel: string;
  edge: "start" | "end";
  onResize: (deltaX: number) => void;
  className?: string;
};

export function CockpitPanelResizeHandle({
  ariaLabel,
  edge,
  onResize,
  className,
}: CockpitPanelResizeHandleProps) {
  const frameRef = useRef<number | null>(null);
  const pendingDeltaRef = useRef(0);

  function flushResize() {
    frameRef.current = null;
    if (pendingDeltaRef.current === 0) return;
    onResize(pendingDeltaRef.current);
    pendingDeltaRef.current = 0;
  }

  function queueResize(deltaX: number) {
    pendingDeltaRef.current += deltaX;
    if (frameRef.current !== null) return;
    frameRef.current = window.requestAnimationFrame(flushResize);
  }

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    event.preventDefault();

    const handle = event.currentTarget;
    handle.setPointerCapture(event.pointerId);

    let lastX = event.clientX;

    function onPointerMove(moveEvent: PointerEvent) {
      const deltaX = moveEvent.clientX - lastX;
      lastX = moveEvent.clientX;
      if (deltaX === 0) return;
      queueResize(deltaX);
    }

    function onPointerUp(upEvent: PointerEvent) {
      handle.releasePointerCapture(upEvent.pointerId);
      handle.removeEventListener("pointermove", onPointerMove);
      handle.removeEventListener("pointerup", onPointerUp);
      handle.removeEventListener("pointercancel", onPointerUp);
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
        flushResize();
      }
    }

    handle.addEventListener("pointermove", onPointerMove);
    handle.addEventListener("pointerup", onPointerUp);
    handle.addEventListener("pointercancel", onPointerUp);
  }

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={ariaLabel}
      tabIndex={-1}
      onPointerDown={onPointerDown}
      className={cn(
        "absolute top-0 z-10 hidden h-full w-2 -translate-x-1/2 cursor-col-resize touch-none lg:block",
        edge === "start" ? "left-0" : "right-0",
        "before:absolute before:inset-y-0 before:left-1/2 before:w-px before:-translate-x-1/2 before:bg-transparent",
        "hover:before:bg-brand/60 active:before:bg-brand",
        className,
      )}
    />
  );
}
