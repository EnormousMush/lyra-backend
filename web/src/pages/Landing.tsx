import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useMe } from "../lib/hooks";
import { Wordmark } from "../components/Shell";
import LogoArt, { type LogoStyle } from "../components/LogoArt";
import DragField, { type Card } from "../components/DragField";

/* Cards that orbit the headline: the Lyra mark in each of the studio's image styles.
   Drag them anywhere; they glide when let go. */
const LAYOUT: Array<Omit<Card, "node"> & { style: LogoStyle }> = [
  { style: "cinematic", x: 64, y: 3, r: -7, w: 180, delay: 300, ratio: "3 / 4" },
  { style: "analog", x: 84, y: 26, r: 5, w: 200, delay: 450, ratio: "4 / 3" },
  { style: "painterly", x: 55, y: 44, r: 3, w: 140, delay: 600, ratio: "1 / 1" },
  { style: "watercolor", x: 74, y: 60, r: -4, w: 190, delay: 750, ratio: "3 / 4" },
  { style: "ink", x: 3, y: 88, r: 6, w: 150, delay: 900, ratio: "4 / 5" },
  { style: "abstract", x: 24, y: 80, r: -3, w: 140, delay: 1050, ratio: "1 / 1" },
  { style: "graphic", x: 90, y: 2, r: 8, w: 120, delay: 1200, ratio: "1 / 1" },
  { style: "dreamscape", x: 44, y: 62, r: -6, w: 160, delay: 1350, ratio: "4 / 5" },
];
const CARDS: Card[] = LAYOUT.map((c) => ({
  ...c,
  node: (
    <div
      className="overflow-hidden rounded-[6px] shadow-[0_30px_60px_-20px_rgba(0,0,0,0.8)]"
      style={{ width: c.w, aspectRatio: c.ratio }}
    >
      <LogoArt style={c.style} className="h-full w-full" />
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
