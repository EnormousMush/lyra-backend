# Roadmap

## Current status — 2026-04-26

**Working end-to-end.** Backend deployed locally + tunneled via cloudflared, Lovable chat UI live, image generation as a Claude tool fires only when explicitly asked, image content guarded to natural-scene-only.

**Completed milestones:**

| Phase | What | When |
|-------|------|------|
| A | Backend restructure for chat architecture | 2026-04-23 |
| B | Port 4 analysis modules (rhythm, key, dynamics, timbral) | 2026-04-23 |
| C | Streaming chat endpoint with feature-aware system prompt | 2026-04-23 |
| D | Image generation as a Claude tool (Gemini Nano Banana) | 2026-04-25 |
| E | Polish + commit + push v2 backend (commit `3f16838`) | 2026-04-23 |
| F | Lovable chat UI in `seeingmusic-frontend` | 2026-04-26 |

**Known fragilities (from current state):**
- Backend runs on developer's laptop. Cloudflared `trycloudflare.com` URL is ephemeral — changes every restart, breaks the Lovable frontend's hardcoded `BACKEND_URL`.
- Sessions are in-memory and wiped on every code edit (`--reload`) or process restart.
- No auth, no rate limiting — anyone with the URL can burn API credit.
- No error monitoring, no logs beyond uvicorn stdout.
- API keys are still the ones pasted in chat during v1 setup. **Need rotation.**

---

## Next stages (rough — to be formalized)

User-defined plan as of 2026-04-26, in priority order:

1. **Stable backend URL** — real fix (deploy backend), not a band-aid.
2. **Ship and send to potential collaborators.** Find a team.
3. **Expand analysis** — port more modules so Claude has more raw musical data to ground answers on.
4. **Quality control on existing modules** — sanity-check that the metrics we already produce match what experienced ears would say about the same songs.
5. **Expand tool surface** — `find_similar_song` (Spotify API), section/structure detection, audio fingerprinting, others TBD.

A formal action plan with concrete tasks, owners, and ordering will be added below once we work through it together.

> **TODO: insert formalized action plan here.**

---

## Production-readiness checklist

What "official customer-usable website" requires beyond the current dev setup. Items marked **must-have** are blockers for first real users; **later** can wait until there's signal that it matters.

### 1. Hosting + domain

- [ ] **Backend host** (must) — Render ($7/mo starter) or Fly.io for FastAPI + librosa. Avoid AWS/GCP unless there's a reason.
- [ ] **Frontend host** (must) — Lovable can publish, or deploy `seeingmusic-frontend` to Vercel / Netlify (free hobby tier).
- [ ] **Domain name** (must) — ~$10-15/yr from Cloudflare Registrar (cheapest, no markup) or Namecheap.
- [ ] **SSL/DNS** — included free with all of the above.

### 2. Data + state

- [ ] **Database** (must) — Postgres for users + chat history. Supabase or Neon free tier.
- [ ] **Object storage for uploaded audio** (later) — only if songs are kept after analysis. Cloudflare R2 ($0.015/GB, no egress). Currently process-and-discard, which sidesteps this.
- [ ] **Redis / cache** (later) — for chat sessions persistent across backend restarts. Upstash free tier when needed.

### 3. Auth + abuse prevention

- [ ] **User auth** (must) — accounts so usage can be rate-limited per user. Clerk has a generous free tier and ~30 min to integrate. Without auth, one viral tweet drains API credit overnight.
- [ ] **Rate limiting / quota** (must) — e.g. `5 uploads + 50 chat messages per user per day` on free tier.
- [ ] **API budget alarms** (must, today, free) — Anthropic console and Google Cloud both support "email me at $X." Set them to $50 and $200 immediately. Highest-ROI 5 minutes in this list.
- [ ] **Rotate exposed API keys** (must) — the keys pasted in chat during v1 setup are still in `.env`. Rotate before any public deploy.

### 4. Legal + trust

- [ ] **Privacy Policy + Terms of Service** (must) — required anywhere uploads are collected. Termly or Iubenda generate decent ones for ~$10/mo, or DIY by adapting from a similar product.
- [ ] **Copyright / DMCA policy** (later, conditional) — if audio is ever stored. Process-and-discard avoids this. If/when storing: registered DMCA agent ($6 with US Copyright Office) + takedown policy.
- [ ] **Cookie/analytics consent** (later) — only if EU users + tracking analytics are used.

### 5. Operations + product polish

- [ ] **Error monitoring** (must) — Sentry free tier. Without it, bugs are silent until users disappear.
- [ ] **Sanitized error messages** (must) — `/chat` currently leaks Python class names (`AnthropicError: ...`) to the user. Wrap into friendly text in `app/chat.py`.
- [ ] **Mobile-responsive UI** (must) — half the traffic from any tweet is phone.
- [ ] **Lock down CORS** (must) — currently `allow_origins=["*"]`. Restrict to the frontend domain.
- [ ] **Uptime monitoring** (nice) — Better Stack or UptimeRobot free.
- [ ] **Analytics** (nice) — Plausible ($9/mo) or PostHog (free hobby) to see if anyone's actually using it.
- [ ] **CI/CD + tests** (nice) — GitHub Actions free; backend currently has zero tests.
- [ ] **Staging environment** (later) — fine to ship from main while traffic is low.

### 6. Money

- [ ] **Stripe** — only when ready to charge. Free until first transaction.
- [ ] **Pricing model** — defer until users are asking to pay.

### Realistic monthly cost at "small but real" scale

- Render backend: $7
- Domain: $1 amortized
- Database, auth, error monitoring: $0 on free tiers
- Legal docs: $0 (DIY) to $10 (Termly)
- **Fixed infra: ~$10-20/mo**
- Variable Claude + Gemini API: roughly $0.05-0.30 per song-and-chat session. 100 active users × 5 sessions/mo ≈ $25-150/mo.

### What you don't need yet

- A company / LLC (only when charging seriously or taking investment)
- Trademark
- "Real" cloud (AWS/GCP) — Render is fine
- Microservices / Kubernetes / any of that
- A team — solo + Lovable + Claude is enough until there's signal
