import { useState } from "react";
import type { Generation, GenerateBody, Meta, Mode } from "../lib/api";

interface Props {
  meta: Meta | undefined;
  mode: Mode;
  setMode: (m: Mode) => void;
  selectedCount: number;
  totalSections: number;
  parent: Generation | null;
  clearParent: () => void;
  busy: boolean;
  onGenerate: (body: Omit<GenerateBody, "sections" | "parent_id">) => void;
}

const MODES: { id: Mode; label: string }[] = [
  { id: "cover", label: "Covers" },
  { id: "scenes", label: "Section scenes" },
  { id: "variation", label: "Variations" },
];

export default function Controls(p: Props) {
  const [style, setStyle] = useState("cinematic");
  const [aspect, setAspect] = useState("1:1");
  const [count, setCount] = useState(2);
  const [direction, setDirection] = useState("");
  const [people, setPeople] = useState(false);

  const styles = p.meta?.styles ?? [];
  const aspects = p.meta?.aspects ?? ["1:1"];
  const disabled =
    p.busy || (p.mode === "scenes" && p.selectedCount === 0) || (p.mode === "variation" && !p.parent);
  const n = p.mode === "scenes" ? p.selectedCount : count;
  const action =
    p.mode === "scenes"
      ? `Paint ${n} ${n === 1 ? "scene" : "scenes"}`
      : p.mode === "variation"
        ? `Paint ${n} ${n === 1 ? "variation" : "variations"}`
        : `Paint ${n} ${n === 1 ? "cover" : "covers"}`;

  return (
    <div className="rounded-[18px] bg-sheet p-5 shadow-[0_1px_0_rgba(32,35,38,0.06),0_14px_40px_-24px_rgba(32,35,38,0.35)] sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            className="chip"
            aria-pressed={p.mode === m.id}
            onClick={() => p.setMode(m.id)}
            disabled={m.id === "variation" && !p.parent}
            title={m.id === "variation" && !p.parent ? "Open an image and choose Make variations" : undefined}
          >
            {m.label}
          </button>
        ))}
      </div>

      {p.mode === "scenes" && (
        <p className="mt-4 text-sm text-slate">
          {p.selectedCount} of {p.totalSections} sections selected. Click the sections under the waveform to choose.
        </p>
      )}
      {p.mode === "variation" && p.parent && (
        <div className="mt-4 flex items-center gap-3 rounded-xl bg-paper p-2 pr-3">
          {p.parent.image_url && <img src={p.parent.image_url} alt="" className="h-12 w-12 rounded-md object-cover" />}
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">Varying “{p.parent.title}”</div>
            <div className="text-xs text-slate">The original is sent to the image model as a reference.</div>
          </div>
          <button className="text-sm text-slate underline underline-offset-4 hover:text-graphite" onClick={p.clearParent}>
            Clear
          </button>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_auto]">
        <div>
          <div className="text-sm font-medium">Style</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {styles.map((s) => (
              <button key={s.id} className="chip" aria-pressed={style === s.id} onClick={() => setStyle(s.id)} title={s.description}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-6">
          <div>
            <div className="text-sm font-medium">Frame</div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {aspects.map((a) => {
                const [w, h] = a.split(":").map(Number);
                const s = 14 / Math.max(w, h);
                return (
                  <button
                    key={a}
                    className="chip num px-2.5"
                    aria-pressed={aspect === a}
                    aria-label={`Aspect ratio ${a}`}
                    onClick={() => setAspect(a)}
                  >
                    <span className="inline-block rounded-[2px] border border-current" style={{ width: w * s, height: h * s }} />
                    {a}
                  </button>
                );
              })}
            </div>
          </div>
          {p.mode !== "scenes" && (
            <div>
              <div className="text-sm font-medium">Count</div>
              <div className="mt-2 flex gap-1.5">
                {[1, 2, 3, 4].map((c) => (
                  <button key={c} className="chip num w-8 justify-center px-0" aria-pressed={count === c} onClick={() => setCount(c)}>
                    {c}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <label className="mt-6 block">
        <span className="text-sm font-medium">Direction</span>
        <span className="ml-2 text-sm text-slate">optional</span>
        <textarea
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          maxLength={600}
          rows={2}
          placeholder={
            p.mode === "variation"
              ? "What should change? For example: same scene at dawn, closer framing"
              : "Anything the art director should know? For example: winter coast, no sun, lots of empty space"
          }
          className="field mt-2 h-auto resize-none py-2.5 leading-relaxed"
        />
      </label>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-slate">
          <input
            type="checkbox"
            checked={people}
            onChange={(e) => setPeople(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Allow people in the images
        </label>
        <button
          className="btn btn-accent h-11 px-6"
          disabled={disabled}
          onClick={() => p.onGenerate({ mode: p.mode, style, aspect, count, direction: direction.trim() || undefined, people })}
        >
          {p.busy ? "Starting" : action}
        </button>
      </div>
    </div>
  );
}
