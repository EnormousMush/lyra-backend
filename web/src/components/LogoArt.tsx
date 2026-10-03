/**
 * The Lyra mark drawn in each of the studio's image styles. Used for the draggable cards on the
 * landing page, so the cards show what a style does to one subject. Pure SVG, no images.
 */
export type LogoStyle = "cinematic" | "analog" | "painterly" | "watercolor" | "ink" | "abstract" | "graphic" | "dreamscape";

export const LOGO_STYLES: LogoStyle[] = ["cinematic", "analog", "painterly", "watercolor", "ink", "abstract", "graphic", "dreamscape"];

/* The mark, in the 32-unit space of the nav logo: five stars, two polygons, one bright star. */
const PTS = { a: [15.5, 6], b: [13, 12.5], c: [21.5, 14], d: [23.5, 26], e: [15.2, 24.6] } as const;
const STAR = [8.5, 7.5] as const;
const TRI = "M8.5 7.5 L15.5 6 L13 12.5 Z";
const QUAD = "M13 12.5 L21.5 14 L23.5 26 L15.2 24.6 Z";
const FOUR = (cx: number, cy: number, r: number) =>
  `M${cx} ${cy - r} L${cx + r * 0.22} ${cy - r * 0.22} L${cx + r} ${cy} L${cx + r * 0.22} ${cy + r * 0.22} L${cx} ${cy + r} L${cx - r * 0.22} ${cy + r * 0.22} L${cx - r} ${cy} L${cx - r * 0.22} ${cy - r * 0.22} Z`;

/* Places the 32-unit mark inside the 100-unit card. */
const FIT = "translate(16 12) scale(2.6)";

function Mark({
  stroke, dots, star, width = 0.5, dot = 0.7, starR = 3.2, filter, lines = true, dotOpacity = 1,
}: {
  stroke: string; dots: string; star: string; width?: number; dot?: number; starR?: number; filter?: string; lines?: boolean; dotOpacity?: number;
}) {
  return (
    <g transform={FIT} filter={filter}>
      {lines && (
        <g stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" fill="none">
          <path d={TRI} />
          <path d={QUAD} />
        </g>
      )}
      <g fill={dots} opacity={dotOpacity}>
        {Object.values(PTS).map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={dot * (i === 3 || i === 4 ? 1.1 : 1)} />
        ))}
      </g>
      <path d={FOUR(STAR[0], STAR[1], starR)} fill={star} />
    </g>
  );
}

const Grain = ({ id, amount }: { id: string; amount: number }) => (
  <>
    <filter id={id}>
      <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" stitchTiles="stitch" />
      <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
    </filter>
    <rect width="100" height="100" filter={`url(#${id})`} opacity={amount} style={{ mixBlendMode: "overlay" }} />
  </>
);

function Cinematic({ id }: { id: string }) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}bg`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0b1a2a" />
          <stop offset="1" stopColor="#1f1410" />
        </linearGradient>
        <radialGradient id={`${id}fl`} cx="0.7" cy="0.35" r="0.5">
          <stop offset="0" stopColor="#f4c98a" stopOpacity="0.55" />
          <stop offset="1" stopColor="#f4c98a" stopOpacity="0" />
        </radialGradient>
        <filter id={`${id}soft`}><feGaussianBlur stdDeviation="0.25" /></filter>
      </defs>
      <rect width="100" height="100" fill={`url(#${id}bg)`} />
      <rect width="100" height="100" fill={`url(#${id}fl)`} />
      <line x1="0" y1="37" x2="100" y2="31" stroke="#f4c98a" strokeWidth="0.3" opacity="0.35" />
      <Mark stroke="#d9c7a8" dots="#fff4dc" star="#f1b45a" width={0.35} dot={0.75} filter={`url(#${id}soft)`} />
      <rect width="100" height="9" fill="#050608" />
      <rect y="91" width="100" height="9" fill="#050608" />
    </>
  );
}

function Analog({ id }: { id: string }) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}bg`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3a4a5c" />
          <stop offset="1" stopColor="#6b6a62" />
        </linearGradient>
        <linearGradient id={`${id}leak`} x1="1" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#ff8a3d" stopOpacity="0.7" />
          <stop offset="0.5" stopColor="#ff8a3d" stopOpacity="0" />
        </linearGradient>
        <filter id={`${id}halo`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.4" /></filter>
      </defs>
      <rect width="100" height="100" fill={`url(#${id}bg)`} />
      <g opacity="0.8" filter={`url(#${id}halo)`}>
        <Mark stroke="#f5efe0" dots="#f5efe0" star="#f5efe0" width={0.9} dot={1.2} starR={3.6} />
      </g>
      <Mark stroke="#f5efe0" dots="#fffdf6" star="#ffd9a0" width={0.4} dot={0.7} />
      <rect width="100" height="100" fill={`url(#${id}leak)`} />
      <Grain id={`${id}g`} amount={0.35} />
      <rect width="100" height="100" fill="#d8c8a8" opacity="0.12" />
    </>
  );
}

function Painterly({ id }: { id: string }) {
  const strokes = Array.from({ length: 70 }, (_, i) => {
    const t = i * 0.618;
    const x = ((t * 100) % 100) + Math.sin(i) * 6;
    const y = (i * 13.7) % 100;
    const cols = ["#1d2b3a", "#2a3f5e", "#3e5c76", "#5c6e7a", "#8aa7b5", "#2b2238"];
    return { x, y, w: 14 + (i % 5) * 4, h: 3 + (i % 3), r: -14 + (i % 7) * 4, c: cols[i % cols.length] };
  });
  return (
    <>
      <rect width="100" height="100" fill="#1b2433" />
      {strokes.map((s, i) => (
        <rect key={i} x={s.x - s.w / 2} y={s.y} width={s.w} height={s.h} rx={s.h / 2} fill={s.c} opacity="0.85" transform={`rotate(${s.r} ${s.x} ${s.y})`} />
      ))}
      <g opacity="0.55">
        <Mark stroke="#d8c08a" dots="#d8c08a" star="#e9b25a" width={1.6} dot={1.6} starR={4} />
      </g>
      <Mark stroke="#f3e2b4" dots="#fff3d2" star="#f2c46b" width={0.7} dot={1} />
      <Grain id={`${id}g`} amount={0.18} />
    </>
  );
}

function Watercolor({ id }: { id: string }) {
  return (
    <>
      <defs>
        <filter id={`${id}bleed`} x="-30%" y="-30%" width="160%" height="160%">
          <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="3" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="4" />
          <feGaussianBlur stdDeviation="0.5" />
        </filter>
        <filter id={`${id}wash`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
      </defs>
      <rect width="100" height="100" fill="#f6f1e7" />
      <g filter={`url(#${id}wash)`} opacity="0.55">
        <circle cx="62" cy="40" r="26" fill="#9db7d6" />
        <circle cx="38" cy="66" r="20" fill="#e3b3a1" />
      </g>
      <g filter={`url(#${id}bleed)`} opacity="0.9">
        <Mark stroke="#2d4a73" dots="#2d4a73" star="#c2543e" width={0.9} dot={1.1} starR={3.6} />
      </g>
      <Grain id={`${id}g`} amount={0.1} />
    </>
  );
}

function Ink({ id }: { id: string }) {
  return (
    <>
      <defs>
        <filter id={`${id}rough`} x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.4" numOctaves="2" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="1.2" />
        </filter>
      </defs>
      <rect width="100" height="100" fill="#efe9dc" />
      <g filter={`url(#${id}rough)`}>
        <Mark stroke="#15110e" dots="#15110e" star="#b8322a" width={1.1} dot={1.3} starR={3.4} />
        <path d="M70 80 c3 -2 6 -1 7 2 c1 3 -3 5 -6 4 c-2 -1 -3 -4 -1 -6 Z" fill="#15110e" opacity="0.75" />
      </g>
      <rect x="82" y="82" width="9" height="9" fill="#b8322a" opacity="0.9" />
      <Grain id={`${id}g`} amount={0.12} />
    </>
  );
}

function Abstract({ id }: { id: string }) {
  return (
    <>
      <defs>
        <filter id={`${id}b`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9" /></filter>
        <filter id={`${id}glow`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.2" /></filter>
      </defs>
      <rect width="100" height="100" fill="#2b1d3a" />
      <g filter={`url(#${id}b)`}>
        <circle cx="30" cy="30" r="34" fill="#7a3f6e" opacity="0.9" />
        <circle cx="72" cy="58" r="30" fill="#e07a5f" opacity="0.8" />
        <circle cx="40" cy="85" r="26" fill="#f2c46b" opacity="0.7" />
      </g>
      <g filter={`url(#${id}glow)`}>
        <Mark stroke="#fff1d6" dots="#fff1d6" star="#fff1d6" lines={false} dot={1.6} starR={4.4} />
      </g>
      <Mark stroke="#fff1d6" dots="#fff1d6" star="#fff1d6" lines={false} dot={0.8} starR={3} />
      <Grain id={`${id}g`} amount={0.16} />
    </>
  );
}

function Graphic() {
  return (
    <>
      <rect width="100" height="100" fill="#e9623f" />
      <circle cx="58" cy="52" r="34" fill="#15110e" />
      <rect x="0" y="86" width="100" height="14" fill="#f5e6c8" />
      <Mark stroke="#f5e6c8" dots="#f5e6c8" star="#f2c46b" width={1.4} dot={1.9} starR={4.2} />
    </>
  );
}

function Dreamscape({ id }: { id: string }) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1a1f3a" />
          <stop offset="0.65" stopColor="#5b4b7c" />
          <stop offset="1" stopColor="#d8a07c" />
        </linearGradient>
        <radialGradient id={`${id}moon`}>
          <stop offset="0" stopColor="#fff2d6" />
          <stop offset="0.6" stopColor="#fff2d6" stopOpacity="0.9" />
          <stop offset="1" stopColor="#fff2d6" stopOpacity="0" />
        </radialGradient>
        <filter id={`${id}mist`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" /></filter>
      </defs>
      <rect width="100" height="100" fill={`url(#${id}sky)`} />
      <circle cx="70" cy="70" r="34" fill={`url(#${id}moon)`} opacity="0.9" />
      <g filter={`url(#${id}mist)`} opacity="0.7">
        <ellipse cx="50" cy="96" rx="70" ry="14" fill="#f3d9c4" />
      </g>
      <path d="M0 88 Q25 78 48 86 T100 84 L100 100 L0 100 Z" fill="#2a2140" opacity="0.9" />
      <Mark stroke="#fff6e6" dots="#ffffff" star="#ffe9a8" width={0.3} dot={0.6} starR={2.8} dotOpacity={0.95} />
    </>
  );
}

export default function LogoArt({ style, className = "" }: { style: LogoStyle; className?: string }) {
  const id = `lg-${style}`;
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" className={className} role="img" aria-label={`Lyra mark, ${style} style`}>
      {style === "cinematic" && <Cinematic id={id} />}
      {style === "analog" && <Analog id={id} />}
      {style === "painterly" && <Painterly id={id} />}
      {style === "watercolor" && <Watercolor id={id} />}
      {style === "ink" && <Ink id={id} />}
      {style === "abstract" && <Abstract id={id} />}
      {style === "graphic" && <Graphic />}
      {style === "dreamscape" && <Dreamscape id={id} />}
    </svg>
  );
}
