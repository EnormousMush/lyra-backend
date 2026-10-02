import { useState, type FormEvent, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
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
  const atlas = meta.data?.atlas;

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
        <Block title="Suno atlas" sub="Powers Prompt DNA matching and corpus percentiles.">
          {atlas?.profiles_ready ? (
            <p className="text-sm">
              Built from {atlas.source_csv} with {atlas.n_songs_with_features.toLocaleString()} songs
              {atlas.built_at ? ` on ${new Date(atlas.built_at).toLocaleDateString()}` : ""}.
            </p>
          ) : (
            <p className="text-sm text-slate">
              Not built yet. Prompt DNA is estimated by Claude until you run scripts/build_atlas.py with the research
              feature table.
            </p>
          )}
        </Block>
        <Block title="About">
          <p className="text-sm text-slate">Lyra Studio {meta.data?.version}. Runs entirely on this computer, apart from calls to the AI services above.</p>
        </Block>
      </div>
    </main>
  );
}
