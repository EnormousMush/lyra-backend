import PaletteArt from "./PaletteArt";

/**
 * Artwork for the right side of the sign-in and sign-up pages. Four looks; the one in use is
 * picked in Auth.tsx. All of them stay still under prefers-reduced-motion.
 */
export type AuthArtKind = "exposure" | "ribbons" | "constellation" | "sheet";

const PALETTE = ["#14223a", "#2c4a6e", "#6b8fb3", "#d9c7a8", "#f1e6d2"];

/* 1. Long exposure: slow drifting colour fields under film grain, like a light leak. */
function Exposure() {
  return (
    <div className="auth-exposure absolute inset-0 overflow-hidden">
      <span style={{ background: "#2c4a6e", left: "-10%", top: "-20%", animationDuration: "46s" }} />
      <span style={{ background: "#8c3f5e", left: "40%", top: "30%", animationDuration: "58s", animationDelay: "-20s" }} />
      <span style={{ background: "#d9a86b", left: "10%", top: "60%", animationDuration: "52s", animationDelay: "-35s" }} />
      <svg className="absolute inset-0 h-full w-full opacity-[0.16] mix-blend-overlay" aria-hidden>
        <filter id="auth-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
          <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#auth-grain)" />
      </svg>
    </div>
  );
}

/* 2. Ribbons: a field of thin vertical bars shaped like a waveform, breathing slowly. */
function Ribbons() {
  const n = 96;
  const bars = Array.from({ length: n }, (_, i) => {
    const t = i / n;
    const h = 0.22 + 0.5 * (0.5 + 0.5 * Math.sin(t * 9.1)) * (0.6 + 0.4 * Math.sin(t * 23 + 1.3)) + 0.12 * Math.sin(t * 61);
    return { h: Math.min(0.92, h), d: (i % 7) * 0.9 };
  });
  return (
    <div className="auth-ribbons absolute inset-0 flex items-center gap-[3px] px-[12%]">
      {bars.map((b, i) => (
        <span
          key={i}
          style={{ height: `${b.h * 100}%`, animationDelay: `-${b.d}s`, opacity: i === 61 ? 1 : undefined, background: i === 61 ? "var(--color-vega)" : undefined }}
        />
      ))}
    </div>
  );
}

/* 3. Constellation: the Lyra mark drawn large among faint stars, drifting very slowly. */
function Constellation() {
  const stars = Array.from({ length: 70 }, (_, i) => {
    const a = (i * 137.5 * Math.PI) / 180;
    const r = Math.sqrt(i / 70) * 0.5;
    return { x: 50 + Math.cos(a) * r * 100, y: 50 + Math.sin(a) * r * 100, s: 0.25 + ((i * 7) % 5) * 0.12 };
  });
  return (
    <div className="auth-constellation absolute inset-0 overflow-hidden">
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" aria-hidden>
        {stars.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.s * 0.35} fill="#ecebe6" opacity={0.18 + s.s * 0.3} />
        ))}
      </svg>
      <svg viewBox="0 0 32 32" className="absolute left-1/2 top-1/2 h-[min(60vh,420px)] w-[min(60vh,420px)]" style={{ transform: "translate(-50%, -50%)" }} aria-hidden>
        <g stroke="#ecebe6" strokeWidth="0.18" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.6">
          <path d="M8.5 7.5 L15.5 6 L13 12.5 Z" />
          <path d="M13 12.5 L21.5 14 L23.5 26 L15.2 24.6 Z" />
        </g>
        <g fill="#ecebe6">
          <circle cx="15.5" cy="6" r="0.5" />
          <circle cx="13" cy="12.5" r="0.55" />
          <circle cx="21.5" cy="14" r="0.45" />
          <circle cx="23.5" cy="26" r="0.6" />
          <circle cx="15.2" cy="24.6" r="0.6" />
        </g>
        <path d="M8.5 4.5 L9.2 6.8 L11.5 7.5 L9.2 8.2 L8.5 10.5 L7.8 8.2 L5.5 7.5 L7.8 6.8 Z" fill="var(--color-vega)" />
      </svg>
    </div>
  );
}

/* 4. Contact sheet: a loose stack of palette cards, echoing the landing page. */
function Sheet() {
  const cards = [
    { r: -9, x: -34, y: 22, w: 190, seed: 11, energy: 0.3, ratio: "3 / 4", p: PALETTE },
    { r: 6, x: 26, y: -30, w: 230, seed: 29, energy: 0.9, ratio: "4 / 3", p: ["#2b1d3a", "#7a3f6e", "#e07a5f", "#f2c46b", "#fff1d6"] },
    { r: -2, x: -4, y: 2, w: 200, seed: 47, energy: 0.6, ratio: "1 / 1", p: ["#101c17", "#2a4a3a", "#6f9a7c", "#d8c99a", "#f0ead8"] },
  ];
  return (
    <div className="auth-sheet absolute inset-0 overflow-hidden">
      {cards.map((c, i) => (
        <div
          key={i}
          className="absolute left-1/2 top-1/2 overflow-hidden rounded-[6px] shadow-[0_40px_80px_-20px_rgba(0,0,0,0.85)]"
          style={{
            width: c.w,
            aspectRatio: c.ratio,
            transform: `translate(calc(-50% + ${c.x}%), calc(-50% + ${c.y}%)) rotate(${c.r}deg)`,
            animationDelay: `-${i * 3}s`,
          }}
        >
          <PaletteArt palette={c.p} seed={c.seed} energy={c.energy} className="h-full w-full" />
        </div>
      ))}
    </div>
  );
}

export default function AuthArt({ kind }: { kind: AuthArtKind }) {
  return (
    <div className="relative hidden bg-[#17191d] lg:block" aria-hidden>
      {kind === "exposure" && <Exposure />}
      {kind === "ribbons" && <Ribbons />}
      {kind === "constellation" && <Constellation />}
      {kind === "sheet" && <Sheet />}
    </div>
  );
}
