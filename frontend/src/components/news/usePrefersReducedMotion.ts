"use client";

// Stage 7B-A.3.2 — prefers-reduced-motion detection hook for the news
// entry hero. Returns a stable boolean that flips between motion /
// reduced modes. The component must read this on every render and
// pass it to the CSS animation via a data-attribute so the static
// fallback is rendered when the user has reduced-motion enabled.

import { useEffect, useState } from "react";

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return;
    }
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mql.matches);
    update();
    // Safari < 14 uses `addListener` instead of `addEventListener`.
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", update);
      return () => mql.removeEventListener("change", update);
    }
    mql.addListener(update);
    return () => mql.removeListener(update);
  }, []);

  return reduced;
}
