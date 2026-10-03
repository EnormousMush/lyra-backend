import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, type Generation, type GenerateBody, type Mode, type TrackDetail } from "../lib/api";
import { useMeta, useTrack } from "../lib/hooks";
import { accentFromPalette, fmtTime, STAGE_ORDER, STAGE_TEXT } from "../lib/format";
import Timeline from "../components/Timeline";
import AnalysisPanel from "../components/AnalysisPanel";
import Controls from "../components/Controls";
import { ImageTile, Lightbox } from "../components/Images";
import { useToast } from "../components/Toast";

function Title({ t }: { t: TrackDetail }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(t.title);
  const qc = useQueryClient();
  const toast = useToast();
  useEffect(() => setValue(t.title), [t.title]);
  const save = async () => {
    setEditing(false);
    const v = value.trim();
    if (!v || v === t.title) return setValue(t.title);
    try {
      await api.rename(t.id, v);
      qc.invalidateQueries({ queryKey: ["track", t.id] });
      qc.invalidateQueries({ queryKey: ["tracks"] });
    } catch (e) {
      toast((e as Error).message, "error");
      setValue(t.title);
    }
  };
  return editing ? (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={save}
      onKeyDown={(e) => e.key === "Enter" && save()}
      className="display w-full rounded-lg bg-transparent text-[clamp(2.2rem,4.5vw,3.6rem)] outline-none ring-1 ring-rule"
      aria-label="Song title"
    />
  ) : (
    <h1
      className="display cursor-text text-[clamp(2.2rem,4.5vw,3.6rem)]"
      onClick={() => setEditing(true)}
      title="Click to rename"
    >
      {t.title}
    </h1>
  );
}

function DeleteTrack({ t }: { t: TrackDetail }) {
  const [arm, setArm] = useState(false);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const go = async () => {
    try {
      await api.deleteTrack(t.id);
      qc.removeQueries({ queryKey: ["track", t.id] });
      qc.invalidateQueries({ queryKey: ["tracks"] });
      qc.invalidateQueries({ queryKey: ["gallery"] });
      toast("Song and its images deleted");
      navigate("/library");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };
  if (!arm)
    return (
      <button className="text-sm text-slate hover:text-alarm" onClick={() => setArm(true)}>
        Delete song
      </button>
    );
  return (
    <span className="flex items-center gap-3 text-sm">
      <span className="text-slate">Delete this song and all {t.generations.length} images?</span>
      <button className="font-medium text-alarm" onClick={go}>
        Delete
      </button>
      <button className="text-slate" onClick={() => setArm(false)}>
        Keep
      </button>
    </span>
  );
}

function Progress({ t }: { t: TrackDetail }) {
  const qc = useQueryClient();
  const toast = useToast();
  if (t.stage === "error") {
    return (
      <div className="mt-10 rounded-[18px] bg-sheet p-8">
        <h2 className="text-xl font-medium">Analysis did not finish</h2>
        <p className="mt-2 max-w-[60ch] text-slate">{t.error}</p>
        <button
          className="btn btn-primary mt-6"
          onClick={async () => {
            try {
              await api.reanalyze(t.id);
              qc.invalidateQueries({ queryKey: ["track", t.id] });
            } catch (e) {
              toast((e as Error).message, "error");
            }
          }}
        >
          Run analysis again
        </button>
      </div>
    );
  }
  const steps = STAGE_ORDER.slice(1, -1);
  const at = STAGE_ORDER.indexOf(t.stage);
  return (
    <div className="mt-10 rounded-[18px] bg-sheet p-8">
      <h2 className="voice text-2xl">Listening to {t.title}</h2>
      <ol className="mt-6 grid gap-3 sm:grid-cols-4">
        {steps.map((s, i) => {
          const idx = i + 1;
          const state = idx < at ? "done" : idx === at ? "now" : "todo";
          return (
            <li key={s} className={`border-t-2 pt-2 ${state === "todo" ? "border-rule" : "border-[var(--accent)]"}`}>
              <span className={`text-sm ${state === "todo" ? "text-mist" : ""} ${state === "now" ? "breathe font-medium" : ""}`}>
                {STAGE_TEXT[s]}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-6 text-sm text-slate">This usually takes 30 to 60 seconds. You can leave this page; it keeps going.</p>
    </div>
  );
}

const MODE_LABEL: Record<Mode, string> = { cover: "Covers", scenes: "Section scenes", variation: "Variations" };

function Batches({
  t,
  styleLabel,
  onOpen,
}: {
  t: TrackDetail;
  styleLabel: (id: string) => string;
  onOpen: (g: Generation) => void;
}) {
  const batches = useMemo(() => {
    const map = new Map<string, Generation[]>();
    for (const g of t.generations) {
      if (!map.has(g.batch_id)) map.set(g.batch_id, []);
      map.get(g.batch_id)!.push(g);
    }
    return Array.from(map.values()).map((gs) =>
      gs[0].mode === "scenes" ? [...gs].sort((a, b) => (a.section_index ?? 0) - (b.section_index ?? 0)) : gs,
    );
  }, [t.generations]);

  if (!batches.length) {
    return (
      <div className="mt-10 rounded-[18px] border border-dashed border-rule p-10 text-center">
        <p className="voice text-xl">Nothing painted yet.</p>
        <p className="mt-2 text-sm text-slate">Pick a style above and paint your first covers, or switch to section scenes.</p>
      </div>
    );
  }
  return (
    <div className="mt-10 space-y-14">
      {batches.map((gs) => {
        const g0 = gs[0];
        const scenes = g0.mode === "scenes";
        const cols = scenes ? Math.min(gs.length, 5) : gs.length === 4 ? 4 : 3;
        return (
          <section key={g0.batch_id}>
            <header className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-rule pb-2">
              <h2 className="font-medium">{MODE_LABEL[g0.mode]}</h2>
              <span className="text-sm text-slate">{styleLabel(g0.style)}</span>
              <span className="num text-sm text-slate">{g0.aspect}</span>
              {g0.direction && <span className="voice min-w-0 truncate text-sm text-slate">“{g0.direction}”</span>}
              <span className="num ml-auto text-xs text-mist">
                {new Date(g0.created_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
              </span>
            </header>
            <div
              className="grid gap-4 max-sm:!grid-cols-2"
              style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` } as CSSProperties}
            >
              {gs.map((g) => {
                const sec = g.section_index != null ? t.sections[g.section_index] : null;
                return (
                  <ImageTile
                    key={g.id}
                    g={g}
                    onOpen={onOpen}
                    caption={sec ? `${sec.label}, ${fmtTime(sec.start)}` : undefined}
                  />
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default function Studio() {
  const { id = "" } = useParams();
  const track = useTrack(id);
  const meta = useMeta();
  const qc = useQueryClient();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("cover");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [parent, setParent] = useState<Generation | null>(null);
  const [open, setOpen] = useState<Generation | null>(null);
  const [busy, setBusy] = useState(false);

  const t = track.data;
  useEffect(() => {
    if (t?.sections?.length && selected.size === 0) setSelected(new Set(t.sections.map((s) => s.index)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t?.sections?.length]);

  const accent = accentFromPalette(t?.palette);
  const style = (accent ? { "--accent": accent.accent, "--accent-ink": accent.ink } : {}) as CSSProperties;
  const styleLabel = (sid: string) => meta.data?.styles.find((s) => s.id === sid)?.label ?? sid;

  if (track.isLoading) return <main className="mx-auto max-w-[1440px] px-5 pt-10 md:px-8" />;
  if (track.isError || !t) {
    return (
      <main className="mx-auto max-w-[1440px] px-5 pt-16 md:px-8">
        <h1 className="display text-4xl">This song is not in your library</h1>
        <Link to="/library" className="btn btn-primary mt-6">
          Back to library
        </Link>
      </main>
    );
  }

  const ready = t.stage === "ready";
  const generate = async (body: Omit<GenerateBody, "sections" | "parent_id">) => {
    setBusy(true);
    try {
      await api.generate(t.id, {
        ...body,
        sections: mode === "scenes" ? Array.from(selected).sort((a, b) => a - b) : undefined,
        parent_id: mode === "variation" ? parent?.id : undefined,
      });
      await qc.invalidateQueries({ queryKey: ["track", t.id] });
      window.scrollTo({ top: document.getElementById("results")?.offsetTop ?? 0, behavior: "smooth" });
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  const toggleFav = async (g: Generation) => {
    try {
      const updated = await api.favorite(g.id, !g.favorite);
      setOpen((o) => (o && o.id === g.id ? { ...o, favorite: updated.favorite } : o));
      toast(updated.favorite ? "Added to favourites" : "Removed from favourites");
      qc.invalidateQueries({ queryKey: ["track", t.id] });
      qc.invalidateQueries({ queryKey: ["gallery"] });
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };
  const vary = (g: Generation) => {
    setParent(g);
    setMode("variation");
    setOpen(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main style={style} className="mx-auto max-w-[1440px] px-5 pb-28 pt-8 md:px-8">
      <div className="flex items-center justify-between">
        <Link to="/library" className="text-sm text-slate hover:text-graphite">
          Library
        </Link>
        <DeleteTrack t={t} />
      </div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-x-10 gap-y-3">
        <div className="w-full min-w-0 md:w-auto md:flex-1">
          <Title t={t} />
          {t.headline && <p className="voice mt-1 text-xl text-slate">{t.headline}</p>}
        </div>
        {ready && (
          <dl className="num flex gap-7 text-sm">
            {[
              ["Length", fmtTime(t.duration_s)],
              ["Tempo", t.tempo ? `${Math.round(t.tempo)} BPM` : "None"],
              ["Key", t.key ?? "Unclear"],
              ["Sections", String(t.sections.length)],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-slate">{k}</dt>
                <dd className="mt-0.5 font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {ready ? (
        <>
          <div className="mt-8">
            <Timeline
              audioUrl={`/api/tracks/${t.id}/audio`}
              waveform={t.waveform}
              sections={t.sections}
              duration={t.duration_s ?? 0}
              selectable={mode === "scenes"}
              selected={selected}
              onToggle={(i) =>
                setSelected((s) => {
                  const n = new Set(s);
                  if (n.has(i)) n.delete(i);
                  else n.add(i);
                  return n;
                })
              }
            />
          </div>
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_380px] xl:gap-14">
            <div className="min-w-0">
              <Controls
                meta={meta.data}
                mode={mode}
                setMode={setMode}
                selectedCount={selected.size}
                totalSections={t.sections.length}
                parent={parent}
                clearParent={() => {
                  setParent(null);
                  setMode("cover");
                }}
                busy={busy}
                onGenerate={generate}
              />
              <div id="results">
                <Batches t={t} styleLabel={styleLabel} onOpen={setOpen} />
              </div>
            </div>
            <aside className="lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
              <AnalysisPanel t={t} />
            </aside>
          </div>
        </>
      ) : (
        <Progress t={t} />
      )}

      {open && (
        <Lightbox
          g={open}
          onClose={() => setOpen(null)}
          onFavorite={toggleFav}
          onVary={vary}
          styleLabel={styleLabel(open.style)}
          trackTitle={t.title}
        />
      )}
    </main>
  );
}
