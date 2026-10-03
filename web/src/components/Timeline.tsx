import { useEffect, useRef, useState } from "react";
import type { Section } from "../lib/api";
import { fmtTime } from "../lib/format";

interface Props {
  audioUrl: string;
  waveform: number[];
  sections: Section[];
  duration: number;
  selectable: boolean;
  selected: Set<number>;
  onToggle: (i: number) => void;
}

/** The song as a timeline: waveform, playhead, and the section bands that drive scene images. */
export default function Timeline({ audioUrl, waveform, sections, duration, selectable, selected, onToggle }: Props) {
  const audio = useRef<HTMLAudioElement>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const a = audio.current;
    if (!a) return;
    const tick = () => setT(a.currentTime);
    const on = () => setPlaying(true);
    const off = () => setPlaying(false);
    a.addEventListener("timeupdate", tick);
    a.addEventListener("play", on);
    a.addEventListener("pause", off);
    a.addEventListener("ended", off);
    return () => {
      a.removeEventListener("timeupdate", tick);
      a.removeEventListener("play", on);
      a.removeEventListener("pause", off);
      a.removeEventListener("ended", off);
    };
  }, []);

  const toggle = () => {
    const a = audio.current;
    if (!a) return;
    if (a.paused) a.play();
    else a.pause();
  };
  const seek = (frac: number) => {
    const a = audio.current;
    if (!a || !duration) return;
    a.currentTime = Math.max(0, Math.min(duration, frac * duration));
    setT(a.currentTime);
  };

  const n = waveform.length || 1;
  const progress = duration ? t / duration : 0;
  const current = sections.find((s) => t >= s.start && t < s.end);

  return (
    <div>
      <audio ref={audio} src={audioUrl} preload="metadata" />
      <div className="flex items-center gap-4">
        <button
          onClick={toggle}
          aria-label={playing ? "Pause" : "Play"}
          className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-graphite text-paper transition-transform active:scale-95"
        >
          {playing ? (
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <rect x="2" y="1" width="3.5" height="12" rx="1" fill="currentColor" />
              <rect x="8.5" y="1" width="3.5" height="12" rx="1" fill="currentColor" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <path d="M3 1.5v11l9.5-5.5z" fill="currentColor" />
            </svg>
          )}
        </button>
        <div
          className="relative h-16 min-w-0 flex-1 cursor-pointer"
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            seek((e.clientX - r.left) / r.width);
          }}
          role="slider"
          aria-label="Playback position"
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(t)}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight") seek((t + 5) / duration);
            if (e.key === "ArrowLeft") seek((t - 5) / duration);
            if (e.key === " ") {
              e.preventDefault();
              toggle();
            }
          }}
        >
          <svg viewBox={`0 0 ${n * 3} 64`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
            {waveform.map((v, i) => {
              const played = i / n < progress;
              const h = Math.max(1.5, v * 60);
              return (
                <rect
                  key={i}
                  x={i * 3}
                  y={32 - h / 2}
                  width={1.8}
                  height={h}
                  rx={0.9}
                  fill={played ? "var(--accent)" : "#ecebe6"}
                  opacity={played ? 1 : 0.78}
                />
              );
            })}
          </svg>
          <div className="pointer-events-none absolute inset-y-0 w-px bg-graphite" style={{ left: `${progress * 100}%` }} />
        </div>
        <div className="num w-24 shrink-0 text-right text-sm text-slate">
          {fmtTime(t)} / {fmtTime(duration)}
        </div>
      </div>

      <div className="mt-3 flex gap-1 pl-16 pr-28 max-sm:pl-0 max-sm:pr-0">
        {sections.map((s) => {
          const on = selected.has(s.index);
          const isNow = current?.index === s.index;
          return (
            <button
              key={s.index}
              onClick={() => (selectable ? onToggle(s.index) : seek(s.start / duration))}
              style={{ flexGrow: s.end - s.start, flexBasis: 0 }}
              aria-pressed={selectable ? on : undefined}
              title={`${s.label} ${fmtTime(s.start)} to ${fmtTime(s.end)}`}
              className={`group min-w-0 border-t-2 pt-1.5 text-left transition-colors ${
                selectable
                  ? on
                    ? "border-[var(--accent)]"
                    : "border-rule opacity-55 hover:opacity-100"
                  : isNow
                    ? "border-graphite"
                    : "border-rule hover:border-mist"
              }`}
            >
              <span className="block truncate text-xs font-medium">{s.label}</span>
              <span className="num block truncate text-[0.7rem] text-slate">{fmtTime(s.start)}</span>
              <span className="mt-1 block h-1 overflow-hidden rounded-full bg-rule/60">
                <span
                  className="block h-full rounded-full"
                  style={{ width: `${10 + s.energy * 90}%`, background: on || !selectable ? "var(--accent)" : "#6a6f78" }}
                />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
