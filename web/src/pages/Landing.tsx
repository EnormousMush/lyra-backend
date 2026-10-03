import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useMe } from "../lib/hooks";
import { Wordmark } from "../components/Shell";
import PaletteArt from "../components/PaletteArt";
import DragField, { type Card } from "../components/DragField";

/* Cards that orbit the headline. Drag them anywhere; they glide when let go. */
const PALETTES = [
  ["#14223a", "#2c4a6e", "#6b8fb3", "#d9c7a8", "#f1e6d2"],
  ["#2b1d3a", "#7a3f6e", "#e07a5f", "#f2c46b", "#fff1d6"],
  ["#0f1a2c", "#22344f", "#4c6a8c", "#b9b0a0", "#e6ddcc"],
  ["#1d2b3a", "#3e5c76", "#8aa7b5", "#e3c38f", "#f6ead6"],
  ["#2b1d3a", "#8c3f5e", "#ef8a5f", "#f7d27a", "#fff4dc"],
  ["#101c17", "#2a4a3a", "#6f9a7c", "#d8c99a", "#f0ead8"],
];
const LAYOUT = [
  { x: 66, y: 4, r: -7, w: 190, delay: 300, energy: 0.3, ratio: "3 / 4" },
  { x: 84, y: 30, r: 5, w: 230, delay: 450, energy: 0.9, ratio: "4 / 3" },
  { x: 58, y: 48, r: 3, w: 150, delay: 600, energy: 0.6, ratio: "1 / 1" },
  { x: 76, y: 66, r: -4, w: 210, delay: 750, energy: 1, ratio: "3 / 4" },
  { x: 4, y: 70, r: 6, w: 170, delay: 900, energy: 0.15, ratio: "4 / 5" },
  { x: 30, y: 84, r: -3, w: 140, delay: 1050, energy: 0.5, ratio: "1 / 1" },
];
const CARDS: Card[] = LAYOUT.map((c, i) => ({
  ...c,
  node: (
    <div
      className="overflow-hidden rounded-[6px] shadow-[0_30px_60px_-20px_rgba(0,0,0,0.8)]"
      style={{ width: c.w, aspectRatio: c.ratio }}
    >
      <PaletteArt palette={PALETTES[i]} seed={i * 131 + 7} energy={c.energy} className="h-full w-full" />
    </div>
  ),
}));

const STEPS = [
  {
    title: "Measure",
    body: "Lyra runs a series of audio-analysis through a pipeline that embodies features like timing against the beat grid, pitch against equal temperament, brightness, dynamics and section structure.",
  },
  {
    title: "Decode",
    body: "Lyra compares the song with songs in the Lyra database with their prompts, and find the best match.",
  },
  {
    title: "Produce",
    body: "Lyra produces images like cover designs, variation scenes through out the track, and basic audio measurements of the song",
  },
];

function Rise({ text, delay = 0 }: { text: string; delay?: number }) {
  return (
    <span className="rise-mask">
      <span style={{ "--d": `${delay}ms` } as React.CSSProperties}>{text}</span>
    </span>
  );
}

function useReveal() {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => e.isIntersecting && (el.classList.add("in"), io.disconnect())),
      { threshold: 0.2 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return ref;
}

export default function Landing() {
  const me = useMe();
  const signedIn = !!me.data;
  const steps = useReveal();
  return (
    <div className="min-h-screen overflow-x-hidden">
      <header className="relative z-20 mx-auto flex h-16 max-w-[1440px] items-center px-5 md:px-10">
        <Wordmark />
        <div className="ml-auto flex items-center gap-2">
          {signedIn ? (
            <Link to="/library" className="btn btn-primary">
              Open library
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-quiet">
                Sign in
              </Link>
              <Link to="/signup" className="btn btn-primary">
                Create account
              </Link>
            </>
          )}
        </div>
      </header>

      <main>
        <section className="relative mx-auto min-h-[calc(100vh-4rem)] max-w-[1440px] px-5 md:px-10">
          <div className="absolute inset-0 z-20 hidden md:block">
            <DragField cards={CARDS} />
          </div>
          <div className="pointer-events-none relative z-10 flex min-h-[calc(100vh-4rem)] flex-col justify-center pb-24 pt-10">
            <h1 className="display pointer-events-auto w-fit max-w-[12ch] text-[clamp(3.4rem,9.5vw,9.5rem)] font-normal leading-[0.95]">
              <Rise text="Lyra Studio:" delay={80} />
              <Rise text="an audio-to-image" delay={200} />
              <Rise text="generator." delay={320} />
            </h1>
            <div
              className="drift-in pointer-events-auto mt-10 flex w-fit flex-wrap gap-3"
              style={{ "--d": "700ms", "--fy": "16px" } as React.CSSProperties}
            >
              <Link to={signedIn ? "/library" : "/signup"} className="btn btn-primary h-12 px-6 text-[0.95rem]">
                {signedIn ? "Open library" : "Create account"}
              </Link>
              {!signedIn && (
                <Link to="/login" className="btn btn-quiet h-12 px-6 text-[0.95rem]">
                  Sign in
                </Link>
              )}
            </div>
            <p className="mt-16 hidden text-xs text-mist md:block">Drag the pictures.</p>
          </div>
        </section>

        <section
          ref={steps as React.RefObject<HTMLElement>}
          className="reveal mx-auto grid max-w-[1440px] gap-12 border-t border-rule px-5 pt-16 md:grid-cols-3 md:gap-10 md:px-10"
        >
          {STEPS.map((s, i) => (
            <div key={s.title}>
              <div className="num text-sm text-mist">{i + 1}</div>
              <h2 className="display mt-3 text-4xl">{s.title}</h2>
              <p className="mt-4 max-w-[44ch] text-slate">{s.body}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="mx-auto mt-32 max-w-[1440px] px-5 md:px-10">
        <p className="flex flex-wrap gap-x-6 border-t border-rule py-10 text-sm text-slate">
          <span>Lyra Studio is built by Runbao Du.</span>
          <Link to="/terms" className="hover:text-graphite">
            Terms
          </Link>
        </p>
      </footer>
    </div>
  );
}
