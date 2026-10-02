import { useEffect } from "react";
import type { Generation } from "../lib/api";
import { ASPECT_RATIO } from "../lib/format";

export function ImageTile({ g, onOpen, caption }: { g: Generation; onOpen: (g: Generation) => void; caption?: string }) {
  const ratio = ASPECT_RATIO[g.aspect] ?? "1 / 1";
  return (
    <figure className="min-w-0">
      <button
        onClick={() => g.status === "done" && onOpen(g)}
        disabled={g.status !== "done"}
        className="group relative block w-full overflow-hidden rounded-[8px] bg-paper text-left disabled:cursor-default"
        style={{ aspectRatio: ratio }}
        aria-label={g.status === "done" ? `Open ${g.title}` : undefined}
      >
        {g.status === "done" && g.image_url ? (
          <img src={g.image_url} alt={g.title ?? ""} className="develop h-full w-full object-cover" loading="lazy" />
        ) : g.status === "error" ? (
          <div className="flex h-full w-full flex-col justify-end bg-[#efe3e1] p-3">
            <span className="text-sm font-medium text-alarm">Not painted</span>
            <span className="mt-1 line-clamp-3 text-xs text-graphite/80">{g.error}</span>
          </div>
        ) : (
          <div
            className="flex h-full w-full flex-col justify-end p-3"
            style={{
              background: g.palette?.length
                ? `linear-gradient(160deg, ${g.palette.join(", ")})`
                : "linear-gradient(160deg, #e9ebe8, #d7dad5)",
            }}
          >
            <span className={`breathe text-sm ${g.palette?.length ? "text-white" : "text-slate"}`}>
              {g.status === "planning" ? "Writing the brief" : "Painting"}
            </span>
          </div>
        )}
        {g.favorite && (
          <span className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full bg-sheet/90 text-[var(--accent)]">
            <svg width="13" height="13" viewBox="0 0 24 24" aria-label="Favourite">
              <path fill="currentColor" d="M12 21s-7.5-4.6-9.6-9.2C.8 8.2 3 4.5 6.7 4.5c2.1 0 3.6 1.2 5.3 3 1.7-1.8 3.2-3 5.3-3 3.7 0 5.9 3.7 4.3 7.3C19.5 16.4 12 21 12 21z" />
            </svg>
          </span>
        )}
        {g.mock && g.status === "done" && (
          <span className="absolute bottom-2 left-2 rounded-full bg-graphite/70 px-2 py-0.5 text-[0.65rem] text-paper">Preview render</span>
        )}
      </button>
      <figcaption className="mt-2 flex items-baseline justify-between gap-2">
        <span className="truncate text-sm">{g.title ?? caption ?? "Untitled"}</span>
        {caption && g.title && <span className="shrink-0 text-xs text-slate">{caption}</span>}
      </figcaption>
    </figure>
  );
}

interface LightboxProps {
  g: Generation;
  onClose: () => void;
  onFavorite: (g: Generation) => void;
  onVary?: (g: Generation) => void;
  styleLabel?: string;
  trackTitle?: string;
}

export function Lightbox({ g, onClose, onFavorite, onVary, styleLabel, trackTitle }: LightboxProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={g.title ?? "Image"}
      className="fixed inset-0 z-40 flex items-stretch bg-[#202326]/92 backdrop-blur-sm max-lg:flex-col max-lg:overflow-y-auto"
      onClick={onClose}
    >
      <div className="flex min-h-0 flex-1 items-center justify-center p-4 sm:p-10" onClick={(e) => e.stopPropagation()}>
        {g.image_url && (
          <img src={g.image_url} alt={g.title ?? ""} className="max-h-[86vh] max-w-full rounded-[6px] object-contain shadow-2xl" />
        )}
      </div>
      <aside
        className="w-full shrink-0 bg-sheet p-6 sm:p-8 lg:w-[400px] lg:overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="display text-3xl">{g.title}</h2>
            <p className="mt-1 text-sm text-slate">
              {[trackTitle, styleLabel, g.aspect].filter(Boolean).join(", ")}
            </p>
          </div>
          <button onClick={onClose} className="grid h-9 w-9 shrink-0 place-items-center rounded-full hover:bg-paper" aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <button className="btn btn-quiet" onClick={() => onFavorite(g)}>
            {g.favorite ? "Remove from favourites" : "Add to favourites"}
          </button>
          <a className="btn btn-quiet" href={`${g.image_url}?download=true`} download>
            Download
          </a>
          {onVary && (
            <button className="btn btn-accent" onClick={() => onVary(g)}>
              Make variations
            </button>
          )}
        </div>

        {g.rationale && (
          <>
            <h3 className="mt-8 text-sm font-medium">Why it looks like this</h3>
            <p className="voice mt-2 text-lg leading-snug">{g.rationale}</p>
          </>
        )}
        {g.palette && g.palette.length > 0 && (
          <div className="mt-6 flex overflow-hidden rounded-md">
            {g.palette.map((c, i) => (
              <div key={i} className="h-8 flex-1" style={{ background: c }} title={c} />
            ))}
          </div>
        )}
        {g.direction && (
          <>
            <h3 className="mt-8 text-sm font-medium">Your direction</h3>
            <p className="mt-2 text-sm text-slate">{g.direction}</p>
          </>
        )}
        <h3 className="mt-8 text-sm font-medium">Brief sent to the image model</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate">{g.prompt}</p>
        {g.mock && (
          <p className="mt-6 rounded-lg bg-paper p-3 text-xs text-slate">
            Preview render made on this computer. Add a Gemini key to paint it with the image model.
          </p>
        )}
      </aside>
    </div>
  );
}
