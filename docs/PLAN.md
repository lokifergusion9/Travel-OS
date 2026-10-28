# TravelOS — AI-Powered Multi-Tenant Travel CRM & Operations Platform

## Context

Chhoti travel agencies (1–2 log) jab koi naya trek/trip launch karte hain to ek lamba manual
pipeline chalta hai: itinerary banao → posters/videos/docs banao → hotels dhoondho aur deal
karo → transport companies se deal close karo → Insta/WhatsApp pe post karo → ads chalao →
leads aate hain → leads manage karo, auto-followup karo, deal close karo. Sab manual, bikhra
hua, aur leads handle karna sabse bada dard hai.

**TravelOS** ek single operating system hai jo is pure lifecycle ko AI agents + ek CRM ke
through chalata hai — **har critical step pe human-in-the-loop** (agent draft banata hai, human
approve karta hai). Multi-tenant: har agency apna isolated workspace.

**Goal:** Ek aisa system jisme ek 2-person agency pura trip operations + lead funnel ek hi
clean, animated dashboard se chala sake.

**Constraints (user-confirmed):**
- LLM/image = **free-tier first** (Gemini + Groq + Pollinations). Pluggable rakhenge taaki baad me paid pe swap ho.
- **Multi-tenant abhi se** (har row pe `tenant_id`, isolation day 1 se).
- CRM messaging: **Email/SMS pehle, WhatsApp Cloud API Phase 2 me**.
- Frontend = React + TS + Vite + heavy motion. Backend = FastAPI + LangGraph. Deploy = Docker → AWS.

---

## Tech Stack (free-first, pluggable)

| Layer | Choice | Why / Free-tier note |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite | User-specified template |
| UI / styling | Tailwind CSS + shadcn/ui | Clean, composable |
| Motion | **Framer Motion (`motion`)** + Lenis (smooth scroll) | Pure system me motion — page transitions, onboarding, card stagger |
| State/data | TanStack Query + Zustand | Server cache + light client state |
| Backend | **FastAPI** (async) + Pydantic v2 | User-specified |
| Agents | **LangGraph** + LangChain | Stateful multi-agent graphs w/ interrupts (HITL) |
| LLM (text) | **Google Gemini 2.5/2.0 Flash** free tier (1,500 req/day, 1M TPM, no card) — primary; **Groq Llama-3.3-70B** (fast, 30 RPM) for quick CRM replies | Provider abstraction layer so swap is config-only |
| Image (posters) | **Gemini 2.5 Flash Image "Nano Banana"** (~500 req/day free); **Pollinations** (no-key) as fallback | |
| DB | **PostgreSQL 16** (Row-Level Security for tenant isolation) | |
| Cache/queue | **Redis** + (Celery or ARQ) for async agent jobs, scheduled followups | |
| Object storage | Local volume (dev) → **AWS S3** (prod) for posters/docs/videos | |
| Auth | JWT (access+refresh), bcrypt; tenant-scoped | |
| Email | **Resend** (3k/mo free) or **Brevo** (300/day free) | |
| SMS | Dev: console/mock sender; Prod India: MSG91/Fast2SMS (cheap, paise/msg) | |
| Vector store (RAG) | **pgvector** in same Postgres | Hotel/destination knowledge, past itineraries |
| Infra | Docker Compose (dev) → AWS ECS Fargate + RDS + ElastiCache + S3 (prod) | |

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  React + Vite SPA (Framer Motion)                                │
│  Onboarding · Dashboard · Trip Builder · Creative Studio ·       │
│  Sourcing Board · Leads/CRM · Inbox · Settings                   │
└───────────────┬────────────────────────────────────────────────┘
                │ REST + SSE/WebSocket (live agent status, inbox)
┌───────────────▼────────────────────────────────────────────────┐
│  FastAPI Gateway  (JWT auth · tenant middleware · RBAC)          │
│  ┌──────────────┬───────────────┬──────────────┬─────────────┐  │
│  │ Trip module  │ Creative mod. │ Sourcing mod.│ CRM module  │  │
│  └──────┬───────┴───────┬───────┴──────┬───────┴──────┬──────┘  │
│         │  LangGraph Agent Orchestrator (per-tenant state)       │
│  ┌──────▼──────────────────────────────────────────────────┐    │
│  │ Itinerary · Creative · Hotel · Transport · Lead/Followup │    │
│  │ agents — each graph has HITL interrupt nodes (approve)   │    │
│  └─────────────────────────────────────────────────────────┘    │
│  Redis (jobs, schedules) · Postgres+pgvector · S3                │
└───────────────┬────────────────────────────────────────────────┘
                │ Webhooks / outbound
   Meta Lead Ads webhook → leads | Instagram Graph publish | Email/SMS → (WhatsApp P2)
```

**HITL pattern (core to whole system):** Har agent LangGraph graph me ek `interrupt()` /
approval node hota hai. Agent kaam karke ek **draft** (itinerary, poster, message, deal-email)
banata hai → status `pending_review` → UI me human edit/approve/reject → approve pe hi agent
aage badhta hai (publish/send). Approvals ek common `approvals` table + UI "Approval Center" se.

---

## Multi-Tenancy Design (Day 1)

- Har table me `tenant_id UUID NOT NULL` (FK → `tenants`).
- **Postgres Row-Level Security (RLS)**: connection pe `SET app.current_tenant = '<id>'`;
  policies har row ko tenant ke hisaab se filter karti hain → application bug se bhi cross-tenant
  leak nahi.
- FastAPI dependency `get_current_tenant()` JWT se tenant nikaalta hai, har request pe RLS var set.
- `users` ↔ `tenants` many-to-one (ek agency = ek tenant, usme 1–2 users). Roles: `owner`, `member`.
- Per-tenant secrets (Meta tokens, email/SMS keys) encrypted at rest (`integration_credentials`, Fernet).

---

## Modules & Agents

### Module 1 — Trip / Itinerary Builder
- **Itinerary Agent (LangGraph):** input = destination, days, budget, audience, season → RAG over
  past itineraries + destination KB (pgvector) → day-by-day itinerary draft (places, stay type,
  transport legs, costing). HITL approve → saved as `Trip`.
- UI: "Trip Builder" — form → live streaming generation → editable day cards (drag to reorder,
  animated) → approve.
- Tables: `trips`, `itinerary_days`, `trip_costing`.

### Module 2 — Creative Studio (posters / captions / docs / video)
- **Creative Agent:** trip se context lekar — (a) poster image prompts → Gemini Flash Image /
  Pollinations, (b) Insta/WhatsApp captions + hashtags, (c) brochure/PDF doc (HTML→PDF via
  WeasyPrint), (d) Phase-3: short reel script + slideshow video (ffmpeg + stock/poster frames).
- HITL: generated assets → review grid → regenerate/edit/approve.
- Tables: `creative_assets` (type, url, status), `asset_variants`.

### Module 3 — Sourcing (Hotels + Transport)
- **Hotel Agent & Transport Agent:** itinerary ke legs se requirements nikaalo → vendor list
  (per-tenant `vendors` table; seedable) → personalized outreach **email/message draft** with
  rate-ask → HITL approve → send → replies inbox me thread ho → agent deal terms summarize kare,
  human "close" kare.
- *Note:* live hotel-price scraping/booking APIs out-of-scope MVP (legal/keys). Focus = outreach +
  deal tracking + manual confirm. Optional later: Booking/Agoda affiliate, Amadeus self-service.
- Tables: `vendors`, `sourcing_requests`, `vendor_threads`, `deals`.

### Module 4 — Publishing (Instagram / WhatsApp broadcast)
- **Instagram Graph API** (Business/Creator acct + linked FB Page): approved poster + caption →
  Content Publishing API (`/media` → `/media_publish`). Limits: ~25–100 posts/24h, 200 calls/hr per acct.
- Per-tenant Meta OAuth connect flow in Settings. Token storage encrypted.
- WhatsApp broadcast = **Phase 2** (Cloud API, templates pre-approved, per-msg cost).
- Tables: `social_accounts`, `scheduled_posts`, `post_results`.

### Module 5 — CRM + Leads (the core pain)
- **Lead ingestion:** Meta **Lead Ads webhook** (`leadgen` field) → real-time lead → `leads`
  (source=meta). Also manual add + web form capture endpoint.
- **Lead/Followup Agent:** new lead pe → auto first-touch (Email/SMS) using approved templates →
  scheduled multi-step followup sequence (Redis/Celery beat) → reply aane pe agent intent samjhe
  (interested / price / dates / not now) aur next action suggest kare → HITL for anything sent.
- **Pipeline (Kanban):** New → Contacted → Interested → Negotiation → Won/Lost (animated drag).
- **Auto-followup safety:** every outbound respects HITL mode toggle (auto-send vs draft-only).
- Tables: `leads`, `lead_activities`, `message_templates`, `followup_sequences`, `conversations`, `messages`.

### Cross-cutting — Approval Center, Notifications, Audit
- `approvals` table feeds a global Approval Center (animated queue).
- SSE/WebSocket stream → live agent progress + new-lead toasts.
- `audit_log` per tenant (who approved/sent what).

---

## Repository Structure (monorepo)

```
TravelOS/
├── frontend/                 # React + Vite (existing template base)
│   └── src/{app,components,features,lib,hooks,motion,api}
├── backend/
│   └── app/
│       ├── main.py  core/(config,security,db,rls)  api/v1/
│       ├── modules/{trips,creative,sourcing,publishing,crm}/
│       ├── agents/{itinerary,creative,hotel,transport,lead}/  (LangGraph graphs)
│       ├── agents/llm/        # provider abstraction (gemini, groq, image)
│       ├── integrations/{meta,email,sms,storage}/
│       ├── workers/           # Celery/ARQ tasks + beat schedules
│       └── models/  schemas/  migrations/(alembic)
├── docker-compose.yml         # postgres, redis, backend, worker, frontend
├── infra/                     # AWS (ECS task defs / terraform later)
└── docs/  (this plan, ADRs, API)
```

---

## Phase Plan

### Phase 0 — Foundation (skeleton + multi-tenant + onboarding)
- Monorepo + Docker Compose (postgres+pgvector, redis, backend, worker, frontend).
- Backend: FastAPI app, config, Postgres + Alembic, **RLS multi-tenant** base, JWT auth.
- LLM provider abstraction (`LLMProvider` interface → GeminiProvider, GroqProvider, ImageProvider).
- Frontend: Vite + Tailwind + shadcn + Framer Motion setup; **animated onboarding flow**
  (welcome → create agency/tenant → invite/role → connect-later integrations) + dashboard shell
  with route transitions.
- Deliverable: signup → tenant create → land on empty animated dashboard.

### Phase 1 — Trip + Creative (content engine)
- Itinerary Agent (LangGraph + Gemini, streaming) + Trip Builder UI + HITL approve.
- Creative Agent: posters (Gemini Flash Image/Pollinations) + captions + PDF brochure + Creative
  Studio review grid.
- Approval Center v1.

### Phase 2 — CRM + Leads (core value)
- Lead model + Meta Lead Ads webhook + manual/web-form capture.
- Lead/Followup Agent + Email/SMS senders + templates + scheduled sequences (worker/beat).
- Kanban pipeline + unified inbox (conversations/threads) + live SSE toasts.

### Phase 3 — Sourcing + Publishing
- Hotel/Transport agents + vendor outreach + deal tracking board.
- Instagram Graph publishing (Meta OAuth connect, schedule posts, results).

### Phase 4 — Advanced + Scale
- WhatsApp Cloud API (templates, broadcast, 2-way inbox).
- Video/reel generation. Analytics dashboard (lead→conversion, ad ROI). RAG knowledge base growth.

### Phase 5 — AWS Production
- Containerize all; ECS Fargate (backend+worker), RDS Postgres+pgvector, ElastiCache Redis, S3,
  CloudFront for frontend, Secrets Manager, ALB, CI/CD (GitHub Actions). Per-tenant rate-limit & cost guards.

---

## Key Integration Notes (researched, June 2026)
- **Instagram publishing** needs Business/Creator account **+ linked Facebook Page**; personal
  accounts can't use Graph API. v21.0. Limits ~25–100 published/24h, 200 calls/hr/account. App
  review needed for production permissions → start in Dev mode with test accounts.
- **Meta Lead Ads:** subscribe app to `leadgen` webhook field; Page must have app installed; leads
  arrive real-time as JSON (`leadgen_id`, `form_id`, `ad_id`) → fetch full lead via Graph API.
- **WhatsApp Cloud API (Phase 2/4):** per-message billing (~₹0.7/marketing msg India), templates
  need pre-approval, 24h (72h via click-to-WA ads) free service window, 80 msg/s default.
- **Free LLM reality:** Gemini free = 1,500 req/day (training-on-prompts allowed on free tier — flag
  to user for sensitive data). Build provider abstraction + caching + queue to stay within limits;
  Groq for low-latency CRM replies. Image free via Gemini Flash Image (~500/day) + Pollinations fallback.

---

## Verification (per phase)
- `docker compose up` → all services healthy; `/health` + `/docs` (OpenAPI) reachable.
- **Multi-tenant test:** create 2 tenants, confirm tenant A can't read tenant B's trips/leads
  (RLS unit + integration test).
- Phase 1: create trip → itinerary streams → approve → generate poster → appears in Studio.
- Phase 2: POST mock Meta webhook → lead appears → followup agent drafts message → approve →
  email/SMS sent (mock sender logs) → reply simulated → pipeline card moves.
- Phase 3: connect IG test account → schedule post → media_publish succeeds (dev).
- Agent tests: LangGraph graphs unit-tested with `interrupt` resume; pytest for APIs; Vitest +
  Playwright for frontend flows/motion smoke.

## Open Decisions (Phase 0 me confirm karenge)
- Exact email/SMS vendor keys (Resend vs Brevo; MSG91 vs mock for SMS).
- Onboarding ke baad pehla "wow" screen kaisa ho (empty-state animation direction).

## Sources
- [Instagram Graph API 2026 guide](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/) ·
  [Phyllo integration/limits](https://www.getphyllo.com/post/instagram-api-integration-101-for-developers-of-the-creator-economy)
- [Meta Lead Ads webhooks](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/) ·
  [Lead Ads integration guide](https://leadsync.me/blog/facebook-lead-ads-integration-ultimate-guide/)
- [WhatsApp Cloud API pricing 2026](https://blueticks.co/blog/whatsapp-business-api-pricing-2026) ·
  [Meta pricing docs](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- [Gemini free tier](https://tokenmix.ai/blog/gemini-api-free-tier-limits) ·
  [Groq free tier](https://tokenmix.ai/blog/groq-free-tier-limits-2026) ·
  [Gemini image free / Pollinations](https://blog.laozhang.ai/en/posts/gemini-image-generation-free-limit-2026)
