import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type AtlasPayload } from "../lib/api";
import { useMeta } from "../lib/hooks";

type Factor = "genre" | "subgenre" | "mood" | "descriptor";
const SLOTS: { id: Factor; label: string }[] = [
  { id: "subgenre", label: "subgenre" },
  { id: "genre", label: "genre" },
  { id: "mood", label: "mood" },
  { id: "descriptor", label: "instrumentation" },
];

function Template({ factor, setFactor }: { factor: Factor; setFactor: (f: Factor) => void }) {
  const slot = (id: Factor, label: string) => (
    <button
      onClick={() => setFactor(id)}
      aria-pressed={factor === id}
      className={`rounded-md px-1.5 transition-colors ${
        factor === id ? "bg-graphite text-paper" : "bg-paper text-graphite hover:bg-rule/60"
      }`}
    >
      {label}
    </button>
  );
  return (
    <p className="display text-[clamp(1.5rem,3.2vw,2.6rem)] leading-[1.35]">
      {slot("subgenre", SLOTS[0].label)} {slot("genre", SLOTS[1].label)}, {slot("mood", SLOTS[2].label)} atmosphere,
      featuring {slot("descriptor", SLOTS[3].label)}
    </p>
  );
}

function Signature({ data, factor, value }: { data: AtlasPayload; factor: Factor; value: string }) {
  const meta = useMeta();
  const prof = data.profiles?.profiles[factor]?.[value];
  if (!prof) return <p className="text-slate">Too few songs with this word to profile it.</p>;
  const rows = Object.entries(prof.d)
    .map(([k, d]) => ({ k, d, label: meta.data?.catalog[k]?.label ?? k, group: meta.data?.catalog[k]?.group ?? "" }))
    .sort((a, b) => Math.abs(b.d) - Math.abs(a.d));
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.d)));
  return (
    <div className="max-w-2xl">
      <p className="text-sm text-slate">
        How {prof.n.toLocaleString()} songs prompted with “{value}” differ from the rest of the corpus. Bars are
        standardized mean differences (Cohen’s d); right means higher than the rest.
      </p>
      <ul className="mt-6 space-y-1.5">
        {rows.map((r) => {
          const w = (Math.abs(r.d) / max) * 50;
          return (
            <li key={r.k} className="grid grid-cols-[10rem_1fr_3rem] items-center gap-3 text-sm max-sm:grid-cols-[7rem_1fr_2.5rem]">
              <span className="truncate text-slate" title={r.group}>
                {r.label}
              </span>
              <span className="relative h-3">
                <span className="absolute inset-y-0 left-1/2 w-px bg-rule" />
                <span
                  className="absolute inset-y-0.5 rounded-sm"
                  style={{
                    left: r.d >= 0 ? "50%" : `${50 - w}%`,
                    width: `${w}%`,
                    background: r.d >= 0 ? "#3352c4" : "#b8743c",
                    opacity: Math.abs(r.d) < 0.2 ? 0.35 : 1,
                  }}
                />
              </span>
              <span className="num text-right text-xs">{r.d > 0 ? "+" : ""}{r.d.toFixed(2)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Vocabulary({ data, factor, value }: { data: AtlasPayload; factor: Factor; value: string }) {
  const v = data.vocabulary;
  if (factor === "genre") {
    const g = v.by_genre[value];
    if (!g) return null;
    return (
      <div className="space-y-6">
        {(
          [
            ["Subgenres", g.subgenres],
            ["Moods", g.moods],
            ["Instrumentation", g.descriptors],
          ] as const
        ).map(([label, list]) => (
          <div key={label}>
            <h3 className="text-sm font-medium">{label}</h3>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {list.map((x) => (
                <li key={x} className="rounded-full bg-paper px-3 py-1 text-sm">
                  {x}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }
  const key = factor === "subgenre" ? "subgenres" : factor === "mood" ? "moods" : "descriptors";
  const genres = Object.entries(v.by_genre)
    .filter(([, d]) => d[key].includes(value))
    .map(([g]) => g);
  return (
    <div>
      <h3 className="text-sm font-medium">Used in</h3>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {genres.map((g) => (
          <li key={g} className="rounded-full bg-paper px-3 py-1 text-sm">
            {g}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Atlas() {
  const q = useQuery({ queryKey: ["atlas"], queryFn: api.atlas, staleTime: 600_000 });
  const [factor, setFactor] = useState<Factor>("mood");
  const [value, setValue] = useState<string | null>(null);
  const data = q.data;
  const list = useMemo(() => data?.vocabulary[factor] ?? [], [data, factor]);
  const current = value && list.some((x) => x.value === value) ? value : list[0]?.value;
  const maxSongs = Math.max(1, ...list.map((x) => x.songs));
  const ready = !!data?.profiles;

  return (
    <main className="mx-auto max-w-[1440px] px-5 pb-24 pt-10 md:px-8">
      <h1 className="display text-5xl">Prompt atlas</h1>
      <p className="mt-3 max-w-[70ch] text-slate">
        The {data?.vocabulary.totals.prompts.toLocaleString() ?? "10,750"} prompts behind{" "}
        {data?.vocabulary.totals.songs.toLocaleString() ?? "21,500"} Suno songs in the humanness study. Every prompt
        uses the same template, so each word is a controlled variable. Choose a slot to explore its words.
      </p>
      <div className="mt-10">
        <Template
          factor={factor}
          setFactor={(f) => {
            setFactor(f);
            setValue(null);
          }}
        />
      </div>

      {data && !ready && (
        <div className="mt-10 rounded-[18px] bg-sheet p-6">
          <h2 className="font-medium">Audio signatures are not built yet</h2>
          <p className="mt-1 max-w-[70ch] text-sm text-slate">
            Import the research feature table to see how each word changes timing, pitch, brightness and dynamics,
            and to let Prompt DNA match songs against the real corpus. Run this from the project folder, then
            restart the backend:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-paper p-3 text-sm">
            python scripts/build_atlas.py --features featuresSuno10mid.csv
          </pre>
        </div>
      )}

      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,420px)_1fr]">
        <ul className="max-h-[70vh] overflow-y-auto pr-2" role="listbox" aria-label={`${factor} words`}>
          {list.map((x) => (
            <li key={x.value}>
              <button
                role="option"
                aria-selected={current === x.value}
                onClick={() => setValue(x.value)}
                className={`grid w-full grid-cols-[1fr_5rem_3.5rem] items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                  current === x.value ? "bg-graphite text-paper" : "hover:bg-paper"
                }`}
              >
                <span className="truncate">{x.value}</span>
                <span className="h-1 overflow-hidden rounded-full bg-rule/60">
                  <span
                    className="block h-full rounded-full"
                    style={{ width: `${(x.songs / maxSongs) * 100}%`, background: current === x.value ? "#e4e6e3" : "#5e646b" }}
                  />
                </span>
                <span className="num text-right text-xs opacity-75">{x.songs.toLocaleString()}</span>
              </button>
            </li>
          ))}
        </ul>
        {data && current && (
          <section>
            <h2 className="display text-4xl">{current}</h2>
            <p className="num mt-1 text-sm text-slate">
              {list.find((x) => x.value === current)?.songs.toLocaleString()} songs in the study
              {ready && data.profiles!.profiles[factor]?.[current]
                ? `, ${data.profiles!.profiles[factor][current].n.toLocaleString()} with measured features`
                : ""}
            </p>
            <div className="mt-8">
              {ready ? (
                <Signature data={data} factor={factor} value={current} />
              ) : (
                <Vocabulary data={data} factor={factor} value={current} />
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
