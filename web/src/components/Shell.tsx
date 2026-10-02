import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useMe, useMeta } from "../lib/hooks";

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="7" fill="#202326" />
        <g fill="#E4E6E3">
          <rect x="7" y="13" width="2.6" height="6" rx="1.3" />
          <rect x="11.6" y="9" width="2.6" height="14" rx="1.3" />
          <rect x="16.2" y="6" width="2.6" height="20" rx="1.3" />
          <rect x="20.8" y="11" width="2.6" height="10" rx="1.3" />
        </g>
        <circle cx="24.6" cy="8" r="2" fill="#7C95F0" />
      </svg>
      <span className="display text-[1.45rem] font-medium">Lyra</span>
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
        <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-8 px-5 md:px-8">
          <Link to="/library" aria-label="Lyra library">
            <Wordmark />
          </Link>
          <nav className="flex items-center gap-1">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `rounded-full px-3.5 py-1.5 text-sm transition-colors ${
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
