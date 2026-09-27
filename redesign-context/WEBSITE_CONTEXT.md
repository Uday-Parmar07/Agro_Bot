# AgroBot Assistant — Current Website Context

Reference document for a Google Stitch redesign. Everything below is read from the
codebase at `agrobot-assistant/frontend/` unless marked `[UNVERIFIED]`.

- Captured: 2026-09-27
- Git branch: `main` @ `b015ba4`
- Source of truth: `agrobot-assistant/frontend/src/`
- Nothing in the site code was modified to produce this document.

---

## 1. Site overview

### What it is

AgroBot Assistant is a **React single-page web application** — an AI-powered
agricultural advisory dashboard for Indian farmers. It is not a content site or blog;
it is a logged-in product with one public marketing landing page in front of it.

The product's job, in its own words (from `public/index.html` and `README.md`):

> "Agricultural Dashboard - Monitor and optimize your farming operations with real-time insights"

> "Agrobot is an AI-powered agricultural assistant platform designed to empower farmers
> with personalized, data-driven insights to optimize crop yields, resource usage, and
> sustainable farming practices."

### Who it is for

Three audiences are visible in the code:

| Audience | Evidence | What they need |
| --- | --- | --- |
| **Indian smallholder farmers** (primary) | Full Hindi translations, `Rs. …/q` mandi prices, Aadhaar/Khasra document checklists, `INDIAN_STATES` list, acre/hectare/bigha units, voice input, text-to-speech, "Don't Know" answer options | Plain-language, low-literacy-friendly, one clear action at a time, works on a cheap phone |
| **Agricultural advisors / admins** | `/advisor` route gated by `RoleRoute roles={['advisor','admin']}`, per-farmer risk flags | Scan many farmers, spot risk |
| **Agricultural analysts** | Home page copy: "helps farmers and agricultural analysts make smarter decisions" | Trends, charts, exports |

### What the redesign should communicate

The current app is unusually **honest about uncertainty** — this is its defining product
trait and must survive the redesign. Everywhere a value is unknown it says so rather
than faking a number:

- `"Not assessed"`, `"Not available"`, `"No data"`, `"Unavailable"`, `"insufficient data"`
- `"Development mock weather — not live conditions"`
- `"Verified matches: 6 / Unverified checks: 2"`, `"Could not verify: rainfall"`
- `"Soil values: estimated"` vs `"measured"`
- `"We need more information"` instead of a fabricated recommendation
- A `Technical details` disclosure with model version, catalogue version, generation
  mode and raw feature values

So the personality to design for is: **trustworthy, plain-spoken, decision-first,
never overclaiming.** Not a slick AI marketing dashboard.

### Stack

| Thing | Value |
| --- | --- |
| Framework | React 18.2 SPA, **Create React App** (`react-scripts` 5.0.1) — no Next.js/Astro/Hugo |
| Routing | `react-router-dom` 6.3, `BrowserRouter` (`src/index.js`) |
| Icons | `lucide-react` 0.263.1 + literal emoji in JSX |
| i18n | `i18next` / `react-i18next` (en, hi) — `src/i18n.js` |
| HTTP | `axios`, bearer token from `localStorage` — `src/services/api.js` |
| Styling | **Hand-written plain CSS, one file per component.** No Tailwind, no SCSS, no CSS-in-JS, no theme file, **no CSS custom properties** |
| Charts | Hand-rolled: `<div>` bars with inline `height:%`, one inline `<svg>` polyline sparkline. No chart library |
| State | React hooks + one `AuthContext`. No Redux |
| Theme | No theme toggle, no `prefers-color-scheme`. Fixed appearance per page (see §4) |
| Build | `npm run build` → `frontend/build/` (gitignored) |
| Dev serve | `npm start` → `localhost:3000` |
| API base | `process.env.REACT_APP_API_URL` ?? `http://localhost:8000/api`; prod = `https://agrobot-api.icypond-baef2cca.eastasia.azurecontainerapps.io/api` |
| Backend | FastAPI + SQLAlchemy, Groq Cloud LLM, OpenWeatherMap, Agmarknet mandi data |
| Analytics | Google Analytics `G-5KBTS5VNTX` hardcoded in `public/index.html` |

There is **no theme** in the Hugo/Jekyll sense and **no design system file** — every
colour and size is a literal value repeated across 13 CSS files.

---

## 2. Sitemap

All routes are declared in `src/App.jsx`. There are **no dynamic/parameterised routes**
and no blog, tags, or post collection.

| URL path | Source file | Access | Template |
| --- | --- | --- | --- |
| `/` | `src/pages/Home.jsx` + `Home.css` | Public | Marketing landing |
| `/login` | `src/pages/Login.jsx` + `Auth.css` | Public only (redirects to `/dashboard` if signed in) | Centred auth card |
| `/signup` | `src/pages/Signup.jsx` + `Auth.css` | Public only | Centred auth card |
| `/questionnaire` | `src/pages/Questionnaire.jsx` + `Questionnaire.css` | Protected | 5-step wizard |
| `/dashboard` | `src/components/Dashboard.jsx` + `Dashboard.css`, `dashboard/DecisionWidgets.css` | Protected | Sidebar app shell |
| `/analytics` | `src/pages/Analytics.jsx` + `Analytics.css` | Protected | Full-width light report |
| `/disease-checkup` | `src/pages/DiseaseCheckup.jsx` + `DiseaseCheckup.css` | Protected | 3-step centred flow |
| `/government-schemes` | `src/pages/GovernmentSchemes.jsx` + `GovernmentSchemes.css` | Protected | 3-step + slide-over |
| `/mandi-prices` | `src/pages/MandiPrices.jsx` + `components/MandiPrices.css` | Protected | 2×2 card grid |
| `/advisor` | `src/pages/AdvisorDashboard.jsx` + `FeaturePages.css` | Role: `advisor` \| `admin` | Auto-fit card grid |
| `*` | — | Any | **`<Navigate to="/" replace />` — there is no 404 page** |

**Route guards** (`src/App.jsx`):
`ProtectedRoute` → `/login` if unauthenticated. `PublicRoute` → `/dashboard` if
authenticated. `RoleRoute` → `/dashboard` if role doesn't match. While
`AuthContext.loading` is true all three render the same bare
`.loading-screen` with a spinner and the text `Loading...`.

### Dashboard sub-views (not routes)

`/dashboard` holds five tabbed views in local state (`activeTab`), so they share the
URL. Screenshots are captured separately for each.

| Tab | `activeTab` | Contents |
| --- | --- | --- |
| Dashboard | `dashboard` | The full decision stack (see §3.5) |
| My Crops | `crops` | `CropMonitor` only |
| Weather | `weather` | `WeatherWidget` only |
| Farm Insights | `insights` | `UpcomingTasks` + `AdvicePanels` |
| Settings | `settings` | One language `<select>` (English / Hindi) — that is the entire settings page |

### Shared layout — there isn't one

This is the single biggest structural finding: **no shared layout, header, or footer
component exists.** `App.jsx` renders only `<AppRoutes />` inside a `div.App`.

- **No site-wide header.** Four pages each hand-roll their own near-identical header:
  `.dc-header` (DiseaseCheckup), `.gs-header` (GovernmentSchemes),
  `.mandi-page-header` (MandiPrices), `.feature-header` (Advisor). Each has its own
  logo block and its own "← Dashboard" back link.
- **No footer anywhere on the site.** Not on the landing page, not in the app.
- **No global nav on the public landing page** — `/` has no way to reach `/login`
  except the two hero buttons; no persistent logo or nav bar.
- The only genuinely reused components are `DecisionSidebar`, `CropMonitor`,
  `WeatherWidget`, `AddCropModal`, `MandiPriceTeaser` and the `DecisionWidgets` set —
  all of them dashboard-internal.

### Reusable components inventory

| Component | File | Used by |
| --- | --- | --- |
| `DecisionSidebar` | `components/dashboard/DecisionWidgets.jsx` | Dashboard only |
| `TodayOnFarm`, `StatusCards`, `AlertsPanel`, `WeatherOverview`, `FarmSummary`, `CropRecommendationsGrid`, `UpcomingTasks`, `CropGrowthProgress`, `AdvicePanels`, `AskAgroBotFab` | same file | Dashboard |
| `CropMonitor` | `components/CropMonitor.jsx` | Dashboard (main + Crops tab) |
| `WeatherWidget` | `components/WeatherWidget.jsx` | Dashboard (Weather tab) |
| `MandiPriceTeaser` | `components/MandiPriceTeaser.jsx` | Dashboard |
| `AddCropModal` | `components/AddCropModal.jsx` | Dashboard |
| `useVoiceRecorder` | `hooks/useVoiceRecorder.js` | DiseaseCheckup, Questionnaire |
| `speakText` | `utils/speech.js` | DiseaseCheckup, GovernmentSchemes |

---

## 3. Per-page content breakdown

Data source legend: **hardcoded** = literal in JSX, **API** = fetched from the FastAPI
backend, **i18n** = `src/i18n.js` resource bundle, **local i18n** = a page-local `T`
object, **form state** = user input.

---

### 3.1 `/` — Home (landing page)

**Purpose:** Convince a farmer or analyst to sign up for the AI farm dashboard.
**Appearance:** Light theme, emerald green accent. Max content width 1200px.
**Data:** 100% hardcoded in `Home.jsx`. Not translated — English only.

#### Section 1 — Hero (`header.hero-section`, two-column grid 1fr 1fr, gap 60px)

- **H1:** "Smart Agriculture with" + `<span class="gradient-text">` "AI-Powered Insights"
  (green→cyan gradient clipped to text)
- **Body:** "Transform your farming operations with real-time monitoring, predictive
  analytics, and intelligent recommendations. Make data-driven decisions that maximize
  yield and optimize resource usage."
- **CTAs:** `Get Started` (primary, `Zap` icon, → `/signup`) · `View Demo`
  (secondary, `ArrowRight` icon, → `/analytics`)
- **Right column visual:** a **fake browser-chrome mock of the dashboard**, CSS-only:
  - Traffic-light dots (red `#ef4444`, amber `#f59e0b`, green `#10b981`), title
    "AgroBot Dashboard"
  - Two stat chips: `Leaf` "12 Active Fields", `Cloud` "24°C Optimal"
  - A five-bar chart with inline heights `60% 80% 45% 90% 70%` — decorative, no data
  - Whole card rotated `perspective(1000px) rotateY(-5deg) rotateX(5deg)`

#### Section 2 — Features (`section.features-section`, white bg, 3-col grid, gap 40px)

- **H2:** "Comprehensive Farm Management"
- **Sub:** "Everything you need to monitor and optimize your agricultural operations"
- Three cards from the hardcoded `features` array. Each: 64×64 mint tile with a 32px
  green Lucide icon, H3, body.

| Icon | Title | Description |
| --- | --- | --- |
| `Leaf` | Real-time Crop Monitoring | "Monitor crop health, soil moisture, and temperature with live sensor data and AI-powered insights." |
| `Cloud` | Weather Intelligence | "Get accurate weather forecasts and alerts to make informed decisions about irrigation and harvesting." |
| `BarChart3` | Analytics & Insights | "Analyze historical data, predict yields, and optimize farming operations with advanced analytics." |

#### Section 3 — Benefits (`section.benefits-section`, `#f9fafb` bg, 2-col grid)

- **H2:** "Why Choose AgroBot?"
- **Body:** "Our AI-powered agricultural dashboard helps farmers and agricultural
  analysts make smarter decisions with real-time data and predictive insights."
- Six `CheckCircle` list items from the hardcoded `benefits` array:
  1. "Increase crop yield by up to 25%"
  2. "Reduce water usage by 30%"
  3. "Early disease detection and prevention"
  4. "Optimize fertilizer and pesticide usage"
  5. "Real-time alerts and notifications"
  6. "Historical data analysis and reporting"
- **Right column — `.stats-showcase`**, 2-col grid where the third tile spans both:
  `25%` / "Yield Increase" · `30%` / "Water Savings" · `24/7` / "Monitoring"

#### Section 4 — CTA (`section.cta-section`, green gradient bg, centred, white text)

- **H2:** "Ready to Transform Your Farm?"
- **Body:** "Start monitoring your crops and optimizing your operations today"
- **CTA:** `Get Started Now` + `ArrowRight` → **`/dashboard`** (inconsistent with the
  hero CTA, which goes to `/signup`; an anonymous visitor is bounced to `/login`)

*No nav bar. No footer. No testimonials, pricing, FAQ, screenshots of the real product,
or contact details.*

---

### 3.2 `/login` — Sign in

**Purpose:** Authenticate an existing user.
**Appearance:** **Dark** navy gradient, **blue** accent — the opposite of the landing page.
**Data:** hardcoded labels (English only) + form state; posts to `/auth/login`.

Single centred `.auth-card`, max-width 480px, radius 20px, 40px padding:

- Logo row: `Leaf` icon (`#60a5fa`) + "AgroBot"
- **H1:** "Welcome Back" · **Sub:** "Sign in to your agricultural dashboard"
- Error banner (red, only on failure) — text comes from the API `detail`
- Field `Email Address` — `Mail` leading icon, placeholder "Enter your email", required
- Field `Password` — `Lock` leading icon, placeholder "Enter your password", required,
  trailing `Eye`/`EyeOff` visibility toggle
- Submit `Sign In` → `Signing In...` while pending. Full width, blue gradient
- Footer: "Don't have an account? **Sign up here**" → `/signup`

**Post-login routing:** `is_new_user` or `!onboarding_completed` → `/questionnaire`,
otherwise `/dashboard`.

---

### 3.3 `/signup` — Create account

Same shell and styling as `/login`.

- **H1:** "Create Account" · **Sub:** "Join thousands of farmers using smart agriculture"
- Fields in order, all with leading icons:
  1. `Full Name` (`User`) — "Enter your full name", required
  2. `Email Address` (`Mail`) — "Enter your email", required
  3. `Phone Number (Optional)` (`Phone`) — "Enter your phone number"
  4. `Password` (`Lock`) — "Create a password", required, visibility toggle
  5. `Confirm Password` (`Lock`) — "Confirm your password", required
- Client validation messages (hardcoded): "Passwords do not match",
  "Password must be at least 6 characters long"
- Submit `Create Account` → `Creating Account...`
- Footer: "Already have an account? **Sign in here**" → `/login`
- On success → **always** `/questionnaire`

---

### 3.4 `/questionnaire` — Farm onboarding wizard

**Purpose:** Collect the soil / water / climate / practice data the crop model needs.
**Appearance:** Dark navy gradient, blue accent, single 800px column.
**Data:** The question bank is a **hardcoded `questionSets` object** in
`Questionnaire.jsx`; answers POST to `/questionnaire/submit-set` then
`/questionnaire/complete`; on refill, saved answers load from
`/questionnaire/user-responses`.

**Interstitials (full-screen, `.welcome-screen`):**
- On first visit, for a fixed **3000 ms**: "Welcome to AgroBot! 🌱" /
  "Let's get to know your farm better to provide personalized recommendations." +
  pulsing circle
- While generating: `Loader` spinner / "Generating Your Personalized Recommendations" /
  "Our AI is analyzing your farm data to create the perfect farming plan..."

**Chrome:** optional farm `<select>` (only when >1 farm) · 8px progress bar filled
`(currentSet / 5) * 100%` · "Step N of 5" · footer `← Previous` / `Next →` (last step:
`Complete & Generate AI Plan` + `Check`). Next is disabled until every non-optional
question in the set is answered.

**Structure of one question item:** `.question-label` (18px semibold) → control →
optional `.question-help` grey note. Text and number inputs additionally render a
`Voice` button that starts/stops `useVoiceRecorder` and writes the transcript into the
field.

**The five sets — 26 questions total:**

| # | Set title | Questions (id · type) |
| --- | --- | --- |
| 1 | 🧪 Soil Physical Properties | `soil_texture` select (Sandy/Loamy/Clayey/Silty/Don't Know) · `water_retention` select · `soil_top_layer` select |
| 2 | 🌱 Soil Fertility & Nutrients | `soil_test_done` radio Yes/No · then conditionally `npk_nitrogen`, `npk_phosphorus`, `npk_potassium`, `soil_ph` number · `soil_test_date` date (optional) · `yellowing_slow_growth` radio · `fertilizer_type` select (Organic/Chemical/Both/None) |
| 3 | 💧 Moisture & Irrigation | `irrigation_type` select (Canal/Borewell/Drip/Rainfed/Sprinkler) · `watering_frequency` select · `water_availability` select |
| 4 | 🌍 Environmental & Regional | `state` text · `district` text · `average_rainfall` number (optional, has help text) · `average_temperature` number (optional) · `total_area` number · `area_unit` select (Acre/Hectare/Bigha) · `season` select (Kharif/Rabi/Zaid/Year-round/Not sure) · `intended_sowing_date` date (optional) |
| 5 | 🌿 Organic Matter & Practices | `uses_organic_matter` radio · `organic_matter_types` checkboxes (Compost/Green Manure/Animal Dung, conditional) · `crop_residue_practice` select · `earthworms_present` radio · `previous_crop` text (optional) · `farmer_goal` select (Household food security/Market sale/Soil improvement/Lower water use/Not sure) |

Example question copy: *"Does your soil retain water for a long time or does it drain
quickly?"*, *"Have you noticed earthworms in your soil recently?"*. The help text on
`average_rainfall` reads: "Used as farm context only. The current crop model dataset
does not document a matching rainfall period."

Deep links work: `?refill=1`, `&farm_id=`, `&section=soil-fertility`, `&field=soil_test_done`
(jumps to the set and focuses the field). Used by the dashboard's "Complete assessment"
and "Add soil-test values" CTAs.

---

### 3.5 `/dashboard` — Decision dashboard

**Purpose:** Answer "what do I do on my farm today?" in one screen.
**Appearance:** Dark navy gradient, fixed 244px sidebar, blue accent.
**Data:** heavily API-driven. Parallel fetch of `/recommendations/latest`,
`/weather/overview`, `/questionnaire/user-responses`, `/dashboard/crops` for the
selected farm, each with its own `.catch(() => null)` fallback. Labels come from i18n.

**Loading state:** the whole page is replaced by `Loading your decision dashboard...`.

#### Sidebar (`DecisionSidebar`) — fixed, 244px, full height, scrollable

1. Logo: `Sprout` icon + "AgroBot"
2. Nav (11 items, `lucide` icon + i18n label). The first four and Settings switch tabs;
   the rest **navigate by `window.location.href`, forcing a full page reload**:
   Dashboard · My Crops · Weather · Farm Insights · Analytics · Disease Detection ·
   Update Farm Info · Government Schemes · Mandi Prices · *(Advisor — role-gated)* · Settings
3. `Quick Actions` block (uppercase 12px heading): `+ Add Crop` · `🔍 Check Disease` ·
   `🌦 Weather` · `💧 Irrigation Advice` — note emoji icons here vs Lucide icons above
4. Footer: user full name, user email, red `Logout` button

#### Main column

**Page header:** H1 "AgroBot Dashboard" (32px, white, text-shadow) + subtitle
"Daily farming decisions, alerts, and crop actions in one place" (i18n
`dashboard.subtitle`). A farm `<select>` appears at right only when >1 farm.

**Then, top to bottom:**

1. **`Today on Your Farm`** — up to 4 rows, each an emoji + bold title + note.
   Emoji chosen by keyword from the calendar event category: 🚜 land · 🌱 sow ·
   💧 irrigation · 🧪 fertiliser · 🐛 pest · ✅ default · ⚠️ weather · ℹ️ empty.
   Empty state: "No assessed tasks — Add a cultivated crop and its planting date to
   create a farm schedule."

2. **`StatusCards`** — 4-up grid, each a title + big value, border tinted by tone
   (green/amber/red):
   - `Farm Health Score` → `7.2 / 10` or `Not assessed`
   - `Soil Health Status` → Good ≥7.5 · Attention Needed ≥6 · Critical · Not assessed
   - `Alerts / Warnings` → count
   - `Today's Tasks` → count
   - If the score is null, an inset blue callout: "**Farm health not assessed** —
     Complete farm details or add a soil test to generate an assessment." +
     `Complete assessment` link deep-linking into the questionnaire

3. **3-column row (`1.3fr 1fr 1fr`)**
   - **`Alerts`** (`Bell`) — derived client-side, not from the API:
     soil score < 6.5 → warning "Low soil health detected"; rain probability > 60 →
     urgent "Rain expected tomorrow / Delay irrigation and protect fertilizer
     application."; otherwise good "No assessed alerts — Add measured farm information
     to enable condition-based alerts."
   - **`Weather Overview`** — 2×2 KPI tiles: `Thermometer` °C · `CloudRain` Rain % ·
     `Wind` km/h · `Droplets` humidity %. Each independently prints `Unavailable`.
     Shows `Weather unavailable` if nothing resolved, and a yellow banner
     "Development mock weather — not live conditions" when `_source === 'mock_fallback'`.
   - **`Farm Summary`** — 5 label/value tiles: Location, Soil Type, Farm Size,
     Current Season, Main Crops. Each defaults to `Not available` / `Not specified`.
     With no crops, an inline `Add crop` text button.

4. **2-column row (`1.5fr 1fr`)**
   - **`CropMonitor`** — see the card spec below
   - **`Crop Growth Progress`** — a 4-dot horizontal track: Seedling → Vegetative →
     Flowering → Harvest. Stage is computed from days since the first crop's planting
     date (<20 / <45 / <75 / else)

5. **`Mandi Prices` teaser** (`MandiPriceTeaser`) — H2 "Mandi Prices", sub "Local price
   and trend at a glance.", `View full mandi prices` link (or `Add Crop` when there are
   no crops). Body: crop name, `Rs. 2,380/q`, market name, and a trend pill with
   `TrendingUp`/`TrendingDown` + direction. Degrades to "Market prices are temporarily
   unavailable. Crop recommendations are unaffected."

6. **`Crop recommendations`** (`CropRecommendationsGrid`) — the most complex panel:
   - Header + `Generate / refresh` button (hidden when high-importance inputs are missing)
   - Coverage note: "AgroBot's ML model compared your farm against {count} trained crop
     classes. Additional crops are considered only from the verified crop knowledge base."
   - Optional notices: stale · template fallback · partial template · error
   - `Information to improve` warning panel listing input limitations
   - `Improve this recommendation` callout + deep-link actions (`Add sowing date`,
     `Add soil-test values`, `Review rainfall information`)
   - `Preliminary matches` heading when results are provisional
   - **3-up card grid.** One card =
     rank pill `#1` · crop name · three badges (suitability band / candidate status /
     source: "ML model + crop knowledge") · `Data reliability: medium` ·
     `Soil values: estimated` · `Verified matches: 6` + `Unverified checks: 2` ·
     `Could not verify: rainfall, soil test` · `Main reasons` (≤3 bullets) ·
     `Crop-specific warnings` (≤3) · `Next action:` · source links
   - Empty state `We need more information` + `Complete farm information` /
     `Add soil-test values`
   - `<details>` **Technical details**: model version, catalogue version, generation
     mode, model status, raw model inputs (`N=82, P=41, …`), environmental sources,
     per-crop product score and model match
   - Total items: 3 recommended crops in the captured state; the real count varies

7. **`Upcoming Farm Tasks`** — ≤5 rows: emoji, `date — activity`, description, and a
   priority pill (`high`/`medium`/`low` → red/amber/green)

8. **`AdvicePanels`** — 2-up: `Soil Improvement Tips` and `Irrigation Advice`, each a
   plain `<ul>` of ≤5 strings from the recommendation payload

9. **`Ask AgroBot` FAB** — fixed bottom-right pill (`MessageCircle`). Opens a panel:
   H3 "Ask AgroBot", "Quick help for daily decisions." and three **non-functional**
   prompt chips: "When should I irrigate my field?", "Which crop suits my soil?",
   "How to treat this disease?"

**`CropMonitor` card (one item):** crop name, variety (defaults to "Variety not
recorded"), status icon, `×` remove button, a health pill (colour from
Excellent `#34d399` / Good `#60a5fa` / Warning `#fbbf24` / Critical `#f87171` / default
`#94a3b8`), two metric tiles — `Soil Moisture` (`Droplets`, cyan) and `Temperature`
(`Thermometer`, orange), **both currently always `Not assessed`** because the dashboard
maps `moisture: null, temperature: null` — and a footer with "Updated {when}" and
"{n} acres". Grid is `auto-fit minmax(280px, 1fr)`.

**`CropMonitor` empty state:** 64px `Leaf`, H3 "No Crops Added Yet", "Add your first
crop to get disease detection, irrigation alerts, fertilizer recommendations, and yield
guidance.", optional `+ Add Your First Crop` button, plus an "🤖 AI Recommended Crops
for Your Farm:" list of ≤3 crops with suitability bands.

**`AddCropModal`:** overlay `rgba(0,0,0,.7)` + blur, 600px card, radius 20px. H2 "Add
New Crop" + `X`. An "AI Recommended Crops" block of clickable `Leaf` chips that prefill
the form. Then five required fields: `Crop Name` ("e.g., Rice, Wheat, Tomato"),
`Variety` ("e.g., Basmati, HD-2967"), `Area (in acres)`, `Planting Date`,
`Expected Harvest Date`. Actions: `Cancel` / `Add Crop`.

**`WeatherWidget` (Weather tab):** H2 "Weather Conditions" + `MapPin` location. A large
centred current-conditions card (80px icon tile, 56px temperature, condition text).
Then a 2×2 metric grid — `Humidity` %, `Wind` km/h, `Visibility` km, `Pressure` hPa,
each with its own coloured icon tile (blue/green/purple/amber). Then `3-Day Forecast` —
three cards with day, emoji (🌧️/☁️/☀️ picked by keyword), and high temp. Error state:
"Weather is currently unavailable. No mock values are being shown."

---

### 3.6 `/analytics` — Farm Analytics

**Purpose:** Show stored history — soil trend, crop mix, disease counts.
**Appearance:** **Light** (`#f8fafc` page, white cards, emerald accent) — the only
signed-in page that is not dark. Max width 1400px, 32px page padding.
**Data:** `/analytics/overview` for the selected farm; labels hardcoded, English only.

- **Header:** H1 "Farm Analytics" / "Comprehensive insights into your agricultural
  operations and performance metrics". Controls: a segmented time-range control
  `7 Days | 30 Days | 90 Days | 1 Year` (active = green fill), an optional farm
  `<select>`, and a green `Download` `Export Report` button.
- **4 overview cards** (`repeat(4, 1fr)`), each = small grey H3, Lucide icon, 28px
  value, caption:
  - `Soil Health` / `7.2/10` / "Latest generated recommendation" (`TrendingUp`, green)
  - `Disease Checks` / count / "Stored leaf analyses" (`Activity`, red)
  - `Active Crops` / count / "Persisted dashboard crops" (`BarChart3`, green)
  - `Adoption` / `66%` / "Recommended crops added" (`PieChart`, green)
- **2 chart panels:**
  - `Crop Mix` / "Persisted crops grouped by crop type" — one horizontal progress bar
    per crop: name, "3/4 active", green gradient fill, `75%` badge. Empty: "No crops
    added yet."
  - `Soil Score Trend` / "Scores from generated recommendation snapshots" — last 6
    points as 8px-wide vertical bars in a 200px-tall box, height = `score * 10`%,
    `title` tooltip `Soil score: 7.2/10`, `Soil Score` legend swatch. Empty: "No
    recommendation history yet."
- **`Key Insights & Recommendations`** — 3 cards, each a 48px tinted icon tile + H3 + body:
  - `Recommendation Adoption` — "66% of the latest recommended crops have been added to this farm."
  - `Weather History` — "96 daily weather snapshots saved for this farm."
  - `Disease Pattern` — "Tomato Early blight is the most frequent check result." /
    "No disease checks have been recorded yet."

**Known issues:** the time-range control is decorative — `timeRange` is in the effect's
dependency array but is never sent to the API, so all four buttons return the same data.
`Export Report` has no `onClick`.

---

### 3.7 `/disease-checkup` — Plant disease detection

**Purpose:** Photo → AI diagnosis → treatment.
**Appearance:** Dark, 800px centred column, 3-step indicator, mobile-first CSS.
**Data:** UI strings from a **page-local bilingual `T` object** (en + hi) with its own
`EN | हिं` toggle — this page does *not* use the shared i18n bundle. Results come from
`POST /disease/predict`.

**Header:** `Leaf` + "AgroBot" / "एग्रोबॉट" · `EN | हिं` toggle · `← Dashboard`
**Steps:** `Upload` → `Analyze` → `Results` (`अपलोड` / `जाँच` / `परिणाम`)

**Step 1 — Upload**
- 🔬 + H1 "Plant Disease Detection" / sub "Upload or capture a leaf image — AI will
  identify the disease and suggest treatment."
- Dashed drop zone: `Upload` icon, "Drag & drop leaf image here", "or",
  three buttons — `Upload Image` (blue gradient) · `Use Camera` (green outline,
  `capture="environment"`) · `Voice Note` / `Use Note`
- "JPG, PNG only • Max 10 MB" (enforced: `VALID_TYPES`, `MAX_SIZE = 10 MB`)
- `Tips for best results` — 3 tiles: ☀️ "Take photo in bright daylight" ·
  🎯 "Focus on a single leaf" · 🚫 "Avoid blurry or dark images"
- Errors: "Invalid format. Please upload JPG or PNG." · "Image too large. Max size is
  10 MB." · "Upload failed. Please try again." · "Network error. Check your connection
  and retry."

**Step 2 — Analyze**
- Image preview (max 380px, radius 16px) with a floating `Change Image` button
- Primary CTA `Analyze Leaf` (`Search` + `ChevronRight`, min-height 54px)
- While loading: a spinning ring + pulsing `Leaf`, "AI is scanning your leaf…", and an
  indeterminate progress bar

**Step 3 — Results**
- If `confidence < 0.45`: amber panel "Image unclear — the AI isn't confident enough.
  Try a clearer photo." + `Try Another Photo`
- Result card, border green when healthy / red when diseased:
  - Badge row: `AI-Powered Analysis` (purple gradient) · `LLM Enhanced` (green,
    conditional) · `Speak` (triggers `speechSynthesis`)
  - 90px thumbnail + a 48px circular status icon (`CheckCircle2` / `XCircle`) +
    H2 "Disease Detected" / "Healthy Leaf" + the class name with `_` stripped
    (e.g. "Tomato Early blight")
  - Confidence meter: label, bar, and `91.2%` — bar colour by threshold:
    ≥0.85 `#10b981`, ≥0.6 `#f59e0b`, else `#ef4444`
  - `Possible Cause` (`Bug`) · `Treatment` (`Pill`) · `<details>` `View Detailed
    Solution` (`ShieldCheck`) — all from the API response
  - Healthy variant: a `Shield` panel with the detailed message
- `Scan Another Leaf` (`RotateCcw`) resets to step 1

---

### 3.8 `/government-schemes` — Government schemes finder

**Purpose:** Match a farm profile to subsidy schemes and prep the paperwork.
**Appearance:** Dark, 800px column, 3-step indicator, right-hand slide-over. Visually
a near-clone of `/disease-checkup` (the two CSS files share the same header, step and
card patterns with `gs-`/`dc-` prefixes).
**Data:** `GET /recommendations/government-schemes`; page-local bilingual `T` object;
**most card fields are inferred client-side by regex**, not supplied by the API.

**Header / steps:** as DiseaseCheckup. Steps: `Your Farm Profile` →
`Best Schemes for You` → `Scheme Details`.

**Step 1 — Farm profile** (`Landmark` + H1 "Government Schemes" / "Find the best
schemes for your farm in 3 easy steps")
- `State` `<select>` — a hardcoded list of **27 Indian states** (no UTs), placeholder
  "Select your state"
- `Crop` text input — "e.g. wheat, rice, cotton"
- `Farm Size` — three-button segmented control `Small | Medium | Large`
- CTA `Find Best Schemes` (`Search`) → "Searching government schemes..." with a spinner

**Step 2 — Scheme cards** (`Sparkles` H2 + `← Your Farm Profile`, `RefreshCcw`, `🔊`)
- **Exactly the top 3** schemes, ranked by `rankScore` (match score, +10 if subsidy >40%,
  +5 if Easy)
- One card = optional `✨ AI Recommended` ribbon (first card only) · a category chip
  (💧 Irrigation · 🌱 Plantation · 🏠 Storage · 🚜 Equipment · ₹ Financial · 📄 General,
  inferred by regex on the name/description) · a subsidy chip (`55% subsidy` or `Info`) ·
  H3 scheme name · description · a **match bar** with `78% match` (amber→green gradient) ·
  three quick stats (💰 estimated benefit · 🟢/🟡/🔴 difficulty · ⏱️ `15-30 days`) ·
  `ChevronRight`
- Empty: `Landmark` + "No schemes found. Try adjusting your profile."
- Loading: skeleton bar + 3 skeleton cards
- `Official Government Links` grid: `🔗 myScheme Portal`
  (`https://www.myscheme.gov.in/`), `🏛 Dept. of Agriculture`
  (`https://agricoop.nic.in/`), plus up to 4 `📄` source PDFs from the API

**Step 3 — Slide-over panel** (480px, `#0f172a`, dimmed overlay)
- Category + subsidy chips, scheme name, description, a large match bar
- 3 stat tiles: `Estimated Benefit` · `Difficulty` · `Approval Time`
- `<details open>` `Eligibility` (`ShieldCheck`) · `<details>` `How to Apply` (`FileText`)
- `<details open>` `Documents Checklist` (`CheckCircle2`) — a tappable ⬜/✅ list.
  Documents are **inferred**, always starting `Aadhaar Card`, `Bank Passbook`, then
  conditionally `Land Record / Khasra`, `Income Certificate`, `Passport Photo`,
  `Ration Card`. Warning while incomplete: "Some documents are not ready yet"
- `Explain Simply` button → a 🤖 paragraph built by **string template on the client**,
  not by an LLM
- `✨ Why recommended?` — "78% match for your small farm in Maharashtra."
- Footer: `Apply on Official Portal` (green gradient, `ExternalLink`, opens the official
  URL) · `Prepare Documents` (just closes the panel) · `Save Scheme`

**Caveat for the redesign:** subsidy %, category, difficulty, approval time, document
list, match score and the "Explain Simply" text are all **heuristics computed in
`GovernmentSchemes.jsx`**, presented with the same visual confidence as real data.

---

### 3.9 `/mandi-prices` — Mandi (market) prices

**Purpose:** Tell a farmer what their crop fetches nearby, whether a further market is
worth the trip, where the price is heading, and why.
**Appearance:** Dark, 920px column, 2×2 card grid. Own header, `EN | हि` toggle.
**Data:** five endpoints — `/mandi-prices/current`, `/compare`, `/trend`, `/news`,
`/locations`, `/commodities` (debounced 250 ms search). Page-local bilingual `T`.
Language is seeded from `localStorage.preferred_language`.

- **Hero:** H1 "Mandi Prices" / "Check local crop value, better markets, price trend,
  and market news". Controls: optional farm select + a `Crop` combobox ("Search any
  Agmarknet crop") with up to 8 chips (saved crops tagged `Saved crops`) and an inline
  `Add to my crops` / `Added to my crops` button
- **Card 1 — `Local Price`:** market name; three cascading selects `State` /
  `District` / `Market` ("All states", "All districts", "Farm nearest mandi");
  a large modal price `Rs. 2,380/q`; a `Min | Modal | Max` row; a meta row with
  `MapPin` district and the price date; and `State avg` / `India avg`
- **Card 2 — `Worth the Trip`** (`Navigation`): note "Trip math is based on your farm
  location: Nashik, Maharashtra." Then a ranked list — "1. Pimpalgaon", "34 km -
  Rs. 2,520/q", and a net-gain figure `Rs. 2,840` with `ArrowUpRight`. Empty: "No
  better nearby mandi clears the net-gain threshold."
- **Card 3 — `30 Day Trend`:** date range, a direction pill (`up`/`down`/`no_data`)
  with `6.4%`, and a hand-rolled inline `<svg>` **sparkline** (polyline + per-point
  circles with `<title>` tooltips + three date ticks). Below it, when a matching
  headline exists, "This trend may be connected to **{headline}**." — matched by regex
  against the news list (`msp|hike|shortage|export demand` for up,
  `glut|surplus|drop|export ban` for down)
- **Card 4 — `Market News`** (`Newspaper`): ≤5 cards with headline, summary and a
  `Source ↗` link. Empty: "No relevant market news found for this crop today."
- Empty page state: `IndianRupee` + "Add a crop from the dashboard to check mandi
  prices." + `Add Crop` link

---

### 3.10 `/advisor` — Advisor dashboard

**Purpose:** Let an advisor scan assigned farmers.
**Appearance:** Flat `#0f172a` (no gradient), 1120px, `FeaturePages.css` — visibly the
least-finished page in the app.
**Access:** `advisor` or `admin` only.
**Data:** `/advisor/farmers`, `/advisor/farmers/{id}/summary`. All labels hardcoded,
English only, no i18n, no loading state, no empty state.

- Header: H1 "Advisor Dashboard" / "Assigned farmer history and risk flags." +
  a `Dashboard` link
- `auto-fit minmax(260px, 1fr)` card grid. One card = farmer name (H3), email,
  "Farms: 2", "Latest soil score: 6.8" (or `No data`), "Disease checks in 30 days: 3",
  and a `View Summary` button
- Selecting a farmer appends a single card **below the grid**: "{name} Summary",
  "Disease checks: 9", "Weather snapshots: 62", "Flags: …" / `None`

---

## 4. Current design system

There is **no design-system file**. No Tailwind config, no SCSS variables, no CSS custom
properties — `grep` for `--` custom properties in `src/**/*.css` returns only one
(`var(--height)` in an unused keyframe). Every value below is a literal repeated across
13 stylesheets, which is why the app drifts between two visual identities.

### 4.1 The two conflicting identities

| | **Identity A — "Marketing / Report"** | **Identity B — "App"** |
| --- | --- | --- |
| Pages | `/` (Home), `/analytics` | `/login`, `/signup`, `/questionnaire`, `/dashboard`, `/disease-checkup`, `/government-schemes`, `/mandi-prices`, `/advisor` |
| Background | `#f8fafc` → `#e2e8f0` light | `#0f172a` → `#1e293b` dark gradient |
| Surface | `white` | `rgba(30, 41, 59, 0.8)` + `backdrop-filter: blur(10px)` |
| Body text | `#1e293b` / `#6b7280` | `#f8fafc` / `#cbd5e1` / `#94a3b8` |
| Accent | **emerald `#059669`** | **blue `#60a5fa` / `#3b82f6`** |
| Primary button | flat `#059669` | gradient `#60a5fa → #3b82f6` |
| Radius | 8 / 12 / 16px | 8 / 12 / 14 / 20px |

There is no dark-mode toggle and no `prefers-color-scheme` query. The theme is simply
whichever one the page author chose. `index.css` sets a light `body`, `App.css`
immediately overrides it dark, and `Home.css`/`Analytics.css` paint light again on top.
Focus rings are green (`#059669`, from `index.css`) even on the blue-accented dark pages.

### 4.2 Colour palette (exact values, with usage)

Counts are occurrences across `src/**/*.{css,jsx,js}`.

**Neutrals — dark app scale (Tailwind Slate)**

| Hex | ×  | Used for |
| --- | --- | --- |
| `#0f172a` | 13 | Darkest page bg, gradient start, sidebar `rgba(15,23,42,.95)`, slide-over bg |
| `#1e293b` | 9 | Gradient end, card base `rgba(30,41,59,.8)` |
| `#f8fafc` | 61 | Primary text on dark; light page bg |
| `#cbd5e1` | 51 | Secondary text on dark, nav item idle |
| `#94a3b8` | 69 | **Most-used colour in the app** — muted/meta text, labels, icons |
| `#64748b` | 10 | Placeholder text, empty-state icons |
| `#e2e8f0` | 11 | Button text on dark, hero gradient end |
| `#f1f5f9` | 5 | `dc-`/`gs-` page text, scrollbar track |
| `#475569` | 1 | Placeholder icon |
| `#4b5563` | 1 | Loading shimmer highlight |
| `rgba(148,163,184,0.1–0.3)` | ~120 | **Every border in the dark UI** |

**Neutrals — light pages (Tailwind Gray)**

| Hex | × | Used for |
| --- | --- | --- |
| `#111827` | 9 | Headings on light (`h1`, `h2`, card values) |
| `#374151` | 5 | Body text on light, secondary button label |
| `#6b7280` | 14 | Muted text on light |
| `#9ca3af` | 1 | Secondary-button hover border |
| `#d1d5db` | 2 | Secondary-button border, preview dots |
| `#e5e7eb` | 6 | Card borders on light |
| `#f3f4f6` | 2 | Progress-bar track, insight-card border |
| `#f9fafb` | 6 | Benefits-section bg, insight-card bg, hover |
| `#ffffff` / `#fff` | 11 | Card surfaces, button text |

Note the app mixes **two** Tailwind neutral ramps (Slate on dark, Gray on light).

**Blue — the app accent**

| Hex | × | Used for |
| --- | --- | --- |
| `#60a5fa` | 34 | Logo icon, links, focus border, active nav text, primary-button gradient start, dashboard `.btn-primary` |
| `#3b82f6` | 15 | Gradient end, active step number, `feature-button`, progress-bar fill |
| `#2563eb` | 6 | `recommendation-action` link, `Ask AgroBot` FAB, CTA gradient end |
| `#93c5fd` | 19 | Small links, step numbers, `<summary>` text, inline text buttons |
| `#bfdbfe` | 7 | Source links, refresh button label, info-notice text |
| `#dbeafe` | 7 | Active language-toggle text |
| `#38bdf8` | 1 | Soil-moisture metric icon |
| `#eff6ff` | 1 | Insight icon tile (info) |

**Green — the marketing accent and "good" state**

| Hex | × | Used for |
| --- | --- | --- |
| `#059669` | 20 | Home/Analytics primary accent, focus outline, selection bg, theme-color meta, chart bars |
| `#047857` | 2 | Primary-button hover, CTA gradient end |
| `#10b981` | 7 | "good" borders, match-bar gradient end, apply-button gradient, traffic dot |
| `#34d399` | 10 | Healthy status icon, positive stat change |
| `#6ee7b7` | 4 | Rank pill, `good` priority pill text |
| `#a7f3d0` | 11 | `LLM Enhanced` badge, camera-button label |
| `#d1fae5` | 2 | Active growth-step label |
| `#ecfdf5` | 3 | Feature icon tile, efficiency badge, insight tile |
| `#f0fdf4` | 1 | Hero preview stat chip |
| `#22c55e` | 2 | `low` priority pill, wind metric icon |

**Amber — "attention"**

`#f59e0b` (5) warnings, preliminary left border, match-gradient start ·
`#fbbf24` (7) warning icons, temperature/pressure metric icons ·
`#fcd34d` (2) legacy note, warning pill text · `#fde68a` (9) warning banner text ·
`#fef3c7` (1) insight tile · `#d97706` (1) insight icon · `#fb923c` (1) temperature icon

**Red — "urgent"**

`#ef4444` (6) logout, remove-crop, error banner, traffic dot · `#dc2626` (3) negative
analytics icons, `feature-button.danger` · `#f87171` (4) critical health, diseased icon ·
`#fca5a5` (9) error-message text · `#fecaca` (2) error-notice text

**Purple — "AI"**

`#a855f7` (1) visibility metric icon · `#7c3aed` (2) analytics legend/bar (unused
series) · `#c4b5fd` (3) `AI-Powered Analysis` badge text

**Cyan** — `#0891b2` (3): hero gradient end, unused chart series

**Gradients in use**

```css
linear-gradient(135deg, #0f172a 0%, #1e293b 100%)    /* dark page bg (5 files) */
linear-gradient(160deg, #0f172a 0%, #1e293b 100%)    /* dc- / gs- page bg */
linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)    /* Home hero */
linear-gradient(135deg, #059669 0%, #0891b2 100%)    /* Home H1 clipped text */
linear-gradient(135deg, #059669 0%, #047857 100%)    /* Home CTA band */
linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)    /* app primary button */
linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)    /* dc- upload / CTA button */
linear-gradient(135deg, #10b981 0%, #059669 100%)    /* gs- apply button */
linear-gradient(90deg,  #059669, #10b981)            /* analytics progress fill */
linear-gradient(90deg,  #60a5fa, #3b82f6)            /* questionnaire progress */
linear-gradient(90deg,  #f59e0b, #10b981)            /* scheme match bar */
linear-gradient(to top, #059669, #10b981)            /* hero preview bars */
linear-gradient(135deg, rgba(168,85,247,.2), rgba(59,130,246,.2))  /* AI badge */
```

### 4.3 Typography

**Families**

- **Inter** — `300, 400, 500, 600, 700` from Google Fonts, `display=swap`, preconnected
  in `public/index.html`. Applied in `index.html`'s inline `<style>`, `index.css` and
  `App.css`.
- Fallback stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
  'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif`
- **`DiseaseCheckup.css` and `GovernmentSchemes.css` set their own family and omit
  Inter entirely**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.
  Those two pages render in the system font while the rest of the app renders in Inter.
- Code: `source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace` — declared
  in `index.css`/`index.html` but **the app never renders a `<code>` or `<pre>` block**,
  so there is no code-block style to carry over.

**Base:** `html { font-size: 16px; line-height: 1.5 }`. No modular scale — sizes are
picked ad hoc; 32 distinct `font-size` values appear across the CSS.

| Role | Size / weight / colour | Where |
| --- | --- | --- |
| Landing H1 | 48px / 700 / 1.2 / `#111827` | `.hero-title` |
| Welcome H1 | 48px / 700, gradient-clipped | `.welcome-content h1` |
| Landing H2 | 36px / 700 / `#111827` | `.section-header h2`, `.benefits-text h2`, `.cta-content h2` |
| Big stat | 36px / 700 / `#059669` · 36px / 700 / `#f8fafc` | `.stat-number` · `.stat-value` |
| Page H1 (app) | 32px / 700 / `#ffffff !important` + `text-shadow: 0 2px 4px rgba(0,0,0,.3)` + `letter-spacing: -0.025em` | `.page-title` |
| Page H1 (light) | 32px / 700 / `#111827` | `.analytics-header h1` |
| Temperature | 56px / 700 / 1 | `.temp-value` |
| Section H2 | 28px / 700 | `.question-set h2`, `.feature-header h1`, `.auth-header h1` |
| Card value | 28px / 700 / `#111827` | `.card-value` |
| Panel H2 | 24px / 600–700 | `.weather-header h2`, `.modal-header h2`, `.insights-section h2`, `.dc-upload-title h1` |
| Crop monitor H2 | 22px / 700 | `.header-left h2` |
| Sidebar logo | 20px / 700 | `.logo-text` |
| Panel title | 20px / 600 (Dashboard) · 18px (DecisionWidgets override) | `.panel-header h2` |
| Status value | 20px / bold | `.status-card strong` |
| Subtitle / lead | 18px / 400 / `#6b7280` (light) · `#cbd5e1` (dark) | `.hero-subtitle`, `.page-subtitle` |
| Question label | 18px / 600 / 1.4 | `.question-label` |
| Body | 16px / 1.5–1.6 | inputs, `.feature-card p`, `.btn` |
| Small / label | 14px (44×) | form labels, nav items, metadata |
| Micro | 13px (48×) / 12px (41×) | notes, chips, captions, badges |
| Tiny | 11px (14×) / 10px (2×) | badges, priority pills, step labels on mobile |

`line-height` is specified only occasionally (`1.2`, `1.35`, `1.4`, `1.45`, `1.5`,
`1.55`, `1.6`), so most text falls back to the global `1.5`.
`letter-spacing` appears four times: `-0.025em` (`.page-title`), `0.04em`
(sidebar Quick Actions heading), `0.5px` (weather metric labels), `0.3px` (AI badges).
`text-transform: uppercase` on priority pills, metric labels, forecast day, Quick Actions.

### 4.4 Spacing and layout

**No spacing scale.** Values used: `2 3 4 6 7 8 9 10 11 12 14 16 18 20 24 28 32 36
40 48 60 62 80 96 120 px`. Roughly 8px-ish, but 7/9/11/14/18 appear often enough
(mostly in `DecisionWidgets.css`, which uses 14px as its base gap) to break any rhythm.

| Container | Max width |
| --- | --- |
| Home `.container` | **1200px**, 24px side padding |
| Analytics `.analytics-container` | **1400px**, 32px page padding |
| Advisor `.feature-container` | **1120px**, 24px page padding |
| Mandi page | **920px**, 16–20px page padding |
| DiseaseCheckup / GovernmentSchemes | **800px**, 12/16/20px page padding |
| Questionnaire | **800px**, 20px page padding |
| Auth card | **480px** |
| AddCropModal | **600px** (90% width) |
| Scheme slide-over | **480px** |
| Dashboard main | **`calc(100vw - 244px)`** — no max width at all; stretches on ultrawide |

Six different content widths for one product.

**Grid systems in use** (all ad hoc, no shared column system):

```css
.hero-content            grid-template-columns: 1fr 1fr;                 gap 60px
.features-grid           repeat(3, 1fr);                                 gap 40px
.benefits-content        1fr 1fr;                                        gap 60px
.stats-showcase          repeat(2, 1fr) + last child spans both;         gap 24px
.analytics-overview      repeat(4, 1fr);                                 gap 24px
.analytics-charts        1fr 1fr;                                        gap 32px
.insights-grid           repeat(3, 1fr);                                 gap 24px
.status-grid             repeat(4, minmax(0,1fr));                       gap 10px
.decision-grid-3         1.3fr 1fr 1fr;                                  gap 14px
.decision-grid-2         1.5fr 1fr;                                      gap 14px
.recommendation-cards    repeat(3, minmax(0,1fr));                       gap 10px
.advice-grid             1fr 1fr;                                        gap 14px
.crops-grid              auto-fit minmax(280px, 1fr);                    gap 14px
.feature-grid            auto-fit minmax(260px, 1fr);                    gap 16px
.mandi-page-grid         minmax(0,1fr) minmax(0,1fr);                    gap —
.gs-card-stats           repeat(3, 1fr)
.weather metrics-grid    repeat(2, 1fr);                                 gap 16px
.widget-row              minmax(0,2fr) minmax(0,1fr);                    gap 24px
```

**Section padding:** landing sections `80px 0` (hero `80px 0 120px`); app panels
`14–24px`; auth card `40px`; question set `40px`.

**Sidebar:** `width: 244px`, `position: fixed`, `height: 100vh`, `overflow-y: auto`;
main column offset with `margin-left: 244px`.

**Breakpoints — five different sets, no shared system:**

| Breakpoint | Files |
| --- | --- |
| `max-width: 1200px` | `Dashboard.css`, `WeatherWidget.css` |
| `max-width: 1100px` | `DecisionWidgets.css`, `CropMonitor.css` |
| `max-width: 900px` | `Dashboard.css` (schemes block) |
| `max-width: 860px` | `MandiPrices.css` |
| `max-width: 768px` | `Dashboard.css`, `DecisionWidgets.css`, `AddCropModal.css` |
| `max-width: 720px` | `CropMonitor.css` |
| `max-width: 640px` + `min-width: 641px` | `DiseaseCheckup.css`, `GovernmentSchemes.css` |
| `max-width: 600px` | `Questionnaire.css` |
| **none** | **`Home.css`, `Analytics.css`, `Auth.css`, `FeaturePages.css`, `index.css`, `App.css`** |

### 4.5 Components

**Buttons** — `.btn` / `.btn-primary` / `.btn-secondary` are **redefined four times**
with different values (`Home.css`, `Dashboard.css`, `Questionnaire.css`,
`AddCropModal.css`). Whichever CSS file loads last wins on shared pages, so the same
class renders differently depending on route.

| Definition | Padding | Radius | Primary fill | Hover |
| --- | --- | --- | --- | --- |
| `Home.css` | `14px 24px` | 8px | flat `#059669` | `#047857` + `translateY(-2px)` |
| `Dashboard.css` | `12px 20px` | 8px | flat `#60a5fa`, text `#0f172a` | `#3b82f6` + `translateY(-1px)` |
| `Questionnaire.css` | `16px 32px` | 12px | gradient `#60a5fa→#3b82f6` | `translateY(-2px)` + blue glow |
| `AddCropModal.css` | `12px 24px` | 8px | gradient `#60a5fa→#3b82f6` | `translateY(-2px)` + blue glow |

Plus ~14 one-off button classes with their own geometry: `.auth-button` (full width,
16px, radius 12, blue gradient), `.dc-cta` (radius 14, min-height 54), `.gs-cta`,
`.gs-apply-btn` (green gradient, radius 14), `.add-first-crop-btn`, `.add-crop-btn`
(tinted ghost), `.recommendation-action` (flat `#2563eb`, radius 8),
`.recommendation-refresh`, `.sidebar-action-btn`, `.mandi-add-crop-btn`,
`.mandi-link-btn`, `.feature-button`, `.logout-btn` (red ghost), `.ask-agrobot-fab`
(fully round pill).
Minimum touch target is honoured only on `/disease-checkup` (`min-height: 48px`).

**Cards / panels**

| Class | Style |
| --- | --- |
| `.card` (`App.css`, unused in JSX) | `rgba(30,41,59,.8)`, 1px `rgba(148,163,184,.2)`, radius 12, padding 24, `blur(10px)`, `0 4px 6px -1px rgba(0,0,0,.3)` |
| `.panel` | same surface, radius **16**, padding 20, `blur(8px)`, `0 10px 30px -12px rgba(0,0,0,.4)` |
| `.decision-panel` | overrides `.panel` → radius **14**, padding **14** |
| `.status-card` | `rgba(30,41,59,.8)`, radius 12, padding 12, border tinted by tone |
| `.recommendation-card` | `rgba(15,23,42,.5)`, radius 10, padding 10 |
| `.crop-card` | `rgba(51,65,85,.4)`, radius 12, padding 14 |
| `.overview-card` (light) | white, `#e5e7eb` border, radius 12, padding 24; hover `0 4px 6px -1px rgba(0,0,0,.1)` |
| `.feature-card` (Advisor) | `rgba(30,41,59,.82)`, radius **8**, padding 18 |
| `.mandi-panel` | `rgba(30,41,59,.82)`, radius **8**, padding 20 |
| `.gs-card` / `.dc-upload-card` | `rgba(15,23,42,.6)`, radius **20** |

Four surface alphas (`.5`, `.6`, `.8`, `.82`, `.95`), radii from 8 to 20, and padding
from 10 to 24 — for the same conceptual "card".

**Navigation**

- `.nav-item` — 12/16px padding, radius 8, 14px, `#cbd5e1`; hover
  `rgba(59,130,246,.1)` + `#f8fafc`; active `rgba(59,130,246,.2)` + `#60a5fa`;
  focus `outline: 2px solid #60a5fa; offset 2px`. Icon 18px + label.
- Sidebar is **not sticky-collapsible** — it is `position: fixed` and, under 768px,
  simply `transform: translateX(-100%)`. **There is no hamburger, drawer, or bottom
  bar** anywhere in the app, so on a phone the entire primary navigation is unreachable
  from `/dashboard`.
- Per-page headers (`.dc-header`, `.gs-header`, `.mandi-page-header`,
  `.feature-header`) are plain flex rows: logo left, `EN | हि` toggle + `← Dashboard`
  right. Not sticky.
- Step indicators (`.dc-steps`, `.gs-steps`): equal-flex pills, `opacity .4` →
  `.65` (done) → `1` (current), current gets a blue tint and a filled 28px numbered
  circle.

**Tags / chips / pills**

| Class | Style |
| --- | --- |
| `.suitability-band` / `.source-badge` / `.candidate-status` | radius 999px, `4px 8px`, 11px, tinted bg + matching text |
| `.priority` (DecisionWidgets) | radius 999px, `4px 8px`, 11px, capitalised |
| `.priority` (Dashboard.css) | radius **4px**, `4px 8px`, **10px**, uppercase — a second, conflicting definition of the same class |
| `.health-badge` | radius 999px, `6px 10px`, 12px/600, colour set inline in JS with `+'20'` / `+'40'` alpha-hex suffixes |
| `.crop-rank` | 28px circle, `rgba(16,185,129,.18)`, `#6ee7b7`, 700 |
| `.gs-card-cat` / `.gs-card-subsidy` | radius 999px, variants `high` green / `med` blue / `info` grey |
| `.stat-change` | radius 6px, 12px, variants `up` / `stable` / `warning` |
| `.efficiency-badge` (light) | radius 4px, `#ecfdf5` bg, `#059669` |
| `.dc-ai-badge` | radius 8px, purple→blue gradient, `#c4b5fd`, `letter-spacing .3px` |

**Forms**

- Dark inputs (`Auth.css`, `Questionnaire.css`, `AddCropModal.css`):
  `padding: 16px` (48px left when there's a leading icon), bg `rgba(51,65,85,.6)`,
  border `1px rgba(148,163,184,.2)`, radius 12, text `#f8fafc`, placeholder `#64748b`,
  `transition: all .2s`. **Focus:** `outline: none` replaced by
  `border-color: #60a5fa` + `box-shadow: 0 0 0 3px rgba(96,165,250,.1)`.
- `index.css` global focus is `outline: 2px solid #059669; offset 2px` — green, and
  overridden by the above on most real inputs.
- `.radio-option` / `.checkbox-option` are full-width 16/20px tappable rows,
  `rgba(51,65,85,.4)`, radius 12, `accent-color: #60a5fa`.
- Error message: `rgba(239,68,68,.1)` bg, `rgba(239,68,68,.3)` border, `#fca5a5` text,
  radius 8, centred.
- Selects are **unstyled native `<select>`** in several places
  (`.questionnaire-farm-select select`, Analytics farm select reusing `.time-btn`,
  `.gs-field select`), so they render with OS chrome against a dark card.

**Code blocks** — none exist. The `code` font-family declaration is dead CSS.

**Footer** — none exists anywhere in the app.

**Modal / slide-over**

- `.modal-overlay`: `rgba(0,0,0,.7)` + `backdrop-filter: blur(5px)`, `z-index: 1000`,
  `fadeIn .3s`. `.modal-content`: radius 20, padding 32, `max-height: 90vh`,
  `overflow-y: auto`, `0 25px 50px -12px rgba(0,0,0,.5)`, `slideIn .3s`
  (`translateY(-20px) scale(.95)` → rest).
- `.gs-overlay` + `.gs-panel`: right-edge slide-over, 480px, flat `#0f172a`, sticky
  header and footer. Neither the modal nor the panel traps focus or closes on `Escape`.

### 4.6 Visual details

**Border radius** — no scale. Counts: `8px` ×41, `12px` ×35, `16px` ×16, `10px` ×23,
`14px` ×14, `6px` ×10, `4px` ×9, `20px` ×9, `999px`/`99px` ×17, `50%` ×6, `3px` ×5,
`18px` ×2, `2px 2px 0 0` ×2, plus `0.375rem`/`0.5rem` in utility classes.

**Shadows**

```css
0 4px 6px -1px rgba(0,0,0,.3)        /* .card */
0 10px 25px -5px rgba(0,0,0,.4)      /* .card:hover */
0 10px 30px -12px rgba(0,0,0,.4)     /* .panel */
0 8px 25px -8px rgba(0,0,0,.3)       /* metric / forecast card hover */
0 12px 28px -8px rgba(0,0,0,.4)      /* overview stat hover */
0 20px 25px -5px rgba(0,0,0,.4)      /* auth card */
0 25px 50px -12px rgba(0,0,0,.5)     /* modal */
0 10px 25px rgba(96,165,250,.3)      /* blue button hover glow */
0 14px 22px -12px rgba(37,99,235,.85)/* Ask AgroBot FAB */
0 20px 25px -5px rgba(0,0,0,.1)      /* light: dashboard preview, feature hover */
0 4px 6px -1px rgba(0,0,0,.1)        /* light: showcase stat, overview hover */
```

**`backdrop-filter: blur(…)`** — 8px (`.panel`), 10px (sidebar, `.card`, auth card,
modal, widgets, weather cards), 5px (modal overlay), 4px (`.dc-change-img`). Applied
to ~12 surfaces; only the sidebar and `.widget-*` add the `-webkit-` prefix.

**Transitions** — `all 0.2s ease` (most), `all 0.3s ease` (cards, buttons),
`all 0.15s` (`dc-`/`gs-` buttons), `width .3s ease` (progress bars),
`height .3s ease` (chart bars), `color .2s ease` (password toggle),
`background .2s ease` (scheme head), `opacity .2s` (`.dc-cta`).
`all` transitions are the norm, which animates layout properties unintentionally.

**Animations / keyframes**

| Name | What it does | Where |
| --- | --- | --- |
| `growBar` | hero preview bars grow from 0 — **broken**, it animates `var(--height)` which is never set | `Home.css` |
| `loading` | 1.5s shimmer sweep on `.stat-value.loading` | `Dashboard.css` |
| `slideInUp` | stat cards fade + rise 30px, staggered 0.1–0.4s | `Dashboard.css` |
| `spin` | 1s linear spinner | `Dashboard.css` |
| `pulse` | 2s scale 1→1.1 breathing circle | `Questionnaire.css` |
| `fadeIn` / `slideIn` | modal entrance, 0.3s | `AddCropModal.css` |
| `dc-fadeIn`, `dc-spin`, `dc-pulse`, `dc-progress` | scan ring, pulsing leaf, indeterminate bar | `DiseaseCheckup.css` |
| `gs-spin`, skeleton pulse | refresh spinner, loading skeleton | `GovernmentSchemes.css` |
| `mandi-spin` | loader | `MandiPrices.css` |

No `prefers-reduced-motion` guard anywhere.

**Hover transforms** — `translateY(-1px)`, `-2px`, `-4px`, `-8px` and `scale(1.05)`
across different components, plus the Home hero's static
`perspective(1000px) rotateY(-5deg) rotateX(5deg)`.

**Icons** — `lucide-react` at 12/14/15/16/18/20/24/28/32/36/48/64px, mixed freely with
literal emoji: 🚜 🌱 💧 🧪 🐛 ✅ ⚠️ ℹ️ 🔬 🤖 🔍 🌦 💰 ⏱️ 🟢 🟡 🔴 ⬜ ✅ 🔗 🏛 📄 ☀️ ☁️ 🌧️ ₹ 🔊 🏠.
Emoji also carry meaning in the step-2 scheme stats and the documents checklist, where
`⬜`/`✅` *are* the checkbox.

**Images** — the app ships **no image assets at all**. `public/` contains only
`index.html`; `favicon.ico` is referenced but absent. Every visual is CSS, an SVG icon,
an emoji, or a user-uploaded leaf photo. The only `<img>` tags are the disease preview
(`max-width: 380px`, radius 16, 2px border) and result thumbnail (`90×90`, radius 14,
`object-fit: cover`) — **neither has descriptive alt text beyond "Leaf preview" /
"Analyzed leaf"**.

**Scrollbars** — restyled globally (6px, `#f1f5f9` track, `#cbd5e1` thumb) and again
per-component with dark values. `::selection` is `#059669` on white.

### 4.7 Responsive behaviour

What actually changes at narrow widths:

| Page | ≤1100–1200px | ≤768px and below |
| --- | --- | --- |
| Dashboard | `widget-row` → 1 col; `decision-grid-3` → 2 col; `decision-grid-2` → 1 col; `status-grid` → 2 col; `recommendation-cards` → 2 col | `main-content` `margin-left: 0`, padding 16; **sidebar slides off-screen with no replacement**; all grids → 1 col; `technical-details` dl → 1 col |
| CropMonitor | `crops-grid` → 1 col | ≤720px: padding 14, header stacks, metrics → 1 col |
| WeatherWidget | `weather-main` stacks, metrics → 1 col, forecast → 1 col (vertical) | — |
| AddCropModal | — | width 95%, padding 24, suggestions stack, actions stack full-width |
| DiseaseCheckup | — | ≤640px: page padding 12, step labels 11px, tips → 1 col, upload buttons stack full width, result top stacks, thumb full width |
| GovernmentSchemes | — | ≤640px: card padding 16, card stats → 1 col, `ChevronRight` hidden, slide-over → 100% width, panel footer → 1 col |
| MandiPrices | ≤860px: all grids → 1 col, header/hero/controls stack full width | — |
| Questionnaire | — | ≤600px: farm select stacks |
| **Home** | **nothing** | **nothing** |
| **Analytics** | **nothing** | **nothing** |
| **Login / Signup** | **nothing** (card is fluid to 480px, so it survives) | — |
| **Advisor** | `auto-fit` grid reflows; header does not | — |

So: the app pages are broadly responsive; **the landing page and the analytics page are
not responsive at all.**

---

## 5. Honest design critique

Specific, with page and section pointers.

### Structural / architectural

1. **Two unrelated visual identities in one product.** `/` and `/analytics` are light
   with an emerald accent; everything else is dark with a blue accent. A farmer who
   clicks `Get Started` on the light-green landing page lands on a dark-blue login
   card that shares no colour, button style, or type treatment with the page they came
   from. The `/dashboard` → sidebar `Analytics` click is worse: a full page reload into
   a completely different-looking product.
2. **No shared layout, header, or footer.** Four pages hand-roll near-identical headers
   (`.dc-header`, `.gs-header`, `.mandi-page-header`, `.feature-header`) with duplicated
   logo markup and duplicated CSS. `DiseaseCheckup.css` and `GovernmentSchemes.css` are
   ~90% the same file with different prefixes. Any redesign should establish one app
   shell and one marketing shell.
3. **No design tokens, and the duplicate class definitions actively collide.** Zero CSS
   custom properties. `#94a3b8` is typed out 69 times, `#f8fafc` 61 times.
   `.btn`/`.btn-primary`/`.btn-secondary`, `.progress-fill` and `.priority` are each
   defined 2–4 times with different values in different files, and in the built bundle
   the last one loaded wins globally. **Measured on the live `/analytics` page:**
   - `Export Report` computes to `linear-gradient(135deg, #60a5fa, #3b82f6)`,
     `padding: 16px 32px`, `border-radius: 12px` — i.e. `Questionnaire.css`'s blue
     gradient button, **not** the flat emerald `#059669` the page's own stylesheet and
     green accent imply. The page's only primary button is off-palette.
   - `.progress-fill` in the `Crop Mix` chart computes to
     `linear-gradient(90deg, #60a5fa, #3b82f6)` — again `Questionnaire.css`'s blue
     progress bar, overriding the `linear-gradient(90deg, #059669, #10b981)` green that
     `Analytics.css` declares two lines below its own `.legend-color.yield { #059669 }`.
     **The chart's legend swatch is green and its bars are blue.**
   These are not theoretical; both are visible in `analytics-desktop.png`.
4. **No footer anywhere** — no contact, no legal, no license, no links. The README has
   a MIT license and a contact email that never reach the UI.
5. **No 404 page.** `path="*"` silently redirects to `/`, so a typo'd or stale URL
   looks like the app forgot where you were going.
6. **The landing page has no navigation.** No logo bar, no sign-in link in a header.
   A returning user on `/` has to guess that `Get Started` leads somewhere useful.

### Mobile

7. **The dashboard has no mobile navigation — this is the most serious usability bug.**
   `Dashboard.css:381` does `.sidebar { transform: translateX(-100%) }` at ≤768px, and
   nothing replaces it. No hamburger, no drawer, no bottom tab bar. On a phone,
   `/dashboard` loses access to My Crops, Weather, Farm Insights, Analytics, Disease
   Detection, Update Farm Info, Government Schemes, Mandi Prices, Settings, the user
   identity block, and **Logout**. For an app whose primary audience is farmers on
   phones, the core screen is nav-less.
8. **`Home.css` has zero media queries, and the landing page overflows its viewport.**
   Measured at a 390px viewport: `document.scrollWidth` is **624px — a 234px horizontal
   overflow**. The hero stays a hard `grid-template-columns: 1fr 1fr` with a 60px gap,
   the features grid a hard `repeat(3, 1fr)` with a 40px gap, and the H1 a fixed 48px.
   Consequences visible in `home-mobile.png`: the H1 wraps to five lines, the
   `View Demo` button is clipped mid-word, each feature card is squeezed to ~90px and
   breaks one or two words per line, and — because the light section backgrounds only
   paint to 390px while the content runs to 624px — **the right third of the features
   and benefits sections sits on the raw dark `.App` gradient**, rendering dark text on
   a dark background. `body { overflow-x: hidden }` hides the damage by clipping it, so
   a real phone user simply never sees the right half of the page.
9. **`Analytics.css` has zero media queries — it is the worst offender.** Measured at
   390px: `scrollWidth` is **696px, a 306px overflow**. `.analytics-overview` stays a
   hard `repeat(4, 1fr)`, `.analytics-charts` a hard `1fr 1fr`, with 32px page padding.
   In `analytics-mobile.png` the `.analytics-header` flex row never wraps, so the
   time-range control and `Export Report` button **overlap and sit on top of the
   "Farm Analytics" H1**; the `90 Days` / `1 Year` segments are cut off; and the three
   Key Insights cards run outside their own container. `/government-schemes` also
   overflows (+82px at 390px), though less severely.
   *(`/dashboard`, `/mandi-prices`, `/disease-checkup`, `/questionnaire` and `/advisor`
   measured clean at 390px.)*
10. **Touch targets.** Only `/disease-checkup` sets `min-height: 48px`. The
    `.remove-crop-btn` is a **24×24px** `×`, the `.summary-add-crop` is bare underlined
    text, the `.time-btn` segments are `8px 16px`, and `.password-toggle` is a 20px icon
    with 4px padding. Several of these are below the 44px minimum.
11. **The `Ask AgroBot` FAB overlaps content on small screens.** It is
    `position: fixed; right: 24px; bottom: 84px` with no safe-area inset, and the
    dashboard only reserves `padding-bottom: 96px` on `.decision-layout .main-content`.
    In `dashboard-mobile.png` it sits directly on top of the `Alerts / Warnings`
    status card, obscuring its value.

### Visual hierarchy

12. **The dashboard is a flat vertical stack of nine near-identical panels.** Every one
    is the same `rgba(30,41,59,.8)` card with an 18px heading. `Today on Your Farm`
    (the one thing a farmer needs) has exactly the same weight as `Technical details`.
    The four `StatusCards` are visually quieter than the panels below them despite being
    the summary. Nothing is dominant; nothing recedes.
13. **Information overload in `Crop recommendations`.** A single card can show a rank
    pill, three badges, two reliability lines, a verified/unverified counter, a
    "could not verify" list, three reason bullets, three warning bullets, a next action,
    and source links — all at 12–13px in near-identical grey. The honesty is the
    product's best feature but it is rendered as undifferentiated small print.
14. **`Farm Health Score` and `Soil Health Status` fight each other.** Two of the four
    top cards report the same underlying number (`soil_health_score`) in two formats
    (`7.2 / 10` and `Good`).
15. **`.page-title` uses `color: #ffffff !important` plus `text-shadow: 0 2px 4px
    rgba(0,0,0,.3)`** — a text shadow on a flat dark background is a 2012 pattern and
    the `!important` signals a specificity fight that was patched rather than fixed.
16. **The `/analytics` "charts" don't read as charts.** The soil trend is six 8px-wide
    bars in a 200px box with no y-axis, no gridlines, and values only in a `title`
    tooltip; the legend has one entry. `.legend-color.water` / `.efficiency` and
    `.chart-bar.water` / `.efficiency` are defined but never rendered — leftovers from
    a richer chart that was removed.
17. **The landing hero's "dashboard preview" is fake and doesn't match the product.**
    It shows "12 Active Fields", "24°C Optimal" and five decorative bars — none of
    which exist in the real dashboard, which is dark, sidebar-driven, and honest about
    missing data. The rotated 3D card + traffic-light dots is also a dated SaaS trope.
    Its `growBar` animation is broken (it animates an undefined `var(--height)`).

### Consistency

18. **Three logo treatments.** `Sprout` icon in the dashboard sidebar, `Leaf` icon on
    auth/disease/schemes/mandi, and no logo at all on `/` and `/analytics`.
19. **Two icon languages mixed inside single components.** The sidebar's main nav uses
    Lucide icons; the `Quick Actions` block directly beneath it uses emoji
    (`🔍 Check Disease`, `🌦 Weather`, `💧 Irrigation Advice`).
20. **Two font stacks.** `/disease-checkup` and `/government-schemes` declare
    `-apple-system, …, Roboto` and never load Inter, so they render in a different
    typeface from the rest of the app.
21. **Six content widths** (800, 920, 1120, 1200, 1400, and unbounded) and **eight
    breakpoints** (600, 640, 720, 768, 860, 900, 1100, 1200) for one product.
22. **Two i18n systems.** `/dashboard` uses the shared `i18next` bundle driven by the
    user's saved language; `/disease-checkup`, `/government-schemes` and `/mandi-prices`
    each carry a page-local `T` object with their own `EN | हिं` toggle in the header.
    So the language you pick in Settings does not apply to three pages, and the toggle
    you flip on those pages does not persist. `/`, `/login`, `/signup`,
    `/questionnaire`, `/analytics` and `/advisor` are **English-only** — including the
    entire 26-question onboarding wizard, which is the first thing a Hindi-speaking
    farmer meets.
23. **Card radius/padding drift for the same concept:** 8px (`mandi-panel`,
    `feature-card`), 10px (`recommendation-card`), 12px (`status-card`, `crop-card`,
    `overview-card`), 14px (`decision-panel`), 16px (`panel`), 20px (`gs-card`,
    `auth-card`, modal).
24. **`.priority` means two different things.** `Dashboard.css` styles
    `.priority.high/.medium/.low` (radius 4, 10px, uppercase); `DecisionWidgets.css`
    styles `.priority.good/.warning/.urgent` (radius 999px, 11px, capitalised). Both
    load on `/dashboard`.

### Readability

25. **Grey-on-dark body text is too low-contrast at small sizes.** `#94a3b8` on
    `#1e293b` is ≈ **4.1:1** — below the 4.5:1 AA threshold for normal text, and it is
    the most-used colour in the app (69 occurrences), applied at 12–14px to metric
    labels, meta rows, empty states, and `.question-help`. `#64748b` on
    `rgba(51,65,85,.6)` (input placeholders) is worse, ≈ **2.6:1**.
26. **Too much 11–13px type.** 13px appears 48×, 12px 41×, 11px 14×. On
    `/dashboard`, the alert descriptions, weather KPIs, farm summary values,
    recommendation reliability lines and task descriptions are all 12–13px grey.
27. **Line length is unconstrained on the dashboard.** `.main-content` is
    `calc(100vw - 244px)` with no max width, so on a 27" display the advice-panel
    bullets and `Today on Your Farm` notes run to 100+ characters.
28. **Raw machine strings reach the user.** `Tomato___Early_blight` is only
    partially cleaned (`replace(/_/g,' ')` → "Tomato Early blight"); the mandi trend
    pill prints the literal API token `no_data`; `data_status` is printed verbatim;
    the questionnaire shows `not_sure` as a stored value.

### Accessibility

29. **Focus states are inconsistent and partly removed.** `index.css` sets a green
    `outline: 2px solid #059669`, `Dashboard.css` sets a blue one on `.nav-item`/`.btn`
    — but every real text input does `outline: none` and replaces it with a
    `border-color` + `box-shadow` ring. Links (`<a>`) get **no** `:focus` style at all,
    and neither do `<details><summary>`, the scheme cards, or the language toggles.
30. **The scheme card is a fake button.** `<article role="button" tabIndex={0}
    onKeyDown={e => e.key === 'Enter' && openScheme(...)}>` — it responds to Enter but
    not Space, and has no `:focus-visible` style, so keyboard users get no indication
    of where they are.
31. **The modal and slide-over don't manage focus.** `AddCropModal` and `.gs-panel`
    don't trap focus, don't move focus on open, don't restore it on close, don't close
    on `Escape`, and have no `role="dialog"` / `aria-modal`.
32. **The documents checklist is not a checkbox.** `<li onClick={toggleDoc}>` with a
    `⬜`/`✅` emoji — not focusable, not announced as a checkbox, no keyboard path.
33. **`alert()` is used for a real error path** (`Questionnaire.handleComplete`), which
    is jarring and unstyled.
34. **Alt text is thin.** The only two `<img>` tags say "Leaf preview" and "Analyzed
    leaf". The entire hero "dashboard preview" is decorative divs with no
    `aria-hidden`, so screen readers walk through "12 Active Fields", "24°C Optimal"
    as if they were real data.
35. **Emoji carry meaning without labels.** 🟢/🟡/🔴 is the *only* indicator of scheme
    difficulty in the card stats row; 💰 and ⏱️ label the benefit and approval time.
    Screen readers announce these as their Unicode names, and colour-only encoding
    fails for colour-blind users.
36. **Status is encoded by border colour alone.** `.status-card.good/.warning/.urgent`
    and `.alert-item.*` change only `border-color` — a 1px tinted edge on a dark card,
    with no icon or text marker.
37. **No `prefers-reduced-motion` guard** on any of the 14 keyframe animations,
    including the infinite `pulse`, `dc-progress`, and staggered `slideInUp`.
38. **Hindi text is styled with a Latin-first stack.** No Devanagari-specific font is
    loaded, and Inter's Devanagari coverage is limited, so Hindi falls back to a system
    font at line heights tuned for Latin — noticeably tight for Devanagari matras.

### Unpolished / dead code

39. **The `/analytics` time-range control does nothing.** `7 Days | 30 Days | 90 Days |
    1 Year` sets state and appears in the effect's dependency array but is never sent
    to the API, so all four return identical data. `Export Report` has **no
    `onClick`** at all.
40. **`Ask AgroBot`'s three prompt chips are dead buttons** with no handlers — the
    headline AI feature of an "AI-powered assistant" is a non-functional stub.
41. **`Prepare Documents` in the scheme slide-over just closes the panel.**
42. **Soil Moisture and Temperature on every crop card always read `Not assessed`,**
    because `Dashboard.jsx` hardcodes `moisture: null, temperature: null`. The card
    devotes two icon tiles and half its height to two permanently empty values.
43. **`/advisor` looks unfinished** — flat background, 8px radius against the rest of
    the app's 12–20px, no loading state, no empty state, and the selected summary
    appends *below* the grid instead of opening in place.
44. **Dead CSS**: `.card` (`App.css`) is never used in JSX; `.chart-bar.water` /
    `.chart-bar.efficiency` / `.legend-color.water` / `.legend-color.efficiency`,
    `.forecast-low`, `.stat-value.loading`, `.overview-stats-horizontal`,
    `.widget-large`/`.widget-medium`, `.analytics-placeholder`, `.crop-item`/
    `.activity-item`/`.tips-list`, `.settings-content`/`.setting-group`,
    `.section-toggle-btn`, and the `code` font-family all have no corresponding markup.
    `Dashboard.css` also carries a full `.schemes-*` block for a schemes panel that
    lives on a different page.
45. **A stray `Settings` "page" with one control.** The Settings tab renders a single
    language `<select>` inside a panel titled "Settings" — no profile, no farm
    management, no notifications, no password change.
46. **Full page reloads for in-app navigation.** Six sidebar items use
    `window.location.href = '/...'` instead of `react-router` navigation, so the SPA
    white-flashes and refetches everything on each of those clicks.

---

## 6. Screenshot index

Captured with Playwright against a local production build (`npm run build`, served at
`http://localhost:4173`), full-page, `deviceScaleFactor: 2`, `reducedMotion: reduce`.
Widths: **desktop 1440px** and **mobile 390px**. There is no dark-mode variant to
capture — the app has a single fixed appearance per page (see §4.1).

Protected routes were reached by seeding a token in `localStorage` and stubbing the
backend with realistic-shaped fixtures (`scratchpad/shots/fixtures.js`); no site code
was changed. Values in the screenshots are representative sample data, not production
records.

| File (`screenshots/`) | Route | What it shows |
| --- | --- | --- |
| `home-{desktop,mobile}.png` | `/` | Landing: hero, features, benefits, CTA band |
| `login-{desktop,mobile}.png` | `/login` | Dark auth card |
| `signup-{desktop,mobile}.png` | `/signup` | Dark auth card, 5 fields |
| `dashboard-{desktop,mobile}.png` | `/dashboard` | Full decision stack + sidebar |
| `dashboard-add-crop-modal-{…}.png` | `/dashboard` | `Add New Crop` modal over the dashboard |
| `dashboard-empty-no-crops-mobile.png` | `/dashboard` | Mobile dashboard with zero saved crops (empty states) |
| `dashboard-tab-crops-desktop.png` | `/dashboard` | My Crops tab (`CropMonitor`) — **desktop only** |
| `dashboard-tab-weather-desktop.png` | `/dashboard` | Weather tab (`WeatherWidget`) — **desktop only** |
| `dashboard-tab-insights-desktop.png` | `/dashboard` | Farm Insights tab — **desktop only** |
| `dashboard-tab-settings-desktop.png` | `/dashboard` | Settings tab (one select) — **desktop only** |
| `analytics-{desktop,mobile}.png` | `/analytics` | Light report page, KPI row, both charts |
| `advisor-{desktop,mobile}.png` | `/advisor` | Advisor card grid + summary card |
| `questionnaire-step1-{…}.png` | `/questionnaire` | Set 1, Soil Physical Properties |
| `questionnaire-step2-{…}.png` | `/questionnaire` | Set 2, conditional soil-test fields |
| `disease-checkup-step1-upload-{…}.png` | `/disease-checkup` | Drop zone + tips |
| `disease-checkup-step2-analyze-{…}.png` | `/disease-checkup` | Preview + `Analyze Leaf` CTA |
| `disease-checkup-step3-result-{…}.png` | `/disease-checkup` | Result card, confidence meter, cause/treatment |
| `government-schemes-step1-profile-{…}.png` | `/government-schemes` | Farm profile form |
| `government-schemes-step2-cards-{…}.png` | `/government-schemes` | Top-3 scheme cards with match bars |
| `government-schemes-step3-detail-panel-{…}.png` | `/government-schemes` | Slide-over with docs checklist |
| `mandi-prices-{desktop,mobile}.png` | `/mandi-prices` | 4-card grid: local price, trip, trend sparkline, news |

**The four dashboard tabs have no mobile capture, and that is the finding, not a gap in
the process.** The capture run tried to click each sidebar nav item at 390px and every
click timed out, because `Dashboard.css:381` moves the sidebar to
`translateX(-100%)` with nothing replacing it. The tabs are genuinely unreachable on a
phone — see critique §5.7. For the same reason the mobile `Add Crop` modal had to be
opened via the in-content `Add crop` link in `Farm Summary` rather than the sidebar
button.

Not captured: the 404 page (does not exist), a dark/light variant (no toggle), the
3-second welcome interstitial and the "Generating…" screen (timed transients), and the
Hindi rendering of the three pages that have their own toggle.
