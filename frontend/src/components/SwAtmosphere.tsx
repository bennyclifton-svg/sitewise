import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export type AtmosphereIntensity = "full" | "dense";

function intensityForPath(pathname: string): AtmosphereIntensity {
  if (pathname === "/" || pathname === "/login") return "full";
  return "dense";
}

/**
 * Mounts Sitewise light layers.
 * Dense intensity (cockpit/product UI) skips sun —
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

  return (
    <>
      {intensity === "full" ? <div className="sw-light-sun" aria-hidden /> : null}
      <div
        className="sw-light-vignette"
        aria-hidden
        style={intensity === "dense" ? { opacity: 0.45 } : undefined}
      />
      <div className="sw-grain" aria-hidden />
    </>
  );
}
