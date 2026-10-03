import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Generation } from "../lib/api";
import { useMeta } from "../lib/hooks";
import { ASPECT_RATIO } from "../lib/format";
import { Lightbox, setOrigin } from "../components/Images";
import { useToast } from "../components/Toast";

export default function Gallery() {
  const [favs, setFavs] = useState(false);
  const q = useQuery({ queryKey: ["gallery", favs], queryFn: () => api.gallery(favs) });
  const meta = useMeta();
  const qc = useQueryClient();
  const toast = useToast();
  const [open, setOpen] = useState<Generation | null>(null);
  const items = q.data ?? [];

  const toggleFav = async (g: Generation) => {
    try {
      const u = await api.favorite(g.id, !g.favorite);
      setOpen((o) => (o && o.id === g.id ? { ...o, favorite: u.favorite } : o));
      toast(u.favorite ? "Added to favourites" : "Removed from favourites");
      qc.invalidateQueries({ queryKey: ["gallery"] });
      qc.invalidateQueries({ queryKey: ["track", g.track_id] });
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  return (
    <main className="mx-auto max-w-[1440px] px-5 pb-24 pt-10 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-5xl">Gallery</h1>
        </div>
        <div className="flex gap-1.5">
          <button className="chip" aria-pressed={!favs} onClick={() => setFavs(false)}>
            All
          </button>
          <button className="chip" aria-pressed={favs} onClick={() => setFavs(true)}>
            Favourites
          </button>
        </div>
      </div>

      {q.isSuccess && items.length === 0 && (
        <div className="mt-12 rounded-[18px] border border-dashed border-rule p-12 text-center">
          <p className="voice text-xl">{favs ? "No favourites yet." : "No images yet."}</p>
          <p className="mt-2 text-sm text-slate">
            {favs ? "Open any image and add it to favourites." : "Open a song in your library and paint its first covers."}
          </p>
          {!favs && (
            <Link to="/library" className="btn btn-primary mt-6">
              Go to library
            </Link>
          )}
        </div>
      )}

      <div className="mt-10 columns-2 gap-4 md:columns-3 xl:columns-4">
        {items.map((g) => (
          <figure key={g.id} className="mb-6 break-inside-avoid">
            <button
              onClick={(e) => {
                setOrigin(e);
                setOpen(g);
              }}
              data-cursor="open"
              className="tile block w-full"
              style={{ aspectRatio: ASPECT_RATIO[g.aspect] ?? "1 / 1" }}
              aria-label={`Open ${g.title}`}
            >
              {g.image_url && <img src={g.image_url} alt={g.title ?? ""} loading="lazy" />}
              <span className="veil">
                <span className="display text-2xl leading-tight text-white">{g.title}</span>
                <span className="mt-1 text-sm text-white/70">{g.track_title}</span>
              </span>
            </button>
            <figcaption className="mt-2 flex items-baseline justify-between gap-3">
              <span className="truncate text-sm">{g.title}</span>
              <Link to={`/t/${g.track_id}`} className="shrink-0 truncate text-xs text-slate hover:text-graphite">
                {g.track_title}
              </Link>
            </figcaption>
          </figure>
        ))}
      </div>

      {open && (
        <Lightbox
          g={open}
          onClose={() => setOpen(null)}
          onFavorite={toggleFav}
          styleLabel={meta.data?.styles.find((s) => s.id === open.style)?.label}
          trackTitle={open.track_title}
        />
      )}
    </main>
  );
}
