import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useMe, useMeta } from "../lib/hooks";

/** The constellation Lyra: Vega (the blue star), the small triangle beside it, and the
 *  parallelogram of the lyre's body. Astronomy and music in one mark. */
export function LyraMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.75">
        <path d="M8.5 7.5 L15.5 6 L13 12.5 Z" />
        <path d="M13 12.5 L21.5 14 L23.5 26 L15.2 24.6 Z" />
      </g>
      <g fill="currentColor">
        <circle cx="15.5" cy="6" r="1.8" />
        <circle cx="13" cy="12.5" r="1.9" />
        <circle cx="21.5" cy="14" r="1.7" />
        <circle cx="23.5" cy="26" r="2" />
        <circle cx="15.2" cy="24.6" r="2" />
      </g>
      <path d="M8.5 1 L9.7 6.3 L15 7.5 L9.7 8.7 L8.5 14 L7.3 8.7 L2 7.5 L7.3 6.3 Z" fill="var(--color-vega)" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LyraMark />
      <span className="display whitespace-nowrap text-[1.35rem] font-medium">Lyra Studio</span>
    </span>
  );
}

const nav = [
  { to: "/library", label: "Library" },
  { to: "/gallery", label: "Gallery" },
  { to: "/atlas", label: "Atlas" },
];

function AccountMenu() {
  const me = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const initials = (me.data?.name || "?")
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const signOut = async () => {
    await api.logout();
    qc.clear();
    navigate("/");
  };
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label="Account"
        className="grid h-9 w-9 place-items-center rounded-full bg-graphite text-xs font-semibold text-paper"
      >
        {initials}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-30 w-60 rounded-2xl border border-rule bg-sheet p-2 shadow-[0_18px_50px_rgba(32,35,38,0.16)]">
          <div className="px-3 pb-2 pt-1.5">
            <div className="text-sm font-medium">{me.data?.name}</div>
            <div className="truncate text-xs text-slate">{me.data?.email}</div>
          </div>
          <Link
            to="/settings"
            onClick={() => setOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm hover:bg-paper"
          >
            Settings
          </Link>
          <button onClick={signOut} className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-paper">
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function ModeNotice() {
  const meta = useMeta();
  const s = meta.data?.services;
  if (!s || (s.claude.live && s.images.live)) return null;
  const parts = [!s.claude.live && "Claude", !s.images.live && "image rendering"].filter(Boolean).join(" and ");
  return (
    <Link
      to="/settings"
      className="hidden items-center gap-2 rounded-full border border-rule px-3 py-1.5 text-xs text-slate hover:text-graphite md:inline-flex"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-[#c58b2a]" />
      Preview mode for {parts}
    </Link>
  );
}

export default function Shell() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-rule/70 bg-wall/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-3 px-4 sm:gap-8 md:px-8">
          <Link to="/library" aria-label="Lyra Studio library">
            <Wordmark />
          </Link>
          <nav className="flex items-center gap-0.5 sm:gap-1">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `rounded-full px-2.5 py-1.5 text-sm transition-colors sm:px-3.5 ${
                    isActive ? "bg-graphite text-paper" : "text-slate hover:text-graphite"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <ModeNotice />
            <AccountMenu />
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
