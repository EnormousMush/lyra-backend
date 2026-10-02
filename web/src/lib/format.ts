export function fmtTime(s: number | null | undefined) {
  if (s == null || !isFinite(s)) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function fmtNum(v: number, digits: number) {
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function luminance([r, g, b]: [number, number, number]) {
  const c = [r, g, b].map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

function contrast(a: [number, number, number], b: [number, number, number]) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

function chroma([r, g, b]: [number, number, number]) {
  return Math.max(r, g, b) - Math.min(r, g, b);
}

/** Pick the most saturated palette colour and darken it until it reads on the paper surface. */
export function accentFromPalette(palette: string[] | undefined | null) {
  const paper: [number, number, number] = [243, 244, 241];
  const rgbs = (palette || []).map(hexToRgb).filter(Boolean) as [number, number, number][];
  if (!rgbs.length) return null;
  let best = rgbs.reduce((a, b) => (chroma(b) > chroma(a) ? b : a));
  let guard = 0;
  while (contrast(best, paper) < 4.5 && guard++ < 20) {
    best = best.map((v) => Math.round(v * 0.9)) as [number, number, number];
  }
  const ink = contrast(best, [255, 255, 255]) >= 4.5 ? "#ffffff" : "#202326";
  return { accent: `rgb(${best.join(",")})`, ink };
}

export const ASPECT_RATIO: Record<string, string> = {
  "1:1": "1 / 1",
  "4:5": "4 / 5",
  "3:2": "3 / 2",
  "16:9": "16 / 9",
  "9:16": "9 / 16",
};

export const STAGE_TEXT: Record<string, string> = {
  queued: "Waiting to start",
  decoding: "Reading the audio",
  features: "Measuring timing, pitch and tone",
  structure: "Finding the sections",
  listening: "Writing the visual identity",
  ready: "Ready",
  error: "Analysis failed",
};

export const STAGE_ORDER = ["queued", "decoding", "features", "structure", "listening", "ready"];
