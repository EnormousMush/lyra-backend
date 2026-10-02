import { useState } from "react";
import type { TrackDetail } from "../lib/api";
import { fmtNum } from "../lib/format";

type Tab = "listening" | "dna" | "measure";

function Listening({ t }: { t: TrackDetail }) {
  const l = t.listening;
  const label = (key: string) => t.readout.find((r) => r.key === key)?.label ?? key;
  if (!l) return <p className="text-slate">The visual identity appears when analysis finishes.</p>;
  return (
    <div>
      <p className="voice text-[1.35rem] leading-snug">{l.summary}</p>
      <div className="mt-7 flex overflow-hidden rounded-lg">
        {l.palette.map((p) => (
          <div key={p.hex} className="h-14 flex-1" style={{ background: p.hex }} title={`${p.name} ${p.hex}`} />
        ))}
      </div>
      <div className="mt-2 flex">
        {l.palette.map((p) => (
          <div key={p.hex} className="min-w-0 flex-1 truncate pr-1 text-[0.7rem] text-slate">
            {p.name}
          </div>
        ))}
      </div>
      <h3 className="mt-8 text-sm font-medium">Motifs</h3>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {l.motifs.map((m) => (
          <li key={m} className="rounded-full bg-paper px-3 py-1 text-sm">
            {m}
          </li>
        ))}
      </ul>
      <h3 className="mt-8 text-sm font-medium">What the numbers say</h3>
      <ul className="mt-3 space-y-4">
        {l.evidence.map((e, i) => (
          <li key={i} className="border-l-2 border-[var(--accent)] pl-3">
            <div className="text-xs text-slate">{label(e.feature)}</div>
            <div className="mt-0.5 text-sm">{e.observation}</div>
          </li>
        ))}
      </ul>
      {l.mock && (
        <p className="mt-8 rounded-lg bg-paper p-3 text-xs text-slate">
          Preview text. Add an Anthropic key to have Claude write this from the measurements.
        </p>
      )}
    </div>
  );
}

const FACTOR_LABEL = { genre: "Genre", subgenre: "Subgenre", mood: "Mood", descriptor: "Instrumentation" } as const;

function Dna({ t }: { t: TrackDetail }) {
  const d = t.dna;
  if (!d) return <p className="text-slate">Prompt DNA appears when analysis finishes.</p>;
  return (
    <div>
      <p className="text-sm text-slate">If you asked Suno for this song, the prompt would read:</p>
      <p className="mt-3 rounded-xl bg-sheet p-4 text-[1.05rem] leading-relaxed shadow-[inset_0_0_0_1px_var(--color-rule)]">
        {d.prompt}
      </p>
      <dl className="mt-7 space-y-5">
        {(Object.keys(FACTOR_LABEL) as (keyof typeof FACTOR_LABEL)[]).map((f) => (
          <div key={f}>
            <dt className="text-xs text-slate">{FACTOR_LABEL[f]}</dt>
            <dd className="mt-1.5 space-y-1.5">
              {(d.factors[f] || []).map((x, i) => (
                <div key={x.value} className="flex items-center gap-3">
                  <span className={`min-w-0 flex-1 truncate text-sm ${i === 0 ? "font-medium" : "text-slate"}`}>{x.value}</span>
                  {d.source === "data" || f === "mood" ? (
                    <>
                      <span className="h-1.5 w-20 overflow-hidden rounded-full bg-rule/60">
                        <span
                          className="block h-full rounded-full"
                          style={{ width: `${Math.round(x.share * 100)}%`, background: i === 0 ? "var(--accent)" : "#8c9298" }}
                        />
                      </span>
                      <span className="num w-9 text-right text-xs text-slate">{Math.round(x.share * 100)}%</span>
                    </>
                  ) : null}
                </div>
              ))}
            </dd>
          </div>
        ))}
      </dl>
      {d.source === "data" ? (
        <>
          <p className="mt-7 text-xs text-slate">
            Matched against the {d.k} nearest of 21,500 Suno songs in the research feature space. Shares are
            distance-weighted votes.
          </p>
          {d.nearest_prompts.length > 0 && (
            <>
              <h3 className="mt-6 text-sm font-medium">Closest real prompts</h3>
              <ul className="mt-2 space-y-2">
                {d.nearest_prompts.map((p) => (
                  <li key={p.prompt} className="text-sm text-slate">
                    {p.prompt}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      ) : (
        <div className="mt-7 rounded-lg bg-paper p-3 text-xs text-slate">
          <p>
            Estimated by Claude from the measurements, using only words from the research prompt vocabulary
            (confidence {Math.round(d.confidence * 100)}%).
          </p>
          {d.reasoning && <p className="voice mt-2 text-sm text-graphite">{d.reasoning}</p>}
          <p className="mt-2">Import the Suno feature table to match this song against the 21,500 real songs instead.</p>
        </div>
      )}
    </div>
  );
}

function Measurements({ t }: { t: TrackDetail }) {
  const [open, setOpen] = useState<string | null>(null);
  const groups = Array.from(new Set(t.readout.map((r) => r.group)));
  const hasPct = Object.keys(t.percentiles).length > 0;
  const key = t.features.key as { best_key?: string; best_corr?: number } | undefined;
  return (
    <div>
      {key?.best_key && (
        <div className="mb-6 flex items-baseline justify-between border-b border-rule pb-3">
          <span className="text-sm">Key</span>
          <span className="num font-medium">
            {key.best_key} <span className="text-xs text-slate">r {key.best_corr?.toFixed(2)}</span>
          </span>
        </div>
      )}
      {groups.map((g) => (
        <section key={g} className="mb-7">
          <h3 className="mb-2 text-sm font-medium">{g === "Performance" ? "Performance texture" : g}</h3>
          <ul>
            {t.readout
              .filter((r) => r.group === g)
              .map((r) => {
                const pct = t.percentiles[r.key];
                return (
                  <li key={r.key} className="border-b border-rule/70 last:border-0">
                    <button
                      className="flex w-full items-baseline gap-3 py-2 text-left"
                      onClick={() => setOpen(open === r.key ? null : r.key)}
                      aria-expanded={open === r.key}
                    >
                      <span className="min-w-0 flex-1 truncate text-sm text-slate">{r.label}</span>
                      {hasPct && pct != null && (
                        <span className="relative h-1 w-16 self-center rounded-full bg-rule/70" title={`Suno percentile ${pct}`}>
                          <span
                            className="absolute top-1/2 h-2.5 w-[3px] -translate-y-1/2 rounded-full bg-[var(--accent)]"
                            style={{ left: `calc(${pct}% - 1.5px)` }}
                          />
                        </span>
                      )}
                      <span className="num w-24 text-right text-sm font-medium">
                        {fmtNum(r.value, r.fmt)}
                        <span className="ml-0.5 text-xs font-normal text-slate">{r.unit}</span>
                      </span>
                    </button>
                    {open === r.key && <p className="pb-3 text-xs leading-relaxed text-slate">{r.explain}</p>}
                  </li>
                );
              })}
          </ul>
        </section>
      ))}
      <p className="text-xs text-slate">
        {hasPct
          ? "Markers show where this song sits among the 21,500 Suno songs."
          : "Measured on the middle 10 s and 30 s of the song and on the full track, with the same settings as the research dataset."}
        {g_note}
      </p>
    </div>
  );
}

const g_note =
  " Performance texture describes how a performance feels. It is not evidence of whether a person or AI made the song.";

export default function AnalysisPanel({ t }: { t: TrackDetail }) {
  const [tab, setTab] = useState<Tab>("listening");
  const tabs: { id: Tab; label: string }[] = [
    { id: "listening", label: "Listening" },
    { id: "dna", label: "Prompt DNA" },
    { id: "measure", label: "Measurements" },
  ];
  return (
    <div>
      <div role="tablist" className="flex gap-1 rounded-full bg-paper p-1">
        {tabs.map((x) => (
          <button
            key={x.id}
            role="tab"
            aria-selected={tab === x.id}
            onClick={() => setTab(x.id)}
            className={`flex-1 rounded-full px-3 py-1.5 text-sm transition-colors ${
              tab === x.id ? "bg-sheet font-medium shadow-[0_1px_2px_rgba(32,35,38,0.12)]" : "text-slate hover:text-graphite"
            }`}
          >
            {x.label}
          </button>
        ))}
      </div>
      <div className="mt-6" role="tabpanel">
        {tab === "listening" && <Listening t={t} />}
        {tab === "dna" && <Dna t={t} />}
        {tab === "measure" && <Measurements t={t} />}
      </div>
    </div>
  );
}
