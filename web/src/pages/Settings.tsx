import { useState, type FormEvent, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useMe, useMeta } from "../lib/hooks";
import { useToast } from "../components/Toast";

function Block({ title, children, sub }: { title: string; sub?: string; children: ReactNode }) {
  return (
    <section className="grid gap-6 border-t border-rule py-10 md:grid-cols-[260px_1fr]">
      <div>
        <h2 className="font-medium">{title}</h2>
        {sub && <p className="mt-1 text-sm text-slate">{sub}</p>}
      </div>
      <div className="max-w-xl">{children}</div>
    </section>
  );
}

function Service({ name, live, model, keyPresent, envName }: { name: string; live: boolean; model: string; keyPresent: boolean; envName: string }) {
  return (
    <div className="flex items-start gap-4 rounded-xl bg-sheet p-4">
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${live ? "bg-moss" : "bg-[#c58b2a]"}`} />
      <div className="min-w-0">
        <div className="font-medium">{name}</div>
        <div className="num mt-0.5 text-sm text-slate">{model}</div>
        <p className="mt-2 text-sm">
          {live
            ? "Connected."
            : keyPresent
              ? "Key found, but preview mode is forced by LYRA_MOCK in .env."
              : `Preview mode. Add ${envName} to the .env file next to the backend and restart it.`}
        </p>
      </div>
    </div>
  );
}

function Usage() {
  const q = useQuery({ queryKey: ["usage"], queryFn: api.usage });
  const u = q.data;
  if (!u) return null;
  const row = (label: string, x: { used: number; limit: number | null }) => (
    <div className="flex items-baseline justify-between border-b border-rule/70 py-2 text-sm">
      <span className="text-slate">{label}</span>
      <span className="num font-medium">
        {x.used}
        {x.limit != null ? ` of ${x.limit}` : ""}
        {x.limit == null && <span className="ml-2 text-xs font-normal text-slate">no limit</span>}
      </span>
    </div>
  );
  return (
    <div>
      {row("Songs uploaded today", u.uploads)}
      {row("Images painted today", u.images)}
      <p className="mt-3 text-xs text-slate">Limits reset at {new Date(u.resets_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}.</p>
    </div>
  );
}

function Invites() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["invites"], queryFn: api.invites });
  const [note, setNote] = useState("");
  const make = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const inv = await api.createInvite(note);
      setNote("");
      qc.invalidateQueries({ queryKey: ["invites"] });
      await navigator.clipboard?.writeText(inv.code).catch(() => undefined);
      toast(`Invite ${inv.code} created and copied`);
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  const revoke = async (code: string) => {
    try {
      await api.revokeInvite(code);
      qc.invalidateQueries({ queryKey: ["invites"] });
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  return (
    <div>
      <form onSubmit={make} className="flex gap-3">
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Who is this for? (optional)" aria-label="Invite note" />
        <button className="btn btn-primary h-11 shrink-0">Create invite</button>
      </form>
      <ul className="mt-5 divide-y divide-rule/70">
        {(q.data ?? []).map((i) => (
          <li key={i.code} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5 text-sm">
            <code className="num rounded bg-paper px-2 py-0.5 font-medium tracking-wider">{i.code}</code>
            <span className="min-w-0 flex-1 truncate text-slate">{i.note}</span>
            {i.used_by ? (
              <span className="text-xs text-moss">used by {i.used_by}</span>
            ) : (
              <>
                <span className="text-xs text-slate">
                  {i.expires_at ? `expires ${new Date(i.expires_at).toLocaleDateString()}` : "no expiry"}
                </span>
                <button className="text-xs text-slate underline underline-offset-4 hover:text-alarm" onClick={() => revoke(i.code)}>
                  Revoke
                </button>
              </>
            )}
          </li>
        ))}
        {q.isSuccess && q.data.length === 0 && <li className="py-2 text-sm text-slate">No invites yet.</li>}
      </ul>
    </div>
  );
}

function Users() {
  const me = useMe();
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["users"], queryFn: api.users });
  const [confirm, setConfirm] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["users"] });
  const toggle = async (id: string, is_admin: boolean) => {
    try {
      await api.setAdmin(id, is_admin);
      refresh();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  const remove = async (id: string, email: string) => {
    try {
      await api.removeUser(id);
      setConfirm(null);
      refresh();
      toast(`Removed ${email}`);
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  return (
    <ul className="divide-y divide-rule/70">
      {(q.data ?? []).map((u) => {
        const self = u.id === me.data?.id;
        const locked = self || u.is_owner;
        return (
          <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3 text-sm">
            <div className="min-w-0 flex-1">
              <div className="truncate">
                {u.name}
                <span className="ml-2 text-slate">{u.email}</span>
                {self && <span className="ml-2 text-xs text-mist">you</span>}
              </div>
              <div className="num mt-0.5 text-xs text-slate">
                {u.tracks} songs, {u.images} images, joined {new Date(u.created_at).toLocaleDateString()}
              </div>
            </div>
            <button
              className="chip"
              aria-pressed={u.is_admin}
              disabled={locked}
              title={locked ? "This account stays an admin" : u.is_admin ? "Remove admin access" : "Make admin"}
              onClick={() => toggle(u.id, !u.is_admin)}
            >
              {u.is_admin ? "Admin" : "Member"}
            </button>
            {!locked &&
              (confirm === u.id ? (
                <span className="flex items-center gap-3">
                  <button className="text-xs text-alarm underline underline-offset-4" onClick={() => remove(u.id, u.email)}>
                    Remove account and files
                  </button>
                  <button className="text-xs text-slate underline underline-offset-4" onClick={() => setConfirm(null)}>
                    Keep
                  </button>
                </span>
              ) : (
                <button className="text-xs text-slate underline underline-offset-4 hover:text-alarm" onClick={() => setConfirm(u.id)}>
                  Remove
                </button>
              ))}
          </li>
        );
      })}
    </ul>
  );
}

export default function Settings() {
  const me = useMe();
  const meta = useMeta();
  const qc = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState(me.data?.name ?? "");
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const u = await api.updateMe(name);
      qc.setQueryData(["me"], u);
      toast("Name saved");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  const savePw = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.changePassword(cur, next);
      setCur("");
      setNext("");
      toast("Password changed");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  const s = meta.data?.services;

  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-24 pt-10 md:px-8">
      <h1 className="display text-5xl">Settings</h1>
      <div className="mt-10">
        <Block title="Profile" sub={me.data?.email}>
          <form onSubmit={saveName} className="flex gap-3">
            <input className="field" value={name} onChange={(e) => setName(e.target.value)} aria-label="Name" />
            <button className="btn btn-primary h-11 shrink-0">Save name</button>
          </form>
        </Block>
        <Block title="Password">
          <form onSubmit={savePw} className="space-y-3">
            <input className="field" type="password" placeholder="Current password" value={cur} onChange={(e) => setCur(e.target.value)} autoComplete="current-password" required />
            <input className="field" type="password" placeholder="New password, at least 8 characters" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required />
            <button className="btn btn-primary h-11">Change password</button>
          </form>
        </Block>
        <Block title="AI services" sub="Keys live in the backend .env file and never reach the browser.">
          {s && (
            <div className="space-y-3">
              <Service name="Claude, art director" live={s.claude.live} model={s.claude.model} keyPresent={s.claude.key_present} envName="ANTHROPIC_API_KEY" />
              <Service name="Gemini, image rendering" live={s.images.live} model={s.images.model} keyPresent={s.images.key_present} envName="GEMINI_API_KEY" />
            </div>
          )}
        </Block>
        <Block title="Usage" sub="Your allowance for today.">
          <Usage />
        </Block>
        {me.data?.is_admin && (
          <Block title="Invites" sub="Each code lets one person create an account. Codes expire after 30 days.">
            <Invites />
          </Block>
        )}
        {me.data?.is_admin && (
          <Block title="Users" sub="Everyone with an account. Removing one also removes their songs and images.">
            <Users />
          </Block>
        )}
      </div>
    </main>
  );
}
