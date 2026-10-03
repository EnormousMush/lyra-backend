import { Link } from "react-router-dom";
import { useMe } from "../lib/hooks";
import { Wordmark } from "../components/Shell";
import PaletteArt from "../components/PaletteArt";

/* A song unrolling into pictures: waveform on top, sections below, one frame per section. */
const DEMO_SECTIONS = [
  { label: "Intro", w: 0.14, energy: 0.15, palette: ["#14223a", "#2c4a6e", "#6b8fb3", "#d9c7a8", "#f1e6d2"] },
  { label: "Verse", w: 0.18, energy: 0.4, palette: ["#1d2b3a", "#3e5c76", "#8aa7b5", "#e3c38f", "#f6ead6"] },
  { label: "Chorus", w: 0.2, energy: 0.95, palette: ["#2b1d3a", "#7a3f6e", "#e07a5f", "#f2c46b", "#fff1d6"] },
  { label: "Verse", w: 0.16, energy: 0.45, palette: ["#1d2b3a", "#3e5c76", "#8aa7b5", "#e3c38f", "#f6ead6"] },
  { label: "Chorus", w: 0.2, energy: 1, palette: ["#2b1d3a", "#8c3f5e", "#ef8a5f", "#f7d27a", "#fff4dc"] },
  { label: "Outro", w: 0.12, energy: 0.1, palette: ["#0f1a2c", "#22344f", "#4c6a8c", "#b9b0a0", "#e6ddcc"] },
];

function demoWave(n: number) {
  const out: number[] = [];
  let x = 0;
  for (const s of DEMO_SECTIONS) {
    const count = Math.round(s.w * n);
    for (let i = 0; i < count; i++) {
      const t = (x + i) * 12.9898;
      const noise = (Math.sin(t) * 43758.5453) % 1;
      out.push(Math.min(1, 0.18 + s.energy * 0.6 + Math.abs(noise) * 0.28));
    }
    x += count;
  }
  return out;
}

function HeroStrip() {
  const wave = demoWave(180);
  let acc = 0;
  return (
    <div className="mt-16 md:mt-20" aria-label="Illustration: a song's waveform split into sections, each with its own image">
      <svg viewBox={`0 0 ${wave.length * 4} 64`} className="h-16 w-full" preserveAspectRatio="none" aria-hidden>
        {wave.map((v, i) => (
          <rect key={i} x={i * 4} y={32 - v * 30} width={2.2} height={v * 60} rx={1.1} fill="#202326" opacity={0.85} />
        ))}
      </svg>
      <div className="mt-3 flex gap-1.5">
        {DEMO_SECTIONS.map((s, i) => {
          const left = acc;
          acc += s.w;
          return (
            <div key={i} style={{ flexGrow: s.w * 100, flexBasis: 0 }} className="min-w-0">
              <div className="flex items-baseline justify-between border-t border-graphite pt-1.5 text-xs text-slate">
                <span>{s.label}</span>
                <span className="num hidden sm:inline">{Math.round(left * 214)}s</span>
              </div>
              <div
                className="develop mt-3 overflow-hidden rounded-[6px]"
                style={{ height: "clamp(150px, 24vw, 330px)", animationDelay: `${400 + i * 260}ms` }}
              >
                <PaletteArt palette={s.palette} seed={i * 97 + 13} energy={s.energy} className="h-full w-full" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

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

export default function Landing() {
  const me = useMe();
  const signedIn = !!me.data;
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex h-16 max-w-[1280px] items-center px-5 md:px-10">
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

      <main className="mx-auto max-w-[1280px] px-5 md:px-10">
        <section className="pt-14 md:pt-24">
          <h1 className="display max-w-[14ch] text-[clamp(2.9rem,7.4vw,6.4rem)] font-normal">
            Lyra Studio: an audio-to-image generator.
          </h1>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link to={signedIn ? "/library" : "/signup"} className="btn btn-primary h-12 px-6 text-[0.95rem]">
              {signedIn ? "Open library" : "Create account"}
            </Link>
            {!signedIn && (
              <Link to="/login" className="btn btn-quiet h-12 px-6 text-[0.95rem]">
                Sign in
              </Link>
            )}
          </div>
          <HeroStrip />
        </section>

        <section className="mt-28 grid gap-12 border-t border-rule pt-12 md:grid-cols-3 md:gap-10">
          {STEPS.map((s, i) => (
            <div key={s.title}>
              <div className="num text-sm text-mist">{i + 1}</div>
              <h2 className="display mt-3 text-3xl">{s.title}</h2>
              <p className="mt-3 max-w-[44ch] text-slate">{s.body}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="mx-auto mt-32 max-w-[1280px] px-5 md:px-10">
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
