# AgroBot — Feature Expansion PRD / TRD
**Scope:** Persistence & Real Analytics · Voice & Multilingual Accessibility · Community/Marketplace & Advisor Roles · Financial Tools
**Base:** Existing AgroBot repo (FastAPI + React, SQLite/Postgres, Groq, XGBoost, CNN, OpenWeatherMap, Tavily)

---

## 0. Why These Four

The current build has real AI plumbing (crop model, disease CNN, LLM recs, scheme search) but three structural weaknesses hold it back from being a genuine farmer product rather than a demo:

1. **Nothing sticks.** Disease results, we ather, added crops, and analytics are ephemeral or hardcoded — so the app can't show a farmer their own history or prove ROI.
2. **It assumes literacy and English/Hindi UI text only** — most of the target user base (small/medium farmers) will not comfortably use a text-heavy dashboard.
3. **It's a single-user tool with no loop back to money or people** — no way to act on a scheme recommendation, track a loan, sell surplus produce, or get a human (field officer) involved when the AI isn't enough.

These four workstreams are ordered to fix that, roughly in build order: persistence unlocks everything else (analytics, financial tracking, and advisor visibility all need real stored data); voice/multilingual removes the adoption barrier; community/marketplace and financial tools are the retention and monetization layer on top.

---

## 1. Persistence & Real Analytics

### 1.1 Problem
`recommendations`, `questionnaire_responses`, and `users` are the only real tables. Disease predictions, weather snapshots, dashboard-added crops, and all Analytics page metrics are either request-time-only or hardcoded in the frontend. This means: no farm health trend over time, no proof that a recommendation was acted on, and an Analytics screen that lies to the user.

### 1.2 Goals
- Every AI output (disease check, weather pull, recommendation) becomes a durable, queryable record tied to a user and a farm/plot.
- Analytics is computed from real rows, not fixtures.
- Support multiple plots per user (a farmer with two fields shouldn't share one soil profile).

### 1.3 User Stories
- As a farmer, I want to see my last 10 disease checks so I can tell if a problem is recurring.
- As a farmer, I want a chart of my farm health score over the season, not just today's number.
- As a farmer, I want the crop I added on my dashboard to still be there tomorrow.
- As an advisor, I want to see a farmer's history, not just their latest snapshot.

### 1.4 Functional Requirements
| ID | Requirement |
|---|---|
| PA-1 | New `farms` table; a user can own 1..N farms; questionnaire responses and recommendations become farm-scoped, not just user-scoped |
| PA-2 | Persist every `/api/disease/predict` call: image ref, predicted class, confidence, treatment text, farm_id, created_at |
| PA-3 | Persist every weather lookup as a daily snapshot per farm (dedupe by farm+date) instead of ad hoc calls |
| PA-4 | Persist user-added dashboard crops (currently React state only) to a `farm_crops` table |
| PA-5 | Analytics endpoint aggregates real data: soil score trend, disease-check frequency, crop mix over time, recommendation adoption rate |
| PA-6 | Backfill-safe migration — existing single-farm users get one auto-created `farms` row so nothing breaks |

### 1.5 TRD

**Schema additions** (`backend/app/database/schemas.py`):
```
farms
  id, user_id (FK), name, location, area_acres, created_at

disease_predictions
  id, farm_id (FK), image_path, predicted_class, confidence,
  treatment_text, source ("cnn"|"cnn+groq_vision"), created_at

weather_snapshots
  id, farm_id (FK), date, source ("openweather"|"mock"),
  temp, humidity, rainfall_mm, raw_json, created_at

farm_crops
  id, farm_id (FK), crop_name, added_by ("user"|"recommendation"),
  status ("active"|"harvested"|"removed"), added_at
```
`questionnaire_responses` and `recommendations` gain a `farm_id` FK (nullable during migration, backfilled to the auto-created default farm).

**New/changed endpoints:**
| Method | Path | Change |
|---|---|---|
| POST | `/api/farms` | Create a farm (new) |
| GET | `/api/farms` | List user's farms (new) |
| POST | `/api/disease/predict` | Now writes to `disease_predictions` |
| GET | `/api/disease/history?farm_id=` | New — returns past checks |
| GET | `/api/weather/current` | Now writes/reads `weather_snapshots` (cache-first, avoids re-hitting OpenWeatherMap same day) |
| GET | `/api/analytics/overview?farm_id=` | New — replaces the frontend's hardcoded metrics |
| POST/DELETE | `/api/dashboard/crops` | New — replaces client-only `CropMonitor.jsx` state |

**Migration approach:** Add Alembic (currently the repo uses `create_all`, flagged as a known gap). Write one migration per table above, plus a data-migration script that creates a default `farms` row per existing user and backfills `farm_id` on existing `questionnaire_responses`/`recommendations` rows.

**Frontend changes:** `Analytics.jsx` switches from static constants to `GET /api/analytics/overview`; `CropMonitor.jsx` switches from local `useState` to API-backed CRUD; add a lightweight farm switcher if `farms.length > 1`.

---

## 2. Voice & Multilingual Accessibility

### 2.1 Problem
Hindi/English toggle exists only inside Disease Checkup and Government Schemes, not globally, and the whole product assumes comfortable reading. For the stated target user (farmers who "may not know soil NPK/pH values"), a text-only form-heavy questionnaire is a real adoption barrier.

### 2.2 Goals
- Global i18n, not screen-by-screen text swapping.
- Voice input for the questionnaire and disease checkup ("speak your answer" instead of typing/selecting where feasible).
- Voice output (TTS) for recommendations and disease treatment text, so results can be *heard*, not just read.

### 2.3 User Stories
- As a farmer with limited reading ability, I want to answer the questionnaire by speaking instead of typing.
- As a farmer, I want to hear my disease diagnosis and treatment read aloud in Hindi.
- As a user, I want the entire app — not just two screens — in my chosen language.

### 2.4 Functional Requirements
| ID | Requirement |
|---|---|
| VA-1 | Introduce a proper i18n layer covering every screen (Home, Login, Signup, Questionnaire, Dashboard, Analytics), not just Disease/Schemes |
| VA-2 | Voice input on questionnaire free-text/numeric fields via speech-to-text, with the recognized text shown for confirmation before submit |
| VA-3 | Voice input on Disease Checkup ("describe what you see") as an alternative/supplement to image upload |
| VA-4 | Text-to-speech playback for: recommendation summary, disease result + treatment, scheme eligibility summary |
| VA-5 | Language preference stored per user, applied on every screen and to TTS voice selection |
| VA-6 | Graceful degradation: if mic/audio permissions are denied, fall back to existing text UI with no functional loss |

### 2.5 TRD

**i18n:** Adopt `react-i18next` on the frontend; move all hardcoded UI strings into `en.json`/`hi.json` resource bundles (this replaces the current per-component conditional text seen in `DiseaseCheckup.jsx`/`GovernmentSchemes.jsx`). Backend adds `preferred_language` to `users` and returns LLM-generated text (recommendations, disease treatment, scheme summaries) in that language by instructing Groq's prompt accordingly — cheaper and more consistent than translating after generation.

**Speech-to-text:** Use Groq's Whisper-family audio endpoint (already have a Groq relationship in this codebase) for STT — record short audio clips client-side, POST to a new `/api/voice/transcribe` endpoint, return transcript for the frontend to populate the relevant field.

**Text-to-speech:** Browser-native `SpeechSynthesis` Web API for MVP (zero backend cost, works for Hindi/English voices on most Android/Chrome devices — relevant since target users skew mobile). Revisit a cloud TTS provider only if voice quality complaints surface.

**New endpoint:**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/voice/transcribe` | Accepts audio blob, returns transcript via Groq Whisper |
| PATCH | `/api/users/me/language` | Set preferred language |

**Data model:** `users.preferred_language` (default `"en"`).

**Non-functional:** Audio clips are transient (not persisted) unless the user explicitly opts into "save voice note" for advisor review (ties into Section 3). Keep STT clip length capped (~30s) to control Groq usage cost.

---

## 3. Community / Marketplace + Advisor Roles

### 3.1 Problem
AgroBot is currently one-directional: AI to farmer, no human in the loop, no farmer-to-farmer interaction, and no path from "I have surplus tomatoes" to a buyer. The TPC-coordinator-style pattern of "a human role that sees more than an individual user" doesn't exist at all yet — everything is scoped to a single farmer's own data.

### 3.2 Goals
- Introduce an **advisor/field officer role** that can view (not edit) a set of farmers' profiles, history, and flag disease outbreaks across their assigned farmers.
- Introduce a lightweight **marketplace**: farmers list surplus produce, other farmers/buyers browse and contact.
- Introduce a **community Q&A/forum** scoped by region, so farmers can ask each other (not just the AI) questions.

### 3.3 User Stories
- As a field officer, I want a list of my assigned farmers with their latest soil score and any recent disease flags, so I know who needs a visit.
- As a farmer, I want to list 50kg of surplus onions and see interested buyers contact me.
- As a farmer, I want to ask "has anyone else in my district seen this leaf spot?" and see replies from nearby farmers.

### 3.4 Functional Requirements
| ID | Requirement |
|---|---|
| CM-1 | New `role` field on users: `farmer` (default), `advisor`, `admin` |
| CM-2 | Advisor dashboard: list of assigned farmers, each farm's latest soil score, disease-check count in last 30 days, unresolved disease flags |
| CM-3 | Assignment model: advisor ↔ farmer many-to-many (an advisor covers a region/set of farmers; a farmer can have one primary advisor) |
| CM-4 | Marketplace: farmer creates a listing (crop, quantity, price, location, contact preference); browsable/filterable by other users; no in-app payment for MVP — just discovery + contact |
| CM-5 | Community forum: post + reply, scoped by district/region (derived from farm location), optionally tagged with crop type |
| CM-6 | Basic moderation: report post/listing, admin can hide |

### 3.5 TRD

**Schema additions:**
```
advisor_farmer_links
  id, advisor_id (FK users), farmer_id (FK users), assigned_at

marketplace_listings
  id, farmer_id (FK), crop_name, quantity, unit, price,
  location, contact_pref, status ("active"|"closed"), created_at

forum_posts
  id, user_id (FK), region, crop_tag, title, body, created_at

forum_replies
  id, post_id (FK), user_id (FK), body, created_at

reports
  id, target_type ("listing"|"post"|"reply"), target_id,
  reported_by (FK), reason, status ("open"|"resolved"), created_at
```
`users.role` added (enum, default `farmer`).

**Auth/RBAC:** Extend the existing JWT auth (`auth.py`) with a role claim; add a `require_role()` FastAPI dependency for advisor/admin-only routes. No new auth system needed — this is additive to what's already there.

**New endpoints:**
| Method | Path | Notes |
|---|---|---|
| GET | `/api/advisor/farmers` | Advisor-only; requires role check |
| GET | `/api/advisor/farmers/{id}/summary` | Farm history rollup for one assigned farmer |
| POST | `/api/marketplace/listings` | Create listing |
| GET | `/api/marketplace/listings` | Browse/filter by crop, location, price |
| POST | `/api/forum/posts`, `/api/forum/posts/{id}/replies` | Community Q&A |
| POST | `/api/reports` | Report content |

**Frontend:** New route group under an `/advisor` prefix, gated by role in `AuthContext.js`. New `Marketplace.jsx` and `Community.jsx` screens, reusing the existing card/list UI patterns already established in `GovernmentSchemes.jsx`.

**Phasing note:** Ship advisor dashboard first (it only needs read access to data that Section 1 already makes persistent) — marketplace and forum are independently shippable after.

---

## 4. Financial Tools

### 4.1 Problem
Government Schemes currently *finds and summarizes* schemes via Tavily but stops there — there's no way to track "I applied," no eligibility persistence, and recommendations never connect to actual profitability (the LLM outputs a "profitability score" per the PRD, but nothing tracks realized outcomes).

### 4.2 Goals
- Let farmers track which schemes they've applied to and status.
- Basic loan/subsidy calculator (EMI, subsidy-adjusted cost) for common agri-loan scenarios.
- Close the loop between recommended crop profitability estimates and what the farmer actually reports back at harvest.

### 4.3 User Stories
- As a farmer, I want to mark a scheme as "applied" and note the date, so I can follow up later.
- As a farmer, I want to see estimated EMI for a loan amount before I apply.
- As a farmer, I want to log what I actually earned from a harvest so future recommendations improve.

### 4.4 Functional Requirements
| ID | Requirement |
|---|---|
| FT-1 | Persist scheme results (currently ephemeral Tavily+Groq output) so a farmer can revisit and act on them |
| FT-2 | Application tracker: status per scheme per farmer (`saved` → `applied` → `approved`/`rejected`) with optional notes/date |
| FT-3 | Loan/subsidy calculator: input principal, tenure, interest rate, subsidy % → output EMI and net cost; no external bank integration for MVP |
| FT-4 | Harvest outcome logging: farmer reports actual yield + sale price against a `farm_crops` entry (from Section 1); used to compute realized profitability vs. predicted |
| FT-5 | Advisor (Section 3) can view a farmer's scheme application status and harvest outcomes as part of the farmer summary |

### 4.5 TRD

**Schema additions:**
```
scheme_records
  id, farm_id (FK), scheme_name, source_url, summary,
  eligibility_text, status ("saved"|"applied"|"approved"|"rejected"),
  applied_at, notes, created_at

harvest_outcomes
  id, farm_crop_id (FK farm_crops), actual_yield, unit,
  sale_price_per_unit, harvested_at, notes, created_at
```

**Loan calculator:** Stateless computation, no persistence needed beyond optional "save this scenario" — standard EMI formula `EMI = P × r × (1+r)^n / ((1+r)^n − 1)`, subsidy simply reduces effective principal before the calc. Ship as a pure frontend calculator (no backend round-trip needed) unless you want saved scenarios, in which case add a thin `POST /api/finance/loan-scenarios` table.

**New endpoints:**
| Method | Path | Notes |
|---|---|---|
| POST | `/api/schemes/{id}/save` | Persist a Tavily/Groq scheme result the farmer wants to track |
| PATCH | `/api/schemes/records/{id}` | Update status/notes |
| GET | `/api/schemes/records?farm_id=` | List tracked schemes |
| POST | `/api/harvest-outcomes` | Log actual yield/sale price |
| GET | `/api/analytics/profitability?farm_id=` | Compares predicted (from `recommendations`) vs. realized (from `harvest_outcomes`) |

**Dependency on Section 1:** This entire module assumes `farms` and `farm_crops` exist — sequence it after Persistence & Analytics.

---

## 5. Cross-Cutting Concerns

- **Migrations:** Introduce Alembic now (already flagged as a gap in the current repo) rather than continuing with `create_all` — every table above needs a real migration path, especially given the `farm_id` backfill in Section 1.
- **Env/config resilience:** The existing issue where `TAVILY_API_KEY`/`GROQ_API_KEY` missing can block backend startup should be fixed *before* adding Section 4, since scheme tracking depends on that service being reliably up.
- **Security:** Financial data (Section 4) and advisor cross-farmer visibility (Section 3) both raise the stakes on auth — this is the point to add rate limiting and audit logging (who viewed which farmer's data) if not already present.
- **Mobile-first:** Given the target user skews rural/mobile and Section 2 leans on browser STT/TTS, test primarily against Chrome-on-Android, not desktop.

## 6. Suggested Build Order

1. **Persistence & Real Analytics** (Section 1) — unblocks everything else, fixes existing known gaps.
2. **Voice & Multilingual** (Section 2) — independent, highest adoption impact, can run in parallel with #1.
3. **Advisor role only**, from Section 3 — needs #1's persisted data, ship before marketplace/forum.
4. **Financial Tools** (Section 4) — needs #1's `farm_crops`.
5. **Marketplace + Forum**, remainder of Section 3 — lowest dependency risk, ship last as it's the most "new surface area" rather than fixing/extending existing flows.

---

*Scope note: this document intentionally excludes IoT sensor integration (mentioned in the README but not implemented) — flag if you want that added as a fifth workstream.*