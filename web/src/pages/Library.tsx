import { useRef, useState, type DragEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, type TrackSummary } from "../lib/api";
import { useMe, useTracks } from "../lib/hooks";
import { fmtTime, STAGE_TEXT } from "../lib/format";
import PaletteArt, { hashString } from "../components/PaletteArt";
import { useToast } from "../components/Toast";

const ACCEPT = ".mp3,.wav,.flac,.ogg,.m4a,.aac";

function Dropzone() {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();

  const send = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const t = await api.upload(file);
      qc.invalidateQueries({ queryKey: ["tracks"] });
      navigate(`/t/${t.id}`);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    send(e.dataTransfer.files?.[0]);
  };

  return (
    <button
      type="button"
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      disabled={busy}
      className={`group flex w-full items-center gap-6 rounded-[18px] border border-dashed px-6 py-7 text-left transition-colors sm:px-8 ${
        over ? "border-graphite bg-sheet" : "border-mist/70 hover:border-graphite hover:bg-paper/60"
      }`}
    >
      <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => send(e.target.files?.[0])} />
      <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden className="shrink-0">
        <circle cx="22" cy="22" r="21" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <path d="M22 13v18M14 21l8-8 8 8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </svg>
      <span className="min-w-0">
        <span className="block text-lg font-medium">{busy ? "Uploading" : "Drop a song here, or choose a file"}</span>
        <span className="mt-0.5 block text-sm text-slate">
          MP3, WAV, FLAC, OGG, M4A or AAC, up to 80 MB. Analysis takes about half a minute.
        </span>
      </span>
    </button>
  );
}

function tilt(e: React.MouseEvent<HTMLDivElement>) {
  const r = e.currentTarget.getBoundingClientRect();
  const px = (e.clientX - r.left) / r.width - 0.5;
  const py = (e.clientY - r.top) / r.height - 0.5;
  e.currentTarget.style.transform = `perspective(900px) rotateX(${-py * 10}deg) rotateY(${px * 12}deg) translateY(-4px)`;
}
function untilt(e: React.MouseEvent<HTMLDivElement>) {
  e.currentTarget.style.transform = "";
}

function Sleeve({ t }: { t: TrackSummary }) {
  const working = t.stage !== "ready" && t.stage !== "error";
  return (
    <Link to={`/t/${t.id}`} className="group block" data-cursor="open" data-cursor-label="Open">
      <div
        onMouseMove={tilt}
        onMouseLeave={untilt}
        className="sleeve relative aspect-square overflow-hidden rounded-[10px] bg-paper shadow-[0_30px_60px_-24px_rgba(0,0,0,0.8)]"
      >
        {t.cover_url ? (
          <img src={t.cover_url} alt="" className="h-full w-full object-cover" loading="lazy" />
        ) : t.palette.length ? (
          <PaletteArt palette={t.palette} seed={hashString(t.id)} className="h-full w-full" />
        ) : (
          <div className="grid h-full w-full place-items-center bg-sheet">
            <span className={`text-sm text-slate ${working ? "breathe" : ""}`}>
              {t.stage === "error" ? "Analysis failed" : STAGE_TEXT[t.stage]}
            </span>
          </div>
        )}
        {t.image_count > 0 && (
          <span className="num absolute bottom-2.5 right-2.5 rounded-full bg-graphite/80 px-2 py-0.5 text-xs text-paper backdrop-blur">
            {t.image_count} {t.image_count === 1 ? "image" : "images"}
          </span>
        )}
      </div>
      <div className="mt-3 truncate font-medium">{t.title}</div>
      <div className="num mt-0.5 truncate text-sm text-slate">
        {t.headline ? <span className="voice text-[0.95rem]">{t.headline}</span> : null}
        {!t.headline && (t.stage === "ready" ? fmtTime(t.duration_s) : STAGE_TEXT[t.stage])}
      </div>
    </Link>
  );
}

export default function Library() {
  const tracks = useTracks();
  const me = useMe();
  const list = tracks.data || [];
  return (
    <main className="mx-auto max-w-[1440px] px-5 pb-24 pt-10 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-5xl">Library</h1>
          <p className="mt-2 text-slate">
            {list.length
              ? `${list.length} ${list.length === 1 ? "song" : "songs"}, ${list.reduce((a, t) => a + t.image_count, 0)} images`
              : `Welcome, ${me.data?.name?.split(" ")[0] ?? ""}. Start with one song.`}
          </p>
        </div>
      </div>
      <div className="mt-8">
        <Dropzone />
      </div>
      {tracks.isError && <p className="mt-8 text-alarm">Could not load your library. Check that the backend is running.</p>}
      {list.length > 0 && (
        <div className="mt-12 grid grid-cols-2 gap-x-5 gap-y-9 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {list.map((t) => (
            <Sleeve key={t.id} t={t} />
          ))}
        </div>
      )}
    </main>
  );
}
