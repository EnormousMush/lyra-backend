import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Wordmark } from "../components/Shell";

function Frame({ children, title, sub }: { children: React.ReactNode; title: string; sub: string }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-6 py-6 sm:px-12">
        <Link to="/" aria-label="Lyra Studio home">
          <Wordmark />
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <h1 className="display text-5xl">{title}</h1>
          <p className="mt-3 text-slate">{sub}</p>
          <div className="mt-9">{children}</div>
        </div>
      </div>
      <div className="hidden bg-[#2a2d31] lg:block" aria-hidden />
    </div>
  );
}

function Field(props: { label: string; type?: string; value: string; onChange: (v: string) => void; autoComplete?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium">{props.label}</span>
      <input
        className="field"
        type={props.type || "text"}
        value={props.value}
        autoComplete={props.autoComplete}
        onChange={(e) => props.onChange(e.target.value)}
        required
      />
    </label>
  );
}

function useFinish() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const loc = useLocation();
  return (user: unknown) => {
    qc.setQueryData(["me"], user);
    navigate((loc.state as { from?: string })?.from || "/library", { replace: true });
  };
}

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const finish = useFinish();
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      finish(await api.login(email, password));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Frame title="Welcome back" sub="Sign in to your library.">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        {error && <p className="text-sm text-alarm" role="alert">{error}</p>}
        <button className="btn btn-primary h-11 w-full" disabled={busy}>
          {busy ? "Signing in" : "Sign in"}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate">
        New to Lyra Studio?{" "}
        <Link to="/signup" className="font-medium text-graphite underline underline-offset-4">
          Create an account
        </Link>
      </p>
    </Frame>
  );
}

export function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const finish = useFinish();
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      finish(await api.signup(name, email, password));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Frame title="Create your account" sub="Your songs and images stay on this computer.">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Name" value={name} onChange={setName} autoComplete="name" />
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="new-password" />
        <p className="text-xs text-slate">At least 8 characters.</p>
        {error && <p className="text-sm text-alarm" role="alert">{error}</p>}
        <button className="btn btn-primary h-11 w-full" disabled={busy}>
          {busy ? "Creating account" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-graphite underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </Frame>
  );
}
