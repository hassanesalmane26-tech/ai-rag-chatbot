import { useEffect } from "react";

// Safari's keyboard resizes visualViewport, not always dvh. Only constrain the
// shell while editing; no scroll listener or permanent compositing promotion.
export default function useKeyboardViewport() {
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return undefined;
    let frame;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const editing = document.activeElement?.matches("input,textarea,select");
        if (editing && window.matchMedia("(pointer:coarse)").matches && viewport.scale === 1) {
          document.documentElement.style.setProperty("--trident-viewport", `${viewport.height}px`);
        } else document.documentElement.style.removeProperty("--trident-viewport");
      });
    };
    viewport.addEventListener("resize", update);
    document.addEventListener("focusin", update);
    document.addEventListener("focusout", update);
    return () => {
      cancelAnimationFrame(frame);
      viewport.removeEventListener("resize", update);
      document.removeEventListener("focusin", update);
      document.removeEventListener("focusout", update);
      document.documentElement.style.removeProperty("--trident-viewport");
    };
  }, []);
}
