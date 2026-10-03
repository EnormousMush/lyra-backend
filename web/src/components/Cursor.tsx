import { useEffect, useRef } from "react";

/**
 * A single dot that follows the pointer. Elements opt in with data-cursor="open" (grows and
 * says Open) or data-cursor="drag" (ring). Hidden on touch devices and under reduced motion.
 */
export default function Cursor() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduced) return;
    const el = ref.current!;
    document.body.classList.add("cursor-on");
    let x = -100, y = -100, tx = x, ty = y, raf = 0;
    const tick = () => {
      x += (tx - x) * 0.35;
      y += (ty - y) * 0.35;
      el.style.transform = `translate(${x}px, ${y}px)`;
      raf = requestAnimationFrame(tick);
    };
    const move = (e: PointerEvent) => {
      tx = e.clientX;
      ty = e.clientY;
      const t = (e.target as HTMLElement | null)?.closest<HTMLElement>("[data-cursor]");
      const mode = t?.dataset.cursor ?? "";
      el.dataset.mode = mode;
      el.textContent = mode === "open" ? (t?.dataset.cursorLabel ?? "Open") : "";
    };
    const reset = () => {
      el.dataset.mode = "";
      el.textContent = "";
    };
    const leave = () => (el.dataset.mode = "hidden");
    const enter = () => (el.dataset.mode = "");
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", reset, { capture: true });
    document.documentElement.addEventListener("mouseleave", leave);
    document.documentElement.addEventListener("mouseenter", enter);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", reset, { capture: true });
      document.documentElement.removeEventListener("mouseleave", leave);
      document.documentElement.removeEventListener("mouseenter", enter);
      document.body.classList.remove("cursor-on");
    };
  }, []);
  return <div ref={ref} className="cursor-dot" aria-hidden />;
}
