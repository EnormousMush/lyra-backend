/** Deterministic palette artwork. Used for the landing strip and as a sleeve before a track has images. */
function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 10000) / 10000;
  };
}

export function hashString(str: string) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

interface Props {
  palette: string[];
  seed: number;
  energy?: number;
  className?: string;
  title?: string;
}

export default function PaletteArt({ palette, seed, energy = 0.5, className = "", title }: Props) {
  const r = rng(seed);
  const p = palette.length >= 4 ? palette : ["#1d1a2f", "#3f3466", "#b86b5e", "#e7b07a", "#f4e6d0"];
  const id = `pa${seed}`;
  const horizon = 58 + r() * 14 - energy * 10;
  const sunX = 18 + r() * 64;
  const sunY = horizon - 10 - energy * 22 - r() * 8;
  const sunR = 6 + energy * 10;
  const ridge = (base: number, amp: number) => {
    let d = `M0 100 L0 ${base}`;
    const steps = 6 + Math.floor(r() * 6);
    for (let i = 1; i <= steps; i++) {
      const x = (i / steps) * 100;
      d += ` L${x.toFixed(1)} ${(base - r() * amp).toFixed(1)}`;
    }
    return d + " L100 100 Z";
  };
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" className={className} role="img" aria-label={title || "Palette artwork"}>
      <defs>
        <linearGradient id={`${id}s`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={p[0]} />
          <stop offset="0.75" stopColor={p[1]} />
          <stop offset="1" stopColor={p[2]} />
        </linearGradient>
        <radialGradient id={`${id}g`}>
          <stop offset="0" stopColor={p[3]} stopOpacity="0.95" />
          <stop offset="0.35" stopColor={p[3]} stopOpacity="0.35" />
          <stop offset="1" stopColor={p[3]} stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="100" height="100" fill={`url(#${id}s)`} />
      <circle cx={sunX} cy={sunY} r={sunR * 3.2} fill={`url(#${id}g)`} />
      <circle cx={sunX} cy={sunY} r={sunR * 0.55} fill={p[4] || p[3]} opacity="0.9" />
      <path d={ridge(horizon, 6 + energy * 14)} fill={p[1]} opacity="0.75" />
      <path d={ridge(horizon + 9, 5 + energy * 10)} fill={p[0]} opacity="0.85" />
      <path d={ridge(horizon + 20, 4)} fill="#000" opacity="0.35" />
    </svg>
  );
}
