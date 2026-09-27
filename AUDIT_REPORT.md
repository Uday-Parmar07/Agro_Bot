# AgroBot — Pre-Production Audit

**Date:** 2026-09-27
**Scope:** `/Users/uday/Development/Agro-Bot` @ `b015ba4` (working tree, which differs substantially from HEAD — see F-24)
**Method:** static read-through of all backend/frontend source, `pip-audit`, `npm audit`, `git log -p` secret scan, test-suite execution. No code was modified.

---

## 0. Architecture summary

AgroBot is a single-container FastAPI + React app for Indian farmers. `agrobot-assistant/backend/app/main.py` mounts 13 routers under `/api/*` and serves the CRA build from a catch-all route, so one process is both API and static host. Auth is email/password → bcrypt (passlib) → a 7-day HS256 JWT (`app/utils/auth_utils.py`); the token carries `sub` (email) and `role`, but authorisation always re-reads `role` from the DB. Persistence is SQLAlchemy ORM against Neon Postgres in production (SQLite locally), with Alembic migrations run **from the app's own startup hook**.

Every farmer owns one or more `Farm` rows; nearly all data (`questionnaire_responses`, `recommendations`, `disease_predictions`, `weather_snapshots`, `farm_crops`, `scheme_records`) hangs off `farm_id`, and ownership is enforced through `farm_service.get_user_farm()` / `get_existing_user_farm()`. That pattern is applied consistently — I found no IDOR.

The product has four external-data features: (1) **crop recommendation** — an XGBoost model (`artifacts/xgboost_crop_model.joblib`, 22 classes) plus a JSON "crop catalogue" knowledge lane, ranked by `crop_ranking_service`, validated by `crop_validation_service`, then narrated by Groq Llama with a strict allow-list; (2) **disease detection** — a 15-class PyTorch CNN over uploaded leaf photos, optionally enriched by a Groq vision model; (3) **mandi prices** — the data.gov.in Agmarknet API, cached in `mandi_price_snapshots`; (4) **government schemes / market news** — Tavily web search over `gov.in` domains, summarised by Groq.

**Trust boundaries:** every `/api` route (all authenticated except `/api/auth/*` and `/api/health`); two multipart upload endpoints (`/api/disease/predict`, `/api/voice/transcribe`); free-text query params on the mandi routes; arbitrary JSON on `/api/questionnaire/submit-set`; and four third-party responses (OpenWeather, Agmarknet, Tavily, Groq) that flow into the DB and into LLM prompts.

The codebase shows real safety engineering in the recommendation path — LLM output is slug-allow-listed and numeric claims are stripped, mock weather is off by default, prices are never fabricated. The problems below are mostly at the *edges*: deployment packaging, concurrency, and unvalidated inputs reaching caches and third-party quotas.

---

## 1. Executive summary — the five most urgent issues

1. **The app will happily boot in production with a publicly-known JWT signing key.** If `SECRET_KEY` is unset, `auth_utils.py` falls back to the literal string `'your-secret-key-change-in-production'`. Anyone who reads this repo can mint a valid token for any email and read/write that farmer's data. Nothing fails, warns, or refuses to start.

2. **The documented production image cannot run the two headline ML features.** `docs/neon-aws-deployment.md` says to build from the root `Dockerfile`, which installs a hand-written package list that omits `numpy`, `pandas`, `scikit-learn`, `joblib`, `xgboost`, `torch` and `torchvision`. Because every ML import is lazy and every failure is caught, the app starts, looks healthy, and silently returns "model unavailable" / "disease detection unavailable" forever.

3. **Every slow third-party call blocks the whole worker.** The Groq, Tavily and PyTorch calls are synchronous SDK calls made from `async def` handlers. One farmer opening Government Schemes freezes *all* concurrent requests on that process for the duration of two Tavily "advanced" searches plus an un-timeout-ed LLM call.

4. **The local dev database — containing real accounts and bcrypt hashes — gets baked into the production image.** The root `.dockerignore` excludes `.env` and `Dataset/` but not `*.db`, so `backend/agrobot.db` is copied to `/app/backend/agrobot.db` and pushed to ECR. Worse, `DATABASE_URL` silently defaults to that same SQLite file, so a missing env var means the app runs happily against stale baked-in data on ephemeral container storage.

5. **The recommendation engine structurally cannot produce a real recommendation.** The crop catalogue ships as a 22-entry stub with no agronomic data at all (`knowledge_profile_complete: false`, `source_name: null` for every crop), and rainfall is hard-coded as model-incompatible. Three independent gates therefore always fail, so `RecommendationStatus.SUCCESS` is unreachable and users only ever see one "preliminary" crop. The tests lock this in, so it is deliberate — but it means the product's core promise is not yet shippable.

---

## 2. Findings table

| ID | Severity | Category | File:Line | Summary |
|----|----------|----------|-----------|---------|
| F-01 | Critical | Secrets / AuthN | `backend/app/utils/auth_utils.py:16` | JWT signing key falls back to a hardcoded public default |
| F-02 | Critical | Deployment | `Dockerfile:20-36` | Production image omits every ML dependency; features fail silently |
| F-03 | High | Async / Availability | `backend/app/services/ai_service.py:100`, `:345` | Blocking Groq SDK calls inside `async def` stall the event loop |
| F-04 | High | Async / Availability | `backend/app/services/government_api_service.py:421` | Tavily + Groq called synchronously from an async route, no timeout |
| F-05 | High | Async / Availability | `backend/app/services/crop_news_service.py:141` | Same, reached from `GET /api/mandi-prices/news` |
| F-06 | High | Async / Availability | `backend/app/services/disease_inference_service.py:193` | Torch inference + vision LLM run on the event loop |
| F-07 | High | Input validation / DoS | `backend/app/routers/disease.py:27`, `voice.py:21` | Unbounded `await file.read()`; 10 MB limit is client-side only |
| F-08 | High | Scaling / Quota | `backend/app/services/mandi_price_service.py:365-386`, `:437-445` | Up to 400 sequential upstream calls in one request; no rate limit |
| F-09 | High | Data integrity | `backend/app/services/mandi_price_service.py:586-595`, `:546-551` | `ilike()` on raw user input makes `%` return another crop's prices |
| F-10 | High | Data exposure | `.dockerignore:1-15` + `backend/app/database/connection.py:28` | Dev SQLite DB (real users, bcrypt hashes) ships in the image; silent SQLite fallback |
| F-11 | High | Safety / Correctness | `backend/app/services/disease_inference_service.py:224` | 15-class tomato/potato/pepper CNN answers confidently for any crop |
| F-12 | High | Dependencies | `backend/requirements.txt:1-23` | 42 known vulns in 7 packages, all on the auth/upload path |
| F-13 | High | AuthN hardening | `backend/app/routers/auth.py:54` | No rate limiting or lockout on login (or anywhere) |
| F-14 | High | Product readiness | `backend/app/data/crop_catalog.v1.json`, `farm_context_service.py:144` | Knowledge lane is empty and `RECOMMENDED` status is unreachable |
| F-15 | Medium | API correctness | `backend/app/main.py:67-71` | Unknown `/api/*` GETs return HTTP **200** with `{"detail":"Not Found"}` |
| F-16 | Medium | CORS | `backend/app/main.py:23` | `localhost` origins permanently allowed with credentials in prod |
| F-17 | Medium | Info disclosure | `backend/app/routers/disease.py:67`, `:79` | Raw exception text and model paths returned to clients |
| F-18 | Medium | Dead feature | `backend/app/services/crop_recommendation_service.py` (never sets it) | `soil_health_score` is never computed → analytics & advisor panels always blank |
| F-19 | Medium | Race condition | `backend/app/routers/weather.py:60-75` vs `schemas.py:120` | Unique constraint + non-idempotent insert → concurrent 500s |
| F-20 | Medium | Migration safety | `backend/app/main.py:51` | `RUN_MIGRATIONS` defaults to `true`; every instance races `alembic upgrade` |
| F-21 | Medium | Observability | no `basicConfig` anywhere; `weather_service.py:55`,`:113` | `logger.info` silently dropped; `print()` used for errors |
| F-22 | Medium | Observability | `backend/app/main.py:62` | `/api/health` checks nothing — not DB, not the model |
| F-23 | Medium | Input validation | `backend/app/models/questionnaire.py:80-84` | `/submit-set` takes any `set_number` and arbitrary unbounded JSON |
| F-24 | Medium | Release process | ~30 untracked files incl. `app/data/crop_catalog.v1.json` | A clean clone crashes at import; the running app is not in version control |
| F-25 | Medium | Scaling | `mandi_price_service.py:604-609`, `analytics_service.py:17-32`, `advisor.py:34-49` | Full-table loads, no pagination, N+1 queries |
| F-26 | Medium | Config drift | `backend/requirements.txt` vs installed venv | Artifacts pickled with numpy 2.2/xgboost 3.2 but image pins numpy 1.26/xgboost 2.x |
| F-27 | Medium | Deployment | `backend/Dockerfile:22-37` | Strips `torch/optim` and `torch/onnx`, which `torch/__init__` imports |
| F-28 | Medium | Config drift | `frontend/.env.production:1` | Points at a stale Azure host while the docs deploy to AWS |
| F-29 | Medium | Latent crash | `backend/app/services/crop_catalog_service.py:154`,`:159`,`:164` | Eager `.lower()` on a possibly-`None` field; fires the day the catalogue is filled |
| F-30 | Medium | Logic | `backend/app/routers/recommendations.py:197-210` | Legacy rows with an unknown score are promoted into `recommended_crops` |
| F-31 | Medium | Data loss | `backend/app/services/mandi_price_service.py:480-490` | Cache refresh overwrites existing lat/long with `None` |
| F-32 | Medium | Error handling | `backend/app/services/government_api_service.py:65-70` | Inner Tavily retry is unguarded → uncaught 500 |
| F-33 | Medium | Timezone | throughout (`datetime.utcnow()` + `date.today()`) | Naive UTC mixed with server-local dates; "today's prices" wrong for IST |
| F-34 | Medium | Supply chain | `backend/app/services/disease_inference_service.py:182`, `crop_prediction_service.py:57` | `torch.load` / `joblib.load` deserialise pickles without `weights_only` |
| F-35 | Medium | Container hardening | `Dockerfile:41-55`, `backend/Dockerfile:44-58` | Runs as root, no `HEALTHCHECK`, `npm install` not `npm ci` |
| F-36 | Low | Crypto | `backend/app/utils/auth_utils.py:13`,`:25` | bcrypt rounds lowered to 10; password truncated by chars not bytes |
| F-37 | Low | Input validation | `backend/app/models/user.py:5-9` | No password policy at all |
| F-38 | Low | XSS hardening | `frontend/src/pages/GovernmentSchemes.jsx:640`, `MandiPrices.jsx:616` | LLM/Tavily-supplied URLs rendered as `href` with no scheme allow-list |
| F-39 | Low | Prompt injection | `backend/app/utils/prompt_generator.py:56-66` | Farmer free-text is interpolated into prompts undelimited |
| F-40 | Low | Dead code | see §4 | Dead functions, unused imports, broken API wrapper, save-only feature |

---

## 3. Detailed findings

### F-01 — Critical — Hardcoded fallback JWT signing key

**What's wrong** — `backend/app/utils/auth_utils.py:16`:

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
```

Nothing validates that `SECRET_KEY` was actually supplied. `docs/neon-aws-deployment.md` tells you to wire it from Secrets Manager, but a typo in the secret name, a failed IAM read, or a `docker run` without `-e` produces a running, apparently-healthy service signing tokens with a string that is in this repository.

**Exploit** — An attacker who knows the app is AgroBot (open-source, MIT, public contact email in the README) runs:

```python
jose.jwt.encode({"sub": "victim@example.com", "role": "admin",
                 "exp": ...}, "your-secret-key-change-in-production", algorithm="HS256")
```

`get_current_user` (`auth_utils.py:62-73`) decodes it, looks up the user by email, and returns them. The attacker now reads and writes that farmer's questionnaire (which contains district-level location), recommendations, and crop records. With `role` set to `advisor`/`admin`, `require_role` (`auth_utils.py:76-84`) reads `role` from the DB rather than the token, so privilege escalation is blocked — but full account takeover of any known email address is not.

**Fix** (quick) — fail closed at import:

```python
SECRET_KEY = os.environ["SECRET_KEY"]          # KeyError on boot if absent
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters")
```

Then rotate the key (invalidating existing sessions) and add a startup assertion to the deploy checklist.

**Effort:** quick fix.

---

### F-02 — Critical — Production image is missing every ML dependency

**What's wrong** — `docs/neon-aws-deployment.md` §4 instructs `docker build -t agrobot-app:latest .` from the repo root. The root `Dockerfile:20-36` does *not* use `requirements.txt`; it re-declares a shorter list:

```dockerfile
RUN pip install --prefix=/install/deps --no-warn-script-location \
    fastapi==0.104.1 uvicorn==0.24.0 "pydantic[email]==2.5.0" \
    sqlalchemy==2.0.23 alembic==1.13.1 psycopg2-binary==2.9.9 \
    "psycopg[binary]==3.2.1" "python-jose[cryptography]==3.3.0" \
    "passlib[bcrypt]==1.7.4" bcrypt==3.2.2 python-multipart==0.0.6 \
    httpx==0.25.2 python-dotenv==1.0.0 groq==0.4.1 tavily-python "Pillow>=10.0.0"
```

`numpy`, `pandas`, `scikit-learn`, `joblib`, `xgboost`, `torch` and `torchvision` — all present in `requirements.txt` — are absent.

I verified that every ML import is lazy (`grep -rE 'numpy|pandas|joblib|torch|sklearn|xgboost' backend/app` matches only inside `crop_prediction_service.py` and `disease_inference_service.py`, both inside functions), so the app **starts normally**. And every failure is swallowed:

- `crop_prediction_service.py:53` `import joblib` → `ImportError`, caught by `except Exception` at `:176` → returns `MODEL_UNAVAILABLE`.
- `main.py:53` `validate_catalog_at_startup()` → `crop_prediction_service.py:104` catches everything and only calls `logger.error` — which, per F-21, has no handler configured for the root logger.
- `disease_inference_service.py:162` `import torch` → `RuntimeError` at `:165`, caught at `:196` → returns `predicted_class="disease_detection_unavailable"` with `confidence=0.0`, which `disease.py:43-52` then **writes to the database** as a prediction row.

**Failure scenario** — You deploy, `curl /api/health` returns `{"status":"ok"}`, App Runner reports healthy. Every farmer who taps "Get recommendations" receives a generic knowledge-only response; every leaf photo returns boilerplate "isolate affected leaves, improve ventilation" guidance. No alarm fires. The `disease_predictions` table fills with `disease_detection_unavailable` rows that later corrupt the advisor dashboard's disease counts (`advisor.py:44-49`).

**Fix** (moderate) — delete the duplicated list and install from the file the repo already maintains:

```dockerfile
COPY agrobot-assistant/backend/requirements.txt ./
RUN pip install --prefix=/install/deps --no-warn-script-location -r requirements.txt
RUN pip install --prefix=/install/deps --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2 torchvision==0.17.2
```

…and add a smoke test to the build: `python -c "from app.services.crop_prediction_service import crop_prediction_service as s; s._ensure_loaded()"`. Independently, stop swallowing the load failure — see F-22.

**Effort:** moderate (the image will grow by ~200 MB even with the CPU-only torch wheel; `backend/Dockerfile` already solves that and may be the better base).

---

### F-03 / F-04 / F-05 / F-06 — High — Blocking I/O inside async request handlers

**What's wrong** — FastAPI runs `async def` handlers directly on the event loop. Four code paths perform long synchronous work there:

| Where | Blocking call | Bound |
|---|---|---|
| `ai_service.py:100` | `self.client.chat.completions.create(...)` (sync Groq SDK) | `GROQ_TIMEOUT_SECONDS`, default 20 s |
| `ai_service.py:345` | `self.client.audio.transcriptions.create(...)` (Whisper) | same client timeout |
| `government_api_service.py:421` via `recommendations.py:449` | 2–3 `tavily.search(search_depth="advanced")` + `groq_client.chat.completions.create` | **no timeout at all** (`Groq(api_key=...)` at `:34`) |
| `crop_news_service.py:141` via `mandi_prices.py:125` | 2 advanced Tavily searches + Groq | **no timeout** |
| `disease_inference_service.py:193` via `disease.py:38` | `torch` forward pass + base64 vision LLM call | unbounded |

Note the shape of the call site — `mandi_prices.py:119-125`:

```python
@router.get("/news", response_model=CropMarketNewsResponse)
async def get_crop_market_news(crop: str = Query(..., min_length=1), ...):
    return crop_news_service.get_or_fetch_news(db=db, crop=crop)   # fully synchronous
```

**Failure scenario** — Two farmers tap "Government Schemes" within a second of each other. The first request enters `generate_government_schemes`, which issues two `search_depth="advanced"` Tavily calls (typically 3–8 s each) followed by a Groq completion with no client timeout. For that entire window the worker's event loop is parked: the second farmer's login, the health check, and every in-flight weather poll all queue behind it. With the default single uvicorn worker, throughput for the whole service drops to roughly one scheme lookup at a time, and App Runner's health check can time out and recycle the instance mid-request.

**Fix** (quick per call site) — either use the async SDK clients, or push the sync call into a thread:

```python
result = await asyncio.to_thread(crop_news_service.get_or_fetch_news, db, crop)
```

For the DB-touching ones (`crop_news_service`, `mandi_price_service`) a thread is not enough, because the `Session` is not thread-safe — move those to `def` (non-async) handlers instead, which FastAPI automatically runs in its threadpool. Separately, give every Groq client an explicit timeout: `Groq(api_key=..., timeout=20)` at `government_api_service.py:34` and `disease_inference_service.py:29`.

**Effort:** moderate (the handler `async`/`def` split needs care around the shared `Session`).

---

### F-07 — High — Unbounded upload bodies read straight into memory

**What's wrong** — `backend/app/routers/disease.py:21-32`:

```python
if not image.content_type or not image.content_type.startswith("image/"):
    raise HTTPException(400, "Please upload a valid image file")
image_bytes = await image.read()          # entire body, no size cap
```

and the identical pattern at `voice.py:15-26`. The only size check in the system is client-side, in `frontend/src/pages/DiseaseCheckup.jsx:133` (`if (f.size > MAX_SIZE)`), which an attacker simply does not run. `Content-Type` is attacker-controlled and is the *only* gate before the bytes are buffered.

**Exploit** — An authenticated user `POST`s a 2 GB body to `/api/disease/predict` with `Content-Type: image/png`. `await image.read()` materialises all of it in the worker's heap; a handful of concurrent requests OOM-kills the container. A cheaper variant: a 10 KB PNG decompression bomb — PIL's default `MAX_IMAGE_PIXELS` raises above ~178 M pixels, which helps, but `Image.open(...).convert("RGB")` at `disease_inference_service.py:216` still allocates for anything under that threshold. The voice endpoint has no equivalent library-level guard at all, and `useVoiceRecorder.js` imposes no recording duration limit.

**Fix** (quick) — cap before reading, and validate by content rather than header:

```python
MAX_UPLOAD = 10 * 1024 * 1024
image_bytes = await image.read(MAX_UPLOAD + 1)
if len(image_bytes) > MAX_UPLOAD:
    raise HTTPException(413, "Image must be 10 MB or smaller")
try:
    img = Image.open(io.BytesIO(image_bytes)); img.verify()
except Exception:
    raise HTTPException(400, "Not a readable image")
```

Also set a request-body limit at the ingress (App Runner / reverse proxy) so the bytes never reach Python.

**Effort:** quick fix.

---

### F-08 — High — Unbounded upstream fan-out per request

**What's wrong** — `mandi_price_service.get_cached_or_fetch` (`:174-203`) loops over `lookback_days + 1` dates (default 8), issuing one Agmarknet call per date until it finds data. Callers multiply it:

- `compare_mandis` (`:356-423`) takes `limit=50` candidate mandis and calls `get_cached_or_fetch` once per mandi in the baseline loop (`:371`) **and again** in the recommendation loop (`:386`) → up to 50 × 8 × 2 = **800** sequential HTTP calls, each with a 5 s timeout.
- `get_price_trend` (`:425-470`) loops 30 days, one `get_cached_or_fetch` per day (`:439`) → 30 calls, each followed by a `db.commit()`.
- `get_current_prices` (`:231-312`) does 5 mandis × 8 dates, then `fetch_recent_scope_snapshots` (+8), then two `_summary_for_scope` calls (+2).

All of it is `await`ed serially, and the circuit breaker (`_record_failure`, `:162`) only opens on *failures*, not on success-but-slow.

**Failure scenario** — A farmer opens the Mandi Prices comparison for a crop with no recent Agmarknet data. Every one of the 50 mandis misses cache, every one of its 8 date probes returns an empty record set, and the request grinds through hundreds of upstream calls before returning — far past the frontend's 30 s axios timeout (`api.js:8`). The farmer retries; the worker is now doing this twice. Meanwhile the shared data.gov.in API key burns its daily quota, which under F-13 (no rate limiting) any authenticated account can do deliberately: `/api/mandi-prices/trend?market=x&crop=y&days=30` in a loop.

**Fix** (refactor) — batch the upstream query instead of iterating. Agmarknet accepts a commodity+state filter returning many markets at once (`_summary_for_scope` already does this with `limit=1000`); fetch once and index the result in memory, rather than one HTTP call per (market, date) pair. Short term, cap `compare_mandis` candidates to ~10, set `lookback_days=2`, and add `asyncio.gather` with a semaphore instead of a serial loop.

**Effort:** refactor.

---

### F-09 — High — `ilike()` on raw user input returns the wrong crop's prices

**What's wrong** — the price cache is looked up with `ILIKE` against an unescaped user-supplied string. `mandi_price_service.py:586-595`:

```python
def _get_cached(self, db, commodity: str, market: str, price_date: date):
    return (db.query(MandiPriceSnapshot)
        .filter(MandiPriceSnapshot.commodity.ilike(commodity),      # commodity is user input
                MandiPriceSnapshot.market_name.ilike(market),
                MandiPriceSnapshot.price_date == price_date)
        .first())
```

Same pattern at `:546-551` (`_summary_for_scope`), `:606` / `:628-632` (`_nearest_mandis`, `_find_mandi`), and `crop_news_service.py:50`. `crop` arrives from `Query(..., min_length=1)` at `mandi_prices.py:62` with no allow-list — `search_commodities` exists but is never used to validate.

**Exploit** — `GET /api/mandi-prices/current?crop=%25` (`%` URL-encoded). `fetch_prices` sends `%` upstream and gets nothing, then `get_cached_or_fetch` calls `_get_cached(db, "%", market, date)`. `ILIKE '%'` matches **every row**, so `.first()` returns an arbitrary commodity's snapshot — onion prices, say — which `snapshot_to_point` returns with `"data_status": "available"` under `"crop": "%"`. A subtler and more damaging variant is `crop=Ric_` or `crop=%heat`, which returns Rice/Wheat data labelled as the requested string. This directly contradicts the module's own stated invariant at `:63-65`: *"Market prices are financial data. Never manufacture them when the external source is unconfigured."*

The same wildcard reaches `crop_news_service._cached_news` (`:50`), returning one crop's market news under another crop's name.

**Fix** (quick) — use exact, case-normalised matching and validate the commodity against the known list:

```python
MandiPriceSnapshot.commodity == commodity_normalised   # or func.lower(col) == commodity.lower()
```

and at the router, reject anything not in `AGMARKNET_COMMODITIES` ∪ the farm's saved crops. If `ILIKE` is genuinely wanted for case-insensitivity, escape the input: `value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")` with `escape="\\"`.

**Effort:** quick fix.

---

### F-10 — High — Dev database with real credentials ships inside the image

**What's wrong** — two issues compound.

The root `.dockerignore` lists `.git`, `**/.env`, `Dataset`, `.venv`, `frontend/build` — but **not** `*.db`. The root `Dockerfile:38` does `COPY agrobot-assistant/backend/ ./`, so `backend/agrobot.db` lands at `/app/backend/agrobot.db` in the published image. I confirmed that file contains a populated `users` table with real email addresses and `$2b$10$…` bcrypt hashes, plus `questionnaire_responses` (which store district-level location) and `recommendations`. (`backend/.dockerignore` *does* exclude `agrobot.db` — but that file only applies to builds from the backend directory, which is not the documented path.)

Then `backend/app/database/connection.py:28`:

```python
DATABASE_URL = _clean_database_url(os.getenv('DATABASE_URL', 'sqlite:///./agrobot.db'))
```

**Failure scenario** — Anyone with `ecr:BatchGetImage` on the repository (a broader group than your DB users) can `docker pull` and read the SQLite file: emails, password hashes to crack offline, and farm locations. Separately, if the `agrobot/DATABASE_URL` secret fails to resolve — a typo, a missing IAM grant, a Secrets Manager throttle — the app does not crash. It falls back to that baked-in SQLite file, serves stale data from the developer's laptop, accepts new signups, and loses every write when the container recycles.

**Fix** (quick) — add to the root `.dockerignore`:

```
**/*.db
**/*.sqlite3
agrobot-assistant/backend/test_*.py
agrobot-assistant/backend/experiments.ipynb
```

and make the URL mandatory in production:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if os.getenv("APP_ENV", "dev") != "dev":
        raise RuntimeError("DATABASE_URL is required")
    DATABASE_URL = "sqlite:///./agrobot.db"
```

Treat the committed `agrobot.db` credentials as compromised and rotate the affected accounts.

**Effort:** quick fix.

---

### F-11 — High — 15-class disease model answers confidently for crops it has never seen

**What's wrong** — `ml-cnn/artifacts/checkpoints/classes.json` contains exactly 15 classes, all bell pepper, potato or tomato (`Tomato_Late_blight`, `Potato___Early_blight`, …). `disease_inference_service.predict` (`:219-231`) takes an unconditional `argmax` over a softmax:

```python
probs = self._torch.softmax(logits, dim=1)
score, pred_idx = self._torch.max(probs, dim=1)
predicted_class = self._class_names[pred_idx.item()]
confidence = float(score.item())
```

There is no out-of-distribution check and no confidence floor. `disease.py:43-62` stores the result and returns it, and `DiseaseCheckup.jsx` presents it as actionable treatment advice. The frontend's file picker accepts any JPEG/PNG (`accept="image/jpeg,image/png"`), and the app is marketed for wheat, rice, cotton and sugarcane farmers.

**Failure scenario** — A wheat farmer photographs rust on a wheat leaf. The CNN has no wheat class, so softmax redistributes over the 15 it knows and returns, say, `Tomato_Septoria_leaf_spot` at 0.94 confidence. The farmer is told to apply a tomato-specific fungicide programme. This is the highest real-world-harm finding in the audit: wrong agrochemical advice costs money and can damage the crop.

**Fix** (moderate) —
1. Gate on confidence and on supported crops. Ask the user which crop they are photographing, and if it is not pepper/potato/tomato, return "not supported for this crop" rather than a prediction.
2. Add a low-confidence threshold (`if confidence < 0.7: return inconclusive`) and surface the confidence prominently in the UI.
3. Do not persist `disease_detection_unavailable` / inconclusive results as `DiseasePrediction` rows (`disease.py:43`) — they pollute `advisor.py:90-93` and `analytics_service.py:56`.

**Effort:** moderate.

---

### F-12 — High — Known-vulnerable dependencies on the authentication and upload paths

`pip-audit` against `requirements.txt` reports **42 vulnerabilities across 7 packages**. Full summary in §5. The three that matter most:

- **`python-multipart==0.0.6`** — 11 advisories, fixes up to 0.0.31. `PYSEC-2024-38` is the `Content-Type` ReDoS. This library parses *every* login (`/api/auth/login` uses `OAuth2PasswordRequestForm`) and both file uploads — it is the first code to touch unauthenticated attacker bytes.
- **`starlette==0.27.0`** — 11 advisories. `PYSEC-2026-1943` (fix 0.40.0) is the unbounded multipart memory DoS, which compounds F-07 directly.
- **`python-jose==3.3.0`** — `PYSEC-2024-232` / `PYSEC-2024-233` (fix 3.4.0), algorithm-confusion and a JWE decompression bomb, sitting in `get_current_user`. `PYSEC-2025-185` has no fix, and the transitive `ecdsa` carries `PYSEC-2026-1325` (also unfixed).

**Fix** (moderate) — bump `fastapi>=0.115`, `python-multipart>=0.0.31`, `starlette>=0.40` (comes with FastAPI), `python-dotenv>=1.2.2`, `anyio>=4.14.2`. Migrate `python-jose` → `PyJWT`, which is maintained and drops the `ecdsa` dependency entirely; the change is ~10 lines in `auth_utils.py`.

**Effort:** moderate (the FastAPI bump needs a regression pass over the Pydantic v2 response models).

---

### F-13 — High — No rate limiting anywhere

`grep -rni "ratelimit|slowapi|limiter" backend/app` returns exactly one hit — a string comparison inside `ai_service._request_failure_code`. There is no throttling middleware, no login attempt counter, and no lockout.

**Failure scenario** — `/api/auth/login` (`auth.py:54`) is an unauthenticated password oracle. bcrypt at 10 rounds (F-36) is ~50 ms per attempt, and `verify_password_async` correctly offloads to a thread — which means the endpoint is *happy* to run many in parallel. An attacker credential-stuffs at hundreds of attempts per second against the known email pattern. Authenticated endpoints are worse: each `/api/recommendations/generate` runs a full model + LLM pass, and each `/api/mandi-prices/trend` burns 30 upstream calls (F-08), so one account can exhaust both the Groq and data.gov.in quotas.

**Fix** (quick) — add `slowapi` with a strict bucket on `/api/auth/*` (e.g. 5/min per IP + per email) and a looser one on the expensive routes (`/recommendations/generate`, `/mandi-prices/*`, `/disease/predict`). Add exponential backoff or lockout after N failed logins for the same email.

**Effort:** quick fix.

---

### F-14 — High — The recommendation engine cannot currently recommend anything

This is a chain of three independent gates, each of which always fails.

**(a) The crop catalogue is an empty stub.** `backend/app/data/crop_catalog.v1.json` holds 22 profiles that look like this:

```json
{"crop_slug": "apple", "display_name": "Apple"}
```

Every agronomic field comes from `profile_defaults`, where `knowledge_profile_complete: false`, `source_name: null`, `supported_states: null`, `supported_soil_types: []`, all pH/temperature/rainfall bounds `null`. So `get_knowledge_profiles()` (`crop_catalog_service.py:102-109`) — which requires `knowledge_profile_complete and source_name and has_verified_constraints()` — returns `[]` **always**, and `find_knowledge_candidates` never enters its loop. The entire knowledge lane is dead.

**(b) Rainfall is hard-coded incompatible.** `farm_context_service.py:144` sets `model_compatible_rainfall_mm=None` unconditionally, and `:134-138` sets `rainfall_compatibility` to `INCOMPATIBLE_PERIOD` or `UNKNOWN` — never `COMPATIBLE`. Therefore `crop_prediction_service.py:184-187` computes `rainfall_withheld = True` on every call, and `:251-252` forces `status = PRELIMINARY_MISSING_INPUT`.

**(c) Ranking then refuses to promote anything.** `crop_ranking_service.py:125-137`:

```python
can_be_recommended = (
    score >= RANKING_CONFIG.minimum_recommendation_score
    and data_quality.level != DataQualityLevel.LOW
    and model_status not in {..., ModelPredictionStatus.PRELIMINARY_MISSING_INPUT}
    and validation.validation_coverage_summary.verified_checks >= 4)
```

`model_status` is always `PRELIMINARY_MISSING_INPUT` (b), so this is always `False`. Independently, `verified_checks` is always 0 because every `crop_validation_service` check returns `NOT_AVAILABLE` against the stub profiles (a), and `data_quality.level` is always `LOW` because `missing` always contains rainfall (`farm_context_service.py:261-276`).

**Consequence** — `CandidateRecommendationStatus.RECOMMENDED`, `RecommendationStatus.SUCCESS`, `DataQualityLevel.HIGH`, and the `MIN_RECOMMENDATION_SCORE` / `MIN_VERIFIED_CHECKS_FOR_RECOMMENDATION` env knobs are all unreachable. Every farmer sees the message *"Only preliminary crop matches are available because important validation is incomplete"* and the template summary *"This is only a preliminary ML pattern; crop-specific local agronomic suitability could not be verified."* Working the arithmetic in `crop_ranking_service.py:108-124` with an empty catalogue (`weighted = model_probability`, `quality_factor = 0.70`, one warning penalty), a candidate needs `p ≥ 0.37` just to clear `MIN_PRELIMINARY_SCORE=25`, so in practice exactly one crop is shown.

`tests/test_safe_crop_recommendations.py:424` (`test_annual_rainfall_pipeline_returns_only_preliminary_model_matches`) asserts this outcome, so it is a deliberate fail-safe rather than a bug — the conservatism is good engineering. **But it means the product's headline feature is not shippable yet**, and that should be an explicit go/no-go decision rather than an emergent property.

**Fix** (refactor) — this is product work, not a patch. Two prerequisites: populate the crop catalogue with sourced agronomic profiles for the 22 model classes (`scripts/sync_crop_catalog_model_classes.py` appears designed for exactly this), and resolve the rainfall-semantics question documented in `artifacts/xgboost_crop_metadata.json` (`"documentation_status": "not_documented_in_repository"`) — either by retraining with a documented rainfall period, or by sourcing seasonal rainfall per district.

**Effort:** refactor.

---

### F-15 — Medium — Unknown `/api` routes return HTTP 200

`backend/app/main.py:67-71`:

```python
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        return {"detail": "Not Found"}
```

Returning a dict from a FastAPI handler yields **200 OK**. So `GET /api/does-not-exist` → `200 {"detail":"Not Found"}`.

**Failure scenario** — `frontend/src/services/api.js:194` calls `GET /api/weather?location=…`, a route that does not exist (the weather router only defines `/current`, `/forecast`, `/overview`). Instead of a 404 that the axios interceptor could surface, the caller gets a 200 whose body is `{"detail": "Not Found"}` and treats it as weather data. Monitoring and uptime checks are equally misled: a totally broken API returns 200 for every GET.

Note the path-traversal guard immediately below (`:73-79`) is sound — `.resolve()` followed by `relative_to(FRONTEND_BUILD_DIR)` correctly rejects both `../` and absolute paths.

**Fix** (quick):

```python
from fastapi import HTTPException
if full_path.startswith("api/") or full_path == "api":
    raise HTTPException(status_code=404, detail="Not Found")
```

and likewise for the two `{"detail": "Not Found"}` returns at `:78` and `:84`.

**Effort:** quick fix.

---

### F-16 — Medium — CORS permanently allows localhost with credentials

`backend/app/main.py:20-28`:

```python
app.add_middleware(CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True, ...)
```

The regex is unconditional — it applies in production exactly as in development. Any page served from `http://localhost:<anything>` on a farmer's machine can make credentialed cross-origin calls to the production API. Since the JWT lives in `localStorage` rather than a cookie (F-40/M12), `allow_credentials` does not by itself leak the token — but any locally-running dev server, Electron app, or malicious tool that *has* obtained the token can now use the API from the browser context without CORS friction, and the exposure is wider than intended.

**Fix** (quick) — gate it on the environment:

```python
allow_origin_regex = (r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
                      if os.getenv("APP_ENV", "dev") == "dev" else None)
```

**Effort:** quick fix.

---

### F-17 — Medium — Internal exception text returned to clients

`backend/app/routers/disease.py:63-80`:

```python
except FileNotFoundError as exc:
    raise HTTPException(500, detail=f"Model artifacts not found. Train the CNN first and ensure checkpoint exists. {exc}")
except RuntimeError as exc:
    raise HTTPException(500, detail=str(exc))
except Exception as exc:
    db.rollback()
    raise HTTPException(500, detail=f"Disease prediction failed: {exc}")
```

**Exploit** — upload a text file with `Content-Type: image/png`. The `startswith("image/")` check passes, `Image.open` raises `PIL.UnidentifiedImageError` (an `OSError`, not a `RuntimeError`), and the client receives a 500 whose body embeds PIL internals. Other paths leak absolute filesystem paths and SQLAlchemy error text. Two of these handlers are also dead code: `disease_inference_service.predict` (`:193-206`) already catches `FileNotFoundError` and `RuntimeError` internally, so they can never reach the router.

**Fix** (quick) — log the detail, return a generic message, and return 400 for bad input:

```python
except Exception:
    db.rollback()
    logger.exception("Disease prediction failed")
    raise HTTPException(500, detail="Disease prediction failed")
```

**Effort:** quick fix.

---

### F-18 — Medium — `soil_health_score` is never computed

`grep -rn soil_health_score backend/app` shows it **read** in seven places and **never assigned** a computed value. `crop_recommendation_service.generate` builds `AIRecommendationResponse` at `:119` and `:164` without it, so it takes the model default `None` (`models/recommendation.py:242`). `_save_recommendation` (`recommendations.py:37`) then writes `NULL` to every row.

**Consequence** — three surfaces are permanently blank: the Analytics soil-score trend chart (`analytics_service.py:39-54` skips every row at the `is None` guard), `latest_soil_health_score` (`:103-107`), and the advisor dashboard's `latest_soil_score` column (`advisor.py:55`, `:102`). The adoption metric is dead for the same underlying reason as F-14: `analytics_service.py:77` reads `latest_recommendation.recommended_crops`, which is always `[]` because nothing is ever `RECOMMENDED`, so `adoption_rate` is hard-zero.

**Fix** (moderate) — either implement a soil score from the NPK/pH/organic-matter inputs already in `FarmContext`, or remove the field and the four UI surfaces that depend on it. Shipping an always-empty chart is worse than shipping no chart.

**Effort:** moderate.

---

### F-19 — Medium — Weather snapshot race produces 500s

`backend/app/database/schemas.py:120-122` declares `UniqueConstraint('farm_id', 'date')` on `weather_snapshots`. Two code paths insert into it without any conflict handling:

- `weather.py:60-75` — `_save_weather_snapshot` does a bare `db.add(); db.commit()`.
- `farm_context_service.py:181-191` — `_weather` adds a snapshot during recommendation generation.

Both are preceded by a read-then-write with no lock (`weather.py:117` `_get_today_snapshot`, `farm_context_service.py:160-164`).

**Failure scenario** — The dashboard loads and fires `/api/weather/overview` and `/api/recommendations/generate` concurrently for the same farm. Both find no snapshot for today, both build one, both commit. The loser gets `IntegrityError` → uncaught in `weather.py` (a raw 500), or caught by `recommendations.py:369` → `db.rollback()` and a misleading "Recommendation generation failed safely" 500. Probability rises with every concurrent tab and with multiple uvicorn workers.

**Fix** (quick) — make the write idempotent. On Postgres:

```python
from sqlalchemy.dialects.postgresql import insert
stmt = insert(WeatherSnapshot).values(...).on_conflict_do_nothing(
    index_elements=["farm_id", "date"])
db.execute(stmt); db.commit()
snapshot = _get_today_snapshot(db, farm_id)
```

or wrap in `try/except IntegrityError: db.rollback(); return _get_today_snapshot(...)`.

**Effort:** quick fix.

---

### F-20 — Medium — Migrations run from the app's startup hook, defaulting to on

`backend/app/main.py:49-53`:

```python
@app.on_event("startup")
async def startup_event():
    if os.getenv("RUN_MIGRATIONS", "true").lower() in {"1", "true", "yes"}:
        run_migrations()
```

The default is `true`. `docs/neon-aws-deployment.md` §5 does set `RUN_MIGRATIONS=false`, but the safe behaviour depends on remembering an env var rather than on the code.

**Failure scenario** — App Runner scales to two instances, or you run uvicorn with `--workers 2`, with `RUN_MIGRATIONS` unset. Every process calls `command.upgrade(cfg, "head")` simultaneously. Alembic takes an advisory lock on some operations but not all; concurrent DDL against Neon typically leaves one process erroring out at boot and, worst case, a partially-applied revision with `alembic_version` already advanced.

Two secondary issues in the same file: `migrations.py:21` passes the DB URL through `alembic_cfg.set_main_option`, which stores it in a `ConfigParser` — a password containing `%` will raise an interpolation error on read (NEEDS-VERIFICATION; Neon's generated passwords are alphanumeric, so this is latent). And `@app.on_event("startup")` is deprecated in modern FastAPI in favour of the `lifespan` context manager.

**Fix** (quick) — flip the default to `false` and run migrations as a separate deploy step (an App Runner pre-deploy hook or a one-off task), which is what the docs already describe for the initial migration.

**Effort:** quick fix.

---

### F-21 / F-22 — Medium — No logging configuration, and a health check that checks nothing

There is no `logging.basicConfig`, no `dictConfig`, and no logging section in any config file. Six modules do `logger = logging.getLogger(__name__)` and then log. Because the root logger has no handler, Python's `lastResort` handler emits `WARNING` and above to stderr with no timestamp, level, or request context — and **drops `INFO` entirely**. So `crop_prediction_service.py:91` ("Loaded crop candidate model …") never appears, and neither does any successful-path signal. Two errors bypass logging altogether via `print()` (`weather_service.py:55`, `:113`).

Meanwhile `main.py:62-64`:

```python
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
```

This is the App Runner health check path. It returns `ok` when the database is unreachable, when the XGBoost model failed to load, and when the CNN checkpoint is missing — i.e. in exactly the F-02 scenario.

**Fix** (quick) — add a `logging.dictConfig` at startup with a JSON formatter and an explicit root level; replace the two `print()` calls with `logger.warning(..., exc_info=True)`. Split the health endpoints:

```python
@app.get("/api/health")      # liveness — stays trivial
@app.get("/api/ready")       # readiness
async def readiness(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok",
            "crop_model": crop_prediction_service._loaded,
            "disease_model": disease_inference_service._loaded}
```

and point the platform health check at `/api/ready`. Add request IDs via a middleware while you are there.

**Effort:** quick fix.

---

### F-23 — Medium — `/submit-set` bypasses all questionnaire validation

`backend/app/models/questionnaire.py:80-84`:

```python
class QuestionnaireSubmission(BaseModel):
    user_id: int
    farm_id: Optional[int] = None
    set_number: int          # no bounds
    answers: Dict[str, Any]  # no schema, no size limit
```

The five carefully-typed models (`SoilPhysicalProperties`, `EnvironmentalRegional`, …) are enforced **only** on `/questionnaire/complete`. But `frontend/src/pages/Questionnaire.jsx:398` submits each page through `submitQuestionnaireSet`, i.e. `/submit-set` — so the typed path is the secondary one.

**Failure scenario** — A client posts `set_number=999` with a 50 MB `answers` blob; it is stored verbatim in the `JSON` column. Or it overwrites set 4 with `{}` after onboarding, stripping `district`/`state`. Downstream, `weather.py:98-104` silently substitutes `"Delhi"` (F-40/M13), and `farm_context_service.py:65` yields `soil_type=None`, which is the trigger condition for the latent crash in F-29. `submission.user_id` is also a client-supplied field that only exists to be compared against `current_user.id` at `questionnaire.py:20` — dead weight on a trust boundary.

**Fix** (quick) — validate on the way in:

```python
set_number: int = Field(..., ge=1, le=5)
```

plus a discriminated union that applies the right typed model per `set_number`, and drop `user_id` from the request body in favour of `current_user.id`.

**Effort:** moderate (the frontend sends untyped dicts today, so the two sides must be aligned).

---

### F-24 — Medium — The running application is not in version control

`git status` shows ~30 untracked files that the current app cannot run without, including `app/services/mandi_price_service.py`, `crop_recommendation_service.py`, `crop_ranking_service.py`, `crop_validation_service.py`, `crop_catalog_service.py`, `crop_news_service.py`, `farm_context_service.py`, `app/routers/mandi_prices.py`, `app/config.py`, **`app/data/crop_catalog.v1.json`**, migrations `0007`–`0011`, and the entire `tests/` directory — alongside ~40 modified tracked files.

**Failure scenario** — `crop_catalog_service.py:73` calls `self.reload()` from `__init__`, and `crop_catalog_service = CropCatalogService()` runs at module import (`:232`). A clean `git clone` has no `app/data/crop_catalog.v1.json`, so importing any router that touches the recommendation stack raises `FileNotFoundError` **at import time** — the app does not start at all. The current image only builds because `COPY agrobot-assistant/backend/ ./` picks up your untracked working tree. Any CI build, any teammate, any rebuild after a `git clean` produces either a broken image or a months-old application.

**Fix** (quick) — `git add` the untracked sources and commit the modified ones. Then add a CI job that builds the image from a fresh clone, which would have caught this immediately.

**Effort:** quick fix.

---

### F-25 — Medium — Unbounded queries and N+1 access patterns

Four confirmed spots:

- `mandi_price_service.py:604-609` — `_nearest_mandis` does `db.query(Mandi).all()` (or all rows for a state) and computes haversine distance in Python for every row. The Agmarknet feed covers thousands of markets; the `mandis` table grows on every `_upsert_mandi_from_row`.
- `analytics_service.py:17-32` — loads **all** recommendations, **all** disease predictions and **all** crops for a farm, with no limit, on every dashboard load.
- `recommendations.py:459-464` — `/history` returns every recommendation ever generated, unpaginated.
- `advisor.py:34-49` — for each assigned farmer, three separate queries (farms, latest recommendation, disease count). For an admin with no explicit links, `:29-30` expands to *every* farmer in the system → 3N+1 queries.

**Fix** (moderate) — add `.limit()`/offset pagination to `/history` and the analytics queries; for `_nearest_mandis`, add a bounding-box pre-filter on lat/long (with an index) before the haversine pass; for `advisor.py`, replace the loop with grouped aggregate queries over `farm_id IN (...)`.

**Effort:** moderate.

---

### F-26 / F-27 — Medium — Version drift between the pickled artifacts and the target image

The committed artifacts were produced by the local environment, which holds `numpy 2.2.6`, `pandas 2.3.3`, `scikit-learn 1.7.2`, `xgboost 3.2.0`, `torch 2.10.0`. The images pin `numpy==1.26.4`, `pandas==2.0.3`, `xgboost>=2.0.0`, `scikit-learn>=1.3.0`, `torch==2.2.2`.

`crop_prediction_service.py:57` unpickles `{"model": XGBClassifier, "label_encoder": sklearn.LabelEncoder, ...}` with `joblib.load`. Unpickling a NumPy-2-era object graph under NumPy 1.26, or an xgboost 3.x estimator under xgboost 2.x, commonly fails outright or raises `InconsistentVersionWarning` with silently wrong behaviour. Same exposure for `best_model.pt` saved by torch 2.10 and loaded by torch 2.2.2. **NEEDS-VERIFICATION** — I could not test this, because the local `scipy` binary is itself broken on this macOS build (`ImportError: … _spropack.cpython-310-darwin.so (section '__DATA/__thread_bss' has a zero-fill section type…)`), which is why 8 of 46 tests currently fail and why the model does not load even locally.

Separately, `backend/Dockerfile:22-37` deletes `$SITE/torch/optim`, `$SITE/torch/onnx` and `$SITE/torch/distributed` to shrink the image. In torch 2.x, `torch/__init__.py` imports `optim` and `onnx` at module scope, so `import torch` will likely raise `ModuleNotFoundError` in that image. **NEEDS-VERIFICATION** (requires a build).

**Fix** — pin the training environment to match the runtime image (or vice versa), record the producing versions in `xgboost_crop_metadata.json` alongside the existing SHA256, and add a container smoke test that loads both artifacts. For the torch stripping, keep `test`, `include`, `share` and `caffe2` in the delete list but drop `optim`, `onnx` and `distributed`.

**Effort:** moderate.

---

### F-28 — Medium — Stale production frontend config

`frontend/.env.production:1`:

```
REACT_APP_API_URL=https://agrobot-api.icypond-baef2cca.eastasia.azurecontainerapps.io/api
```

The deployment doc targets AWS App Runner in `eu-north-1`. The root `Dockerfile:9` sets `ENV REACT_APP_API_URL=/api`, and CRA does not override pre-existing shell env vars, so the Docker build is safe. But any `npm run build` outside Docker — a local preview, a Netlify/Amplify build, a CI artifact — bakes the dead Azure host into the bundle and the app cannot reach its API.

**Fix** (quick) — delete `.env.production` (the Docker `ENV` already provides the right value) or set it to `/api`.

**Effort:** quick fix.

---

### F-29 — Medium — Latent `NoneType` crash in the knowledge lane

`backend/app/services/crop_catalog_service.py:152-166`:

```python
compare(
    bool(context.soil_type and profile.supported_soil_types),
    context.soil_type.lower() in {item.lower() for item in profile.supported_soil_types},
    "Soil type compatible",
)
```

Python evaluates **all arguments before the call**, so the `bool(...)` guard in argument 1 does not protect the `.lower()` in argument 2. If `context.soil_type` is `None`, `None.lower()` raises `AttributeError` immediately. The same shape appears for `context.state` (`:159`) and `context.district` (`:164`) — and the district case is worse, because `profile.supported_districts or []` means the expression is evaluated even when the profile has no districts at all.

This is **not currently reachable**: `find_knowledge_candidates` iterates `get_knowledge_profiles()`, which returns `[]` for the stub catalogue (F-14), so the loop body never runs. The moment anyone completes a single crop profile, any farmer whose district is missing or set to `"unknown"`/`"not_sure"` (both mapped to `None` by `_optional_text` at `:333-335`) gets a 500. Note that the sibling module `crop_validation_service.py:116-145` implements the identical checks correctly, with early `return NOT_AVAILABLE` guards — this file simply diverged.

**Fix** (quick) — mirror the validation-service pattern, or make `compare` take callables:

```python
soil_ok = bool(context.soil_type and profile.supported_soil_types)
compare(soil_ok,
        soil_ok and context.soil_type.lower() in {i.lower() for i in profile.supported_soil_types},
        "Soil type compatible")
```

**Effort:** quick fix.

---

### F-30 — Medium — Legacy candidates with unknown scores are promoted to "recommended"

`backend/app/routers/recommendations.py:197-210`:

```python
should_be_preliminary = force_preliminary or (
    isinstance(score, (int, float))                     # ← everything below is gated on this
    and (score < RANKING_CONFIG.minimum_recommendation_score
         or verified_checks < RANKING_CONFIG.minimum_verified_checks_for_recommendation
         or explicit_status != "recommended"))
if should_be_preliminary:
    data["recommendation_status"] = "preliminary"
    preliminary.append(CropRecommendation(**data))
else:
    data.setdefault("recommendation_status", "insufficient_support")
    recommended.append(CropRecommendation(**data))      # ← "insufficient_support" lands here
```

If `overall_suitability_score` is absent (a legacy row written before the field existed), `isinstance(score, (int, float))` is `False`, the whole conjunction short-circuits to `False`, and the candidate is appended to **`recommended`** — carrying the status string `"insufficient_support"`, and regardless of `verified_checks` being 0 or `explicit_status` being `"preliminary"`.

**Failure scenario** — A farmer opens `/api/recommendations/latest` for a recommendation generated before migration `0010`. A crop the system explicitly marked preliminary is re-served in the `recommended_crops` array. Given the project's evident design goal — never present unverified crops as recommendations — this inverts the intended fail-safe on exactly the data the safety rules were added for.

**Fix** (quick) — default to preliminary when the score is unknown:

```python
should_be_preliminary = force_preliminary or not isinstance(score, (int, float)) or (
    score < RANKING_CONFIG.minimum_recommendation_score
    or verified_checks < RANKING_CONFIG.minimum_verified_checks_for_recommendation
    or explicit_status != "recommended")
```

**Effort:** quick fix.

---

### F-31 — Medium — Cache refresh nulls out mandi coordinates

`backend/app/services/mandi_price_service.py:477-491`:

```python
existing = self._get_cached(db, row["commodity"], row["market_name"], row["price_date"])
if existing:
    snapshot = existing
    for field in ("state","district","min_price","max_price","modal_price",
                  "arrival_qty","latitude","longitude"):
        setattr(snapshot, field, row.get(field))   # unconditional overwrite
```

Agmarknet records do not carry `latitude`/`longitude`, so `row.get("latitude")` is `None` on essentially every refresh. Any coordinates previously populated on that snapshot are wiped.

**Consequence** — `get_current_prices` (`:286`) uses `_distance_to_point(farm, snapshot.latitude, snapshot.longitude)` to sort the fallback market list by distance. Once coordinates are nulled, `distance_km` becomes `None`, every fallback sorts to the `999999` bucket (`:289-294`), and the farmer is shown arbitrary markets instead of nearby ones.

**Fix** (quick) — only overwrite with non-`None` values:

```python
value = row.get(field)
if value is not None:
    setattr(snapshot, field, value)
```

**Effort:** quick fix.

---

### F-32 — Medium — Unguarded Tavily retry produces an uncaught 500

`backend/app/services/government_api_service.py:56-71`:

```python
try:
    result = tavily.search(query=query, ..., search_depth="advanced")
except Exception:
    result = tavily.search(query=query, ..., search_depth="basic")   # not wrapped
```

The retry has no handler of its own. `_search_government_schemes` is called at `:414` **outside** the `try` block that guards the Groq call at `:420-438`.

**Failure scenario** — Tavily is down, or the API key is invalid, or the network blips. Both calls raise, the exception propagates out of `generate_government_schemes`, out of `recommendations.py:449` (`/api/recommendations/government-schemes` has no try/except), and the farmer gets a bare 500 with a stack trace in the logs — despite `_fallback_from_sources` (`:361`) existing precisely to degrade gracefully.

**Fix** (quick) — wrap the retry and default to `{}`, exactly as the sibling `crop_news_service.py:74-83` already does correctly:

```python
except Exception:
    try:
        result = tavily.search(..., search_depth="basic")
    except Exception:
        result = {}
```

**Effort:** quick fix.

---

### F-33 — Medium — Naive timestamps and server-local dates

The codebase mixes `datetime.utcnow()` (naive UTC, used for every `created_at`/`fetched_at`/`generated_at`) with `date.today()` (server-local, used for cache keys). `_parse_datetime` in `crop_news_service.py:311` explicitly strips tzinfo: `parsed.replace(tzinfo=None)`.

**Failure scenario** — the cache key for prices and news is `date.today()`. In a UTC container serving IST (+5:30) farmers, "today" rolls over at 05:30 local. A farmer checking prices at 09:00 IST gets data keyed to a date that flipped four hours earlier; the "today's mandi price" label is wrong for the first 5.5 hours of every Indian day, and `WeatherSnapshot.date` has the same skew. `datetime.utcnow()` is also deprecated in Python 3.12+.

**Fix** (moderate) — use timezone-aware UTC (`datetime.now(timezone.UTC)`) for all stored timestamps, and derive the business date explicitly in IST:

```python
IST = ZoneInfo("Asia/Kolkata")
business_date = datetime.now(IST).date()
```

**Effort:** moderate (a migration is needed if existing naive columns are reinterpreted).

---

### F-34 — Medium — Pickle deserialisation of model artifacts

`disease_inference_service.py:182` — `torch.load(checkpoint_path, map_location=self._device)` with no `weights_only=True` (torch 2.2's default is `False`, i.e. full pickle). `crop_prediction_service.py:57` — `joblib.load(self.model_path)`, also arbitrary pickle.

Both files are committed to the repo, so the immediate trust boundary is your own supply chain rather than user input. The mitigation to note is that `crop_prediction_service.py:74-77` **does** verify a SHA256 against `xgboost_crop_metadata.json` — but only *after* `joblib.load` has already executed the pickle, and only to decide whether to trust the metadata.

**Fix** (quick) — pass `weights_only=True` to `torch.load` (the checkpoint is a plain `state_dict`, so this works), and move the SHA256 verification **before** `joblib.load`, failing closed on mismatch.

**Effort:** quick fix.

---

### F-35 — Medium — Container hardening gaps

Both `Dockerfile` (root) and `agrobot-assistant/backend/Dockerfile` run the application as **root** — no `USER` directive anywhere. Neither declares a `HEALTHCHECK`. The frontend build stage uses `RUN npm install` (`Dockerfile:6`) rather than `npm ci`, so the committed `package-lock.json` is advisory: builds are non-reproducible and can silently pull newer transitive versions.

**Fix** (quick):

```dockerfile
RUN useradd --create-home --uid 10001 appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')"
```

and change `npm install` → `npm ci`.

**Effort:** quick fix.

---

### F-36 / F-37 — Low — Password handling details

`auth_utils.py:12-13`:

```python
# Password hashing — use lower rounds for faster hashing (default 12 is slow)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)
```

Cost 10 is ~4× cheaper to brute-force than the default 12. That trade-off is defensible on small instances, but it was made for latency reasons and `verify_password_async` already offloads to a thread, so the latency argument is weak. Given F-13 (no rate limiting), the two compound.

`auth_utils.py:25` — `safe_password = password[:72]` truncates by **characters**, while bcrypt's limit is 72 **bytes**. For a Hindi or Gujarati passphrase (3 bytes/char in UTF-8), 72 characters is 216 bytes. passlib 1.7.4 truncates silently rather than raising, so the practical effect is that only the first ~24 characters are significant — but the intent of the line is not met. Use `password.encode("utf-8")[:72]`.

`models/user.py:5-9` — `UserCreate.password: str` has no minimum length, no complexity requirement, and no maximum. `"a"` is an acceptable password.

**Fix** (quick) — raise rounds to 12, truncate by bytes, and add `password: str = Field(..., min_length=10, max_length=128)`.

**Effort:** quick fix.

---

### F-38 / F-39 — Low — LLM-derived content rendered and prompted without hardening

**Rendering** — `GovernmentSchemes.jsx:640` renders `href={scheme.apply_url}` and `MandiPrices.jsx:616` renders `href={item.source_url}`, both ultimately LLM-selected. Two mitigations already exist: `government_api_service.py:282` requires `apply_url.startswith("http")` before accepting it, and `crop_news_service.py:181-184` requires `source_url` to be one of the URLs actually returned by Tavily. React also escapes text content, and there is **no** `dangerouslySetInnerHTML` anywhere in the codebase — I checked. So this is hardening, not an open hole. The residual gap is that `startswith("http")` is a prefix check rather than a scheme parse.

**Prompting** — `prompt_generator.py:56-66` interpolates `context.state`, `district`, `previous_crop` and `farmer_goal` — all farmer free-text — into a JSON prompt payload, and `government_api_service.py:116-150` interpolates `location` into an f-string prompt with no delimiters. A user can write instructions into their own `farmer_goal`. The blast radius is small: the crop-explanation path allow-lists crop slugs (`ai_service.py:173-174`) and strips any output containing digits or currency symbols (`:229-235`), and the output is only shown back to the same user. The schemes path is less defended — a farmer could steer the model into emitting arbitrary `brief_description`/`eligibility` text — but again only into their own view.

**Fix** (quick) — validate the URL scheme before rendering (`new URL(u).protocol === 'https:'`), and wrap user free-text in the prompts with explicit delimiters plus a "treat the following as data, not instructions" preamble.

**Effort:** quick fix.

---

## 4. Dead code and redundancy

### Safe to delete

| Item | Location | Evidence |
|---|---|---|
| `_select_crop()` | `backend/app/routers/mandi_prices.py:29-44` | `grep -rn "_select_crop"` → only the definition |
| `MandiSnapshotResponse` | `backend/app/models/mandi_price.py:82` | Zero references outside its own class body |
| `oauth2_scheme` | `backend/app/routers/auth.py:11` | Shadows the one in `auth_utils.py`; never used in this module |
| Unused imports | `main.py:3` `Depends`; `auth.py:4` `UserLogin`, `:8` `timedelta`; `questionnaire.py:4` `UserResponse`, `:9` `Dict`,`Any`; `recommendations.py:2` `datetime` | AST scan, confirmed by textual grep |
| Dead `except` blocks | `backend/app/routers/disease.py:63-74` | `predict()` catches `FileNotFoundError`/`RuntimeError` internally at `:196`, so neither can reach the router |
| `getWeatherData()` | `frontend/src/services/api.js:193-196` | Calls `GET /api/weather?location=`, a route that does not exist; unused by any component |
| `backend/package-lock.json` | — | Empty stub (`"packages": {}`) in a Python project |
| `.gitignore:227` | — | Absolute local path `/Users/uday/Development/Agro-Bot/codex-telegram`; can never match, and leaks a local dev path |
| `if __name__ == "__main__"` demo | `backend/app/services/government_api_service.py:441-449` | `print()`-based manual demo in a production service module |

### Check first

| Item | Location | Why it needs a decision |
|---|---|---|
| Save-only schemes feature | `backend/app/routers/schemes.py:36-71` | `getSchemeRecords` and `updateSchemeRecord` exist in `api.js` but are called by **no** component. Users can save a scheme and never see it again. Either build the UI or remove the endpoints. |
| `/api/recommendations/history` | `recommendations.py:452` | Wrapper exists (`getRecommendationHistory`) but is never called. |
| `/api/disease/history` | `disease.py:83` | Same — `getDiseaseHistory` unused. |
| `createFarm` / `updateFarmCrop` | `api.js:103`, `:182` | Backend routes exist and work; no caller. Multi-farm support appears half-built. |
| `fertilizer_recommendations` | `models/recommendation.py`, `recommendations.py:42` | Stored and returned, but `crop_recommendation_service` never populates it — always `[]`. |
| `soil_health_score` | see F-18 | Never computed. Delete the field and its four UI surfaces, or implement it. |
| `RECOMMENDED` / `SUCCESS` enum paths | `crop_ranking_service.py:138-142`, `models/recommendation.py` | Currently unreachable (F-14). Keep — they are the target state — but track them as pending. |
| Training deps in runtime requirements | `requirements.txt:16,21,23` | `tqdm`, `matplotlib`, `pytest` are not used by `app/`; `matplotlib` alone adds ~40 MB. Move to `requirements-dev.txt`. |
| Duplicate Postgres drivers | `requirements.txt:6-7` | Both `psycopg2-binary` and `psycopg[binary]` installed; `connection.py:31` only ever rewrites toward `psycopg` v3. Drop `psycopg2-binary`. |
| Root `Dockerfile` vs `backend/Dockerfile` | — | Two divergent build definitions with different dependency sets (F-02). Pick one. |
| `test_api.py`, `test_expansion_api.py`, `test_phase1_api.py`, `test_mandi_price_service.py` | `backend/` | Standalone `asyncio` smoke scripts, not pytest tests — they are not collected by `pytest tests/`. Either convert them or move them to `scripts/`. They currently ship inside the root-Dockerfile image. |

---

## 5. Dependency vulnerability summary

### Python — `pip-audit -r requirements.txt` → **42 vulnerabilities in 7 packages**

| Package | Pinned | Advisories | Fix | Reachability |
|---|---|---|---|---|
| `python-multipart` | 0.0.6 | 11 (`PYSEC-2024-38`, `PYSEC-2026-1850/1851/1852`, `PYSEC-2026-3036…3040`) | 0.0.31 | **Direct** — parses every login form and both uploads |
| `starlette` | 0.27.0 (via fastapi) | 11 (`PYSEC-2026-1943`, `-1941`, `-161`, `-2280/2281`, `-248/249`) | 0.40.0 → 1.3.1 | **Direct** — `PYSEC-2026-1943` is the multipart memory DoS, compounding F-07 |
| `python-jose` | 3.3.0 | 5 (`PYSEC-2024-232`, `-233`, `PYSEC-2025-185`) | 3.4.0; `-185` unfixed | **Direct** — every `get_current_user` call |
| `fastapi` | 0.104.1 | 1 (`PYSEC-2024-38`) | 0.109.1 | Direct |
| `anyio` | 3.7.1 | 2 (`CVE-2026-63374`, `CVE-2026-64847`) | 4.14.2 | Transitive (starlette/httpx) |
| `python-dotenv` | 1.0.0 | 1 (`PYSEC-2026-2270`) | 1.2.2 | Startup only |
| `ecdsa` | 0.19.2 | 1 (`PYSEC-2026-1325`) | **no fix** | Transitive via `python-jose`; disappears if you migrate to PyJWT |

Also worth flagging even without a CVE: `passlib` 1.7.4 has had no release since 2020 and is effectively abandoned; `groq==0.4.1` is many major versions behind and pairs with `llama-3.2-11b-vision-preview` in `disease_inference_service.py:23`, a Groq model that has been retired — meaning the vision enrichment path most likely always falls back to boilerplate (**NEEDS-VERIFICATION**, requires a live API key). `tavily-python` and `Pillow>=10.0.0` are unpinned, so builds are not reproducible.

### JavaScript — `npm audit --omit=dev` → **57 vulnerabilities (2 critical, 27 high, 16 moderate, 12 low)**

Almost all of it is the `react-scripts@5.0.1` build-tool tree — `nth-check`, `postcss`, `svgo`, `webpack-dev-server`, `shell-quote`, `serialize-javascript`, `workbox-*`. These execute at **build time**, not in the shipped bundle, so the practical risk is compromised-build-input rather than runtime exposure. `react-scripts` has been unmaintained since 2022; migrating to Vite would eliminate the bulk of these in one move.

The one that ships to users is **`axios` (installed 1.13.6, vulnerable range 1.0.0–1.17.0, high)** — "Unrestricted Cloud Metadata Exfiltration" and "Allocation of Resources Without Limits". Bump `axios` to the patched line; this is a one-line change.

---

## 6. What I did not check, and why

- **No running instance.** I did not start the API or the frontend, so nothing here is confirmed against live behaviour. Every finding is traced through source; where the code path could not be executed I have said `NEEDS-VERIFICATION` explicitly (F-26, F-27, and the retired-Groq-model note in §5).
- **The ML model could not be loaded.** `import xgboost` fails in this repository's `.venv` because the installed `scipy` binary is incompatible with this macOS/Python build (`_spropack.cpython-310-darwin.so … zero-fill section type`). That is a local environment problem, not a repo defect — but it is why 8 of 46 tests fail (`tests/test_safe_crop_recommendations.py`, all with `MODEL_UNAVAILABLE` instead of the expected status) and why I could not empirically confirm F-26. The remaining **38 tests pass**.
- **`pytest` is listed in `requirements.txt` but is not installed** in the project venv, so the suite has to be run via `python -m unittest discover -s tests`. Worth fixing as part of F-24.
- **No Docker build.** I did not build either image, so F-02, F-26 and F-27 are reasoned from the Dockerfiles rather than observed. Building the root image and running `python -c "import torch, xgboost, joblib"` inside it would settle all three in minutes.
- **No live third-party calls.** I did not exercise Groq, Tavily, OpenWeather or Agmarknet, so the F-08 latency estimates are derived from the loop structure and configured timeouts, not measured.
- **No database introspection beyond schema.** At your request I stopped querying `agrobot.db` partway through, so the F-18 claim that `soil_health_score` is always `NULL` rests on static analysis (the field is read in seven places and written in none) rather than on row counts.
- **`ml-cnn/` training code, `train_xgboost_crop.py`, `split_dataset.py`, `experiments.ipynb`** — reviewed only for what they reveal about the artifacts. Training-pipeline correctness (train/test leakage, class balance, augmentation) was out of scope; given F-11, an independent review of how the disease model was trained and evaluated would be worthwhile.
- **`frontend/build/`** — the committed build output was not audited; it is stale relative to `src/` and gitignored.
- **No dynamic security testing.** No fuzzing, no authenticated scanning, no attempt to actually exploit any finding. The injection analysis is static: I found no raw SQL anywhere (everything goes through the SQLAlchemy ORM), no `eval`/`exec`/`pickle.loads` on user input, no `yaml.load`, and the one `subprocess` call (`mandi_price_service.py:133-139`) uses an argument list with no shell and is disabled by default — so the `ILIKE` wildcard issue in F-09 is the closest thing to an injection in the codebase.
- **Infrastructure itself.** There is no IaC in the repo — no Terraform, CloudFormation, ECS task definition or App Runner config. IAM policies, security groups, TLS configuration, WAF rules and Secrets Manager permissions are all described only in prose in `docs/neon-aws-deployment.md` and could not be audited.
- **Git history** was scanned for secrets across all 24 commits (`git log -p --all` against patterns for Groq/Tavily/AWS/OpenAI keys, private key headers, and Postgres URIs with embedded credentials) — **clean**. The working tree is clean too; `backend/app/.env` holds real keys but is correctly untracked and correctly excluded by both `.dockerignore` files.
