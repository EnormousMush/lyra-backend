import { useEffect, useRef, type ReactNode } from "react";

/**
 * Children become draggable cards with a little inertia. Each child gets an initial
 * position (percent of the container), a rotation, and a page-load drift-in.
 */
export interface Card {
  x: number; // percent of container width
  y: number; // percent of container height
  r: number; // degrees
  w: number; // px
  delay?: number;
  node: ReactNode;
  energy?: number;
  ratio?: string;
}

export default function DragField({ cards, className = "" }: { cards: Card[]; className?: string }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const field = root.current!;
    const items = Array.from(field.querySelectorAll<HTMLElement>("[data-card]"));
    const cleanups: (() => void)[] = [];
    items.forEach((el) => {
      let dx = 0, dy = 0, vx = 0, vy = 0, lastX = 0, lastY = 0, dragging = false, raf = 0;
      const base = el.style.getPropertyValue("--r") || "0deg";
      const apply = () => {
        el.style.transform = `translate(${dx}px, ${dy}px) rotate(${base})`;
      };
      const glide = () => {
        vx *= 0.88;
        vy *= 0.88;
        dx += vx;
        dy += vy;
        apply();
        if (Math.abs(vx) > 0.05 || Math.abs(vy) > 0.05) raf = requestAnimationFrame(glide);
      };
      const down = (e: PointerEvent) => {
        if (e.button !== 0) return;
        dragging = true;
        cancelAnimationFrame(raf);
        el.classList.remove("drift-in");
        el.setPointerCapture(e.pointerId);
        lastX = e.clientX;
        lastY = e.clientY;
        vx = vy = 0;
        el.style.zIndex = String(Date.now() % 100000);
        el.style.transition = "none";
        e.preventDefault();
      };
      const move = (e: PointerEvent) => {
        if (!dragging) return;
        vx = e.clientX - lastX;
        vy = e.clientY - lastY;
        dx += vx;
        dy += vy;
        lastX = e.clientX;
        lastY = e.clientY;
        apply();
      };
      const up = (e: PointerEvent) => {
        if (!dragging) return;
        dragging = false;
        el.releasePointerCapture(e.pointerId);
        const cap = 28;
        vx = Math.max(-cap, Math.min(cap, vx * 0.6));
        vy = Math.max(-cap, Math.min(cap, vy * 0.6));
        raf = requestAnimationFrame(glide);
      };
      el.addEventListener("pointerdown", down);
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerup", up);
      el.addEventListener("pointercancel", up);
      cleanups.push(() => {
        cancelAnimationFrame(raf);
        el.removeEventListener("pointerdown", down);
        el.removeEventListener("pointermove", move);
        el.removeEventListener("pointerup", up);
        el.removeEventListener("pointercancel", up);
      });
    });
    return () => cleanups.forEach((f) => f());
  }, [cards.length]);

  return (
    <div ref={root} className={`pointer-events-none absolute inset-0 ${className}`} aria-hidden>
      {cards.map((c, i) => (
        <div
          key={i}
          data-card
          data-cursor="drag"
          className="drift-in pointer-events-auto absolute touch-none select-none"
          style={
            {
              left: `${c.x}%`,
              top: `${c.y}%`,
              width: c.w,
              "--r": `${c.r}deg`,
              "--fx": `${(c.x - 50) * 1.6}px`,
              "--fy": `${(c.y - 50) * 1.6 + 60}px`,
              "--fr": `${c.r * 2}deg`,
              "--d": `${c.delay ?? 0}ms`,
              transform: `rotate(${c.r}deg)`,
            } as React.CSSProperties
          }
        >
          {c.node}
        </div>
      ))}
    </div>
  );
}
