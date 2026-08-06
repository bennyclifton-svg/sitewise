import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export type AtmosphereIntensity = "full" | "dense";

function intensityForPath(pathname: string): AtmosphereIntensity {
  if (pathname === "/" || pathname === "/login") return "full";
  return "dense";
}

/**
 * Mounts Sitewise light layers and drives the damped pointer key.
 * Dense intensity (cockpit/product UI) skips sun and the cursor key —
 * only a quiet vignette + grain remain so work surfaces stay readable.
 */
export function SwAtmosphere() {
  const { pathname } = useLocation();
  const intensity = intensityForPath(pathname);

  useEffect(() => {
    document.documentElement.classList.toggle(
      "sw-atmosphere-dense",
      intensity === "dense",
    );
    return () => {
      document.documentElement.classList.remove("sw-atmosphere-dense");
    };
  }, [intensity]);

  useEffect(() => {
    if (intensity !== "full") return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;

    let tx = window.innerWidth * 0.42;
    let ty = window.innerHeight * 0.3;
    let cx = tx;
    let cy = ty;
    let frame = 0;

    const onMove = (event: PointerEvent) => {
      tx = event.clientX;
      ty = event.clientY;
    };

    const tick = () => {
      cx += (tx - cx) * 0.055;
      cy += (ty - cy) * 0.055;
      document.documentElement.style.setProperty("--sw-key-x", `${cx.toFixed(1)}px`);
      document.documentElement.style.setProperty("--sw-key-y", `${cy.toFixed(1)}px`);
      frame = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    frame = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(frame);
    };
  }, [intensity]);

  return (
    <>
      {intensity === "full" ? <div className="sw-light-sun" aria-hidden /> : null}
      {intensity === "full" ? <div className="sw-light-key" aria-hidden /> : null}
      <div
        className="sw-light-vignette"
        aria-hidden
        style={intensity === "dense" ? { opacity: 0.45 } : undefined}
      />
      <div className="sw-grain" aria-hidden />
    </>
  );
}
