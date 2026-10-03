export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: "same-origin", ...init });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg)
        message = String(body.detail[0].msg).replace(/^Value error, /, "");
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export interface User {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  created_at: string;
}

export interface Policy {
  invite_only: boolean;
  daily_uploads: number;
  daily_images: number;
}

export interface Usage {
  uploads: { used: number; limit: number | null };
  images: { used: number; limit: number | null };
  resets_at: string;
}

export interface Invite {
  code: string;
  note: string | null;
  created_at: string;
  expires_at: string | null;
  used_by: string | null;
  used_at: string | null;
}

export interface CatalogEntry {
  label: string;
  unit: string;
  group: string;
  fmt: number;
  explain: string;
}

export interface Meta {
  version: string;
  styles: { id: string; label: string; description: string }[];
  aspects: string[];
  catalog: Record<string, CatalogEntry>;
  groups: string[];
  services: {
    claude: { live: boolean; model: string; key_present: boolean };
    images: { live: boolean; model: string; key_present: boolean };
  };
  atlas: AtlasStatus;
}

export interface AtlasStatus {
  profiles_ready: boolean;
  n_songs_with_features: number;
  built_at: string | null;
  source_csv: string | null;
}

export type Stage = "queued" | "decoding" | "features" | "structure" | "listening" | "ready" | "error";

export interface TrackSummary {
  id: string;
  title: string;
  filename: string;
  stage: Stage;
  error: string | null;
  duration_s: number | null;
  created_at: string;
  headline: string | null;
  palette: string[];
  tempo: number | null;
  key: string | null;
  cover_url: string | null;
  image_count: number;
}

export interface Section {
  index: number;
  start: number;
  end: number;
  label: string;
  group: string;
  energy: number;
  loudness_rel_db: number;
  brightness_hz: number;
}

export interface ReadoutRow extends CatalogEntry {
  key: string;
  value: number;
}

export interface FactorShare {
  value: string;
  share: number;
}

export interface Dna {
  source: "data" | "estimate";
  factors: Record<"genre" | "subgenre" | "mood" | "descriptor", FactorShare[]>;
  prompt: string;
  prompt_parts?: { genre: string; subgenre: string; mood: string; descriptor: string };
  confidence: number;
  reasoning?: string;
  nearest_prompts: { prompt: string; genre: string; distance: number }[];
  k?: number;
  pool?: number;
  reliability?: Record<string, { accuracy: number; chance: number; classes: number }>;
}

export interface Listening {
  headline: string;
  summary: string;
  motifs: string[];
  palette: { hex: string; name: string }[];
  evidence: { feature: string; observation: string }[];
  mock?: boolean;
}

export type Mode = "cover" | "scenes" | "variation";

export interface Generation {
  id: string;
  track_id: string;
  batch_id: string;
  mode: Mode;
  style: string;
  aspect: string;
  direction: string | null;
  section_index: number | null;
  parent_id: string | null;
  status: "planning" | "rendering" | "done" | "error";
  error: string | null;
  title: string | null;
  prompt: string | null;
  rationale: string | null;
  palette: string[] | null;
  mock: boolean;
  favorite: boolean;
  image_url: string | null;
  created_at: string;
  track_title?: string;
}

export interface TrackDetail extends TrackSummary {
  features: Record<string, any>;
  readout: ReadoutRow[];
  percentiles: Record<string, number>;
  sections: Section[];
  waveform: number[];
  dna: Dna | null;
  listening: Listening | null;
  generations: Generation[];
}

export interface GenerateBody {
  mode: Mode;
  style: string;
  aspect: string;
  direction?: string;
  count?: number;
  sections?: number[];
  parent_id?: string;
  people?: boolean;
}

export interface AtlasProfile {
  n: number;
  means: Record<string, number>;
  d: Record<string, number>;
  top: { key: string; d: number }[];
}

export interface AtlasPayload {
  status: AtlasStatus;
  vocabulary: {
    genre: { value: string; prompts: number; songs: number }[];
    subgenre: { value: string; prompts: number; songs: number }[];
    mood: { value: string; prompts: number; songs: number }[];
    descriptor: { value: string; prompts: number; songs: number }[];
    by_genre: Record<string, { subgenres: string[]; moods: string[]; descriptors: string[] }>;
    totals: { prompts: number; unique_prompts: number; songs: number };
  };
  profiles: null | {
    meta: { n_songs: number; built_at: string; source: string };
    features: ({ key: string } & CatalogEntry)[];
    global: Record<string, { mean: number; std: number; median: number }>;
    profiles: Record<"genre" | "subgenre" | "mood" | "descriptor", Record<string, AtlasProfile>>;
  };
}

export const api = {
  me: () => request<User>("/api/auth/me"),
  login: (email: string, password: string) => request<User>("/api/auth/login", json("POST", { email, password })),
  signup: (name: string, email: string, password: string, invite?: string) =>
    request<User>("/api/auth/signup", json("POST", { name, email, password, invite })),
  policy: () => request<Policy>("/api/auth/policy"),
  usage: () => request<Usage>("/api/usage"),
  invites: () => request<Invite[]>("/api/auth/invites"),
  createInvite: (note: string) => request<Invite>("/api/auth/invites", json("POST", { note, days: 30 })),
  revokeInvite: (code: string) => request<{ ok: boolean }>(`/api/auth/invites/${code}`, { method: "DELETE" }),
  deleteTrack: (id: string) => request<{ ok: boolean }>(`/api/tracks/${id}`, { method: "DELETE" }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  updateMe: (name: string) => request<User>("/api/auth/me", json("PATCH", { name })),
  changePassword: (current: string, next: string) =>
    request<{ ok: boolean }>("/api/auth/password", json("POST", { current, new: next })),

  meta: () => request<Meta>("/api/meta"),
  tracks: () => request<TrackSummary[]>("/api/tracks"),
  track: (id: string) => request<TrackDetail>(`/api/tracks/${id}`),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<TrackSummary>("/api/tracks", { method: "POST", body: fd });
  },
  rename: (id: string, title: string) => request<TrackSummary>(`/api/tracks/${id}`, json("PATCH", { title })),
  reanalyze: (id: string) => request<TrackSummary>(`/api/tracks/${id}/reanalyze`, { method: "POST" }),
  generate: (id: string, body: GenerateBody) =>
    request<{ batch_id: string; generations: Generation[] }>(`/api/tracks/${id}/generate`, json("POST", body)),
  gallery: (favorites = false) => request<Generation[]>(`/api/generations${favorites ? "?favorites=true" : ""}`),
  favorite: (id: string, favorite: boolean) =>
    request<Generation>(`/api/generations/${id}/favorite`, json("POST", { favorite })),
  atlas: () => request<AtlasPayload>("/api/atlas"),
};
