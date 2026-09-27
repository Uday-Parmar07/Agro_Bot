# Google Stitch — Ready-to-Paste Prompts

Prompts for redesigning **AgroBot Assistant**. Content and structure come from the real
codebase (see `WEBSITE_CONTEXT.md`); the *styling* is deliberately left open, because
the point is a redesign.

**Placeholders in `[BRACKETS]` are yours to fill in before pasting.** Everything else is
real copy from the app.

### How to use this file

1. Fill in the three placeholders in the master prompt: `[DESIRED VIBE]`,
   `[COLOR DIRECTION]`, `[TYPOGRAPHY DIRECTION]`.
2. Paste the **master prompt** first, on its own, and let Stitch establish the system.
3. Then paste **one page prompt per screen**, in the order listed. Each is
   self-contained — if Stitch loses the thread, re-paste the master prompt first.
4. Attach the screenshot listed under each prompt **as a "what exists today" reference,
   not a target**. Say so explicitly when you upload it: *"This is the current design.
   Use it for content and structure only — do not copy its styling."*
5. Use the **refinement prompts** at the end to adjust one thing at a time.

---

## 1. Master prompt

> Paste this first, on its own.

```
Design AgroBot — an AI farming assistant for smallholder farmers in India, plus the
advisors who support them. Users are on low-end Android phones, in bright sunlight, in
Hindi or English, and are not confident with software.

Vibe: [DESIRED VIBE — 3-5 words, e.g. calm, grounded, practical, trustworthy].

Colors: [COLOR DIRECTION — e.g. earthy neutrals with one confident accent]. One accent
only, used across marketing and app. Reserve green/amber/red strictly for
good/caution/urgent status; never let the accent double as a status color.

Typography: [TYPOGRAPHY DIRECTION — e.g. one humanist sans with real Devanagari
support, large sizes, generous line height]. Readable at arm's length on a phone;
nothing below 14px.

Core principle: this product is honest about what it does not know. It says "Not
assessed", "Could not verify: rainfall", "Soil values: estimated" instead of inventing
numbers. Design uncertainty as a first-class state with its own clear treatment, not as
grey small print.

One design system throughout: a single app shell with navigation that works on mobile,
one card style, one button hierarchy, one spacing scale, one set of status chips, and a
real footer.

Screens: Landing, Sign up / Log in, Farm onboarding wizard, Farm dashboard, Crop
recommendations, Disease check, Government schemes, Mandi prices, Analytics, Advisor.

Mobile-first. Every screen must work at 390px wide.
```

---

## 2. Page prompts

Each is self-contained and under 1,000 characters.

---

### 2.1 Landing page — `/`

📎 **Upload:** `home-desktop.png`, `home-mobile.png`
*(The mobile one shows the page breaking badly — useful as a "don't do this" reference.)*

```
Design the AgroBot marketing landing page. Goal: get a farmer to sign up.

Sticky top nav: logo, "Log in" link, "Get Started" button.

Hero: headline "Smart Agriculture with AI-Powered Insights". Subhead "Transform your
farming operations with real-time monitoring, predictive analytics, and intelligent
recommendations." CTAs: primary "Get Started", secondary "View Demo". Beside it, a
visual that honestly represents the real product — a farm-decision card, not a fake
browser window with invented stats.

Three-card feature row, each icon + title + line: "Real-time Crop Monitoring",
"Weather Intelligence", "Analytics & Insights".

Benefits section: headline "Why Choose AgroBot?", a six-item checklist starting
"Increase crop yield by up to 25%" and "Reduce water usage by 30%", beside three stat
tiles: 25% Yield Increase, 30% Water Savings, 24/7 Monitoring.

Closing CTA band: "Ready to Transform Your Farm?" with "Get Started Now".

Footer with product links, contact and language switcher.
```

**Mobile variant note:** Single column throughout. Hero visual moves below the headline
and CTAs; both CTAs go full-width and stack. Feature cards become a vertical stack (or
a one-card-per-view horizontal swipe), never a 3-across squeeze. Stat tiles become a
3-across row of compact tiles or a 2+1 stack. Nav collapses to logo + "Log in". The
page must not exceed 390px wide — the current one overflows to 624px.

---

### 2.2 Sign up / Log in — `/signup`, `/login`

📎 **Upload:** `login-desktop.png`, `signup-mobile.png`

```
Design the AgroBot sign-up and log-in screens as one pair sharing a layout.

Log in: heading "Welcome Back", subhead "Sign in to your agricultural dashboard".
Fields: Email Address ("Enter your email"), Password ("Enter your password") with a
show/hide toggle. Primary full-width button "Sign In" (pending state: "Signing In...").
Below: "Don't have an account? Sign up here".

Sign up: heading "Create Account", subhead "Join thousands of farmers using smart
agriculture". Fields in order: Full Name, Email Address, Phone Number (Optional),
Password with show/hide, Confirm Password. Button "Create Account" (pending:
"Creating Account..."). Below: "Already have an account? Sign in here".

Include an inline error state above the form, e.g. "Password must be at least 6
characters long".

Put an EN / हिंदी language toggle on both screens — this is the first thing a Hindi
speaker sees. These screens must feel like the same product as the landing page.
```

**Mobile variant note:** The card becomes the full screen with comfortable side
gutters, not a floating box. Inputs at least 48px tall with 16px text so iOS doesn't
zoom. Keep the primary button reachable above the keyboard, or pin it to the bottom.
Sign-up's five fields should scroll cleanly with the submit button always findable.

---

### 2.3 Farm onboarding wizard — `/questionnaire`

📎 **Upload:** `questionnaire-step1-desktop.png`, `questionnaire-step2-mobile.png`

```
Design a 5-step farm onboarding wizard. A farmer answers 26 questions about their land
so the AI can recommend crops. Highest-drop-off screen — make each step feel short.

Header: progress bar, "Step 2 of 5", step title. Titles in order: Soil Physical
Properties, Soil Fertility & Nutrients, Moisture & Irrigation, Environmental &
Regional, Organic Matter & Practices.

Question types: dropdown, large tappable radio rows, checkbox rows, text, number with
unit, date. Each question is one labelled block, e.g. "Does your soil retain water for
a long time or does it drain quickly?" with options "Retains water for long time",
"Drains quickly", "Moderate drainage".

Design these states: a "Don't Know" option that feels acceptable rather than like
failure; a conditional question appearing after a Yes; an optional marker; a helper
note; a microphone button for voice answers.

Footer: "Previous" and "Next", Next disabled until the step is complete. Final step
reads "Complete & Generate AI Plan".
```

**Mobile variant note:** One question per screen, or at most two — not a long scroll of
six. Radio and checkbox rows become full-width tap targets at least 56px tall. Progress
bar and step label stay pinned to the top; Previous/Next pin to the bottom above the
keyboard. The voice button sits inside the field, not in a separate column.

---

### 2.4 Farm dashboard — `/dashboard`

📎 **Upload:** `dashboard-desktop.png`, `dashboard-mobile.png`
*(The mobile one has no navigation at all — that is the main problem to solve.)*

```
Design the AgroBot farm dashboard. It answers one question: "what do I do on my farm
today?"

Sidebar nav: Dashboard, My Crops, Weather, Farm Insights, Analytics, Disease Detection,
Update Farm Info, Schemes, Mandi Prices, Settings, Log out.

Header: "AgroBot Dashboard", subtitle "Daily farming decisions, alerts, and crop
actions in one place", plus a farm switcher.

Content, in priority order:
1. A dominant "Today on Your Farm" panel — 3-4 rows of icon, action, reason. The hero
   of the page.
2. Four status tiles: Farm Health Score "7.2/10", Soil Health Status "Attention
   Needed", Alerts, Today's Tasks.
3. Three-up: Alerts; Weather Overview (temp, rain, wind, humidity); Farm Summary
   (location, soil, size, season, crops).
4. Crop Health Monitor cards; a Seedling-to-Harvest track.
5. Mandi Prices teaser, Crop recommendations, Upcoming Tasks, Soil and Irrigation
   advice.

An "Ask AgroBot" button that never covers content. Design the "Not assessed" empty
state for every tile.
```

**Mobile variant note:** The sidebar becomes a bottom tab bar (Dashboard, Crops,
Weather, Insights, More) or a hamburger drawer — but navigation and **Log out must
remain reachable**, which they currently are not. All grids collapse to one column.
Consider collapsing sections 4–6 into accordions, because the mobile page is currently
~5,200px of continuous scroll. The "Ask AgroBot" button must not overlap the status
tiles.

---

### 2.5 Crop recommendations panel — part of `/dashboard`

📎 **Upload:** `dashboard-desktop.png` (crop the recommendations section)

```
Design the Crop Recommendations panel — AgroBot's most information-dense component. It
must make model uncertainty readable rather than bury it.

Header: "Crop recommendations", a "Generate / refresh" button, and a coverage note:
"AgroBot's ML model compared your farm against 22 trained crop classes."

A grid of ranked crop cards. One card holds: rank "#1", name "Soybean", a suitability
level (High / Medium / Low / Insufficient data), a status (Recommended / Preliminary),
a source label "ML model + crop knowledge", "Data reliability: medium", "Soil values:
estimated", "Verified matches: 6, Unverified checks: 2", "Could not verify: rainfall",
three "Main reasons" bullets, a warning, a "Next action", and a source link.

Give the card a clear hierarchy — name and suitability first, evidence second, caveats
third. Not all equal-weight grey text.

Also design a "We need more information" empty state with a "Complete farm information"
button, and a collapsed "Technical details" disclosure.
```

**Mobile variant note:** One card per row, full width. Collapse "Main reasons",
warnings and evidence counts behind a "Why this crop?" expander so the card opens at
name + suitability + next action. Keep the refresh button in the sticky panel header.

---

### 2.6 Disease check — `/disease-checkup`

📎 **Upload:** `disease-checkup-step1-upload-mobile.png`, `disease-checkup-step3-result-desktop.png`

```
Design a 3-step plant disease checker: Upload, Analyze, Results. Mobile-first — users
photograph a leaf with their phone.

Step 1 Upload: heading "Plant Disease Detection", subhead "Upload or capture a leaf
image — AI will identify the disease and suggest treatment." A drop zone reading "Drag
& drop leaf image here", then "Upload Image", "Use Camera" and a voice-note button.
Caption "JPG, PNG only • Max 10 MB". A "Tips for best results" block: bright daylight,
a single leaf, no blurry images.

Step 2 Analyze: photo preview with "Change Image", an "Analyze Leaf" button, and a
scanning state "AI is scanning your leaf…".

Step 3 Results: photo thumbnail, a clear healthy-versus-diseased verdict, the name
"Tomato Early blight", a confidence meter at "91.2%", then "Possible Cause",
"Treatment", an expandable "View Detailed Solution", and a "Speak" button. Design the
low-confidence warning: "Image unclear — the AI isn't confident enough." Close with
"Scan Another Leaf" and an EN / हि toggle.
```

**Mobile variant note:** This flow is already the most mobile-competent in the app —
keep that. Camera button first and most prominent; tips collapse to a single expandable
line. The step indicator shrinks to three dots with only the current label shown. The
result photo goes full-width above the verdict. "Analyze Leaf" pins to the bottom.

---

### 2.7 Government schemes — `/government-schemes`

📎 **Upload:** `government-schemes-step2-cards-desktop.png`, `government-schemes-step3-detail-panel-mobile.png`

```
Design a 3-step subsidy finder for Indian farmers: Your Farm Profile, Best Schemes for
You, Scheme Details.

Step 1 Profile: heading "Government Schemes", subhead "Find the best schemes for your farm
in 3 easy steps". A State dropdown, a Crop field ("e.g. wheat, rice, cotton"), a
Farm Size control: Small / Medium / Large. Button "Find Best Schemes".

Step 2 Results: three scheme cards, the first flagged "AI Recommended". One card has a
category chip (Irrigation, Equipment, Financial, Storage), a subsidy chip "55%
subsidy", the name "Pradhan Mantri Krishi Sinchayee Yojana", a line of description, a
match meter "78% match", and three stats: benefit, difficulty, approval days. Below,
an "Official Links" block.

Step 3 Detail: name, match meter, the stats as tiles, expandable "Eligibility" and "How
to Apply", and a "Documents Checklist" (Aadhaar Card, Bank Passbook, Land Record /
Khasra) with real checkboxes. Buttons "Apply on Official Portal", "Explain Simply", and
an EN / हि toggle.
```

**Mobile variant note:** Step 3 becomes a full-screen view or a bottom sheet, not a
480px side panel. Card quick-stats stack into a labelled two-column list, and
difficulty must be a word plus an icon, never a coloured dot alone. Documents checklist
rows become 56px tap targets with real checkbox controls. "Apply on Official Portal"
pins to the bottom.

---

### 2.8 Mandi prices — `/mandi-prices`

📎 **Upload:** `mandi-prices-desktop.png`, `mandi-prices-mobile.png`

```
Design a market (mandi) price screen for a farmer with a crop to sell: what is it worth
nearby, is a farther market worth the drive, where is the price going, why.

Header: "Mandi Prices", subhead "Check local crop value, better markets, price trend,
and market news". A crop combobox ("Search any Agmarknet crop") with chips for saved
crops and "Add to my crops".

Four panels:
1. "Local Price" — market name, a large modal price "Rs. 2,380/q", a Min / Modal / Max
   row, the date, "State avg" vs "India avg", and State / District / Market selectors.
2. "Worth the Trip" — ranked markets with name, "34 km", price and a net gain of
   "Rs. 2,840" after travel. Empty: "No better nearby mandi clears the net-gain
   threshold."
3. "30 Day Trend" — a price line chart with a direction badge "up 6.4%" and a linked
   explanation: "This trend may be connected to: Onion export demand lifts Nashik
   prices."
4. "Market News" — five headlines with summary and source.

Include an EN / हि toggle.
```

**Mobile variant note:** Panels stack in the order above — local price first, since it
is the reason a farmer opened the screen. The three location selectors collapse into a
single "Change market" sheet. The trend chart gets a fixed height with a readable
x-axis and a scrubbable value readout instead of hover tooltips, which do not exist on
touch.

---

### 2.9 Analytics — `/analytics`

📎 **Upload:** `analytics-desktop.png`, `analytics-mobile.png`
*(The mobile one has an overlapping header and overflows by 306px — a clear "fix this".)*

```
Design a farm analytics screen showing stored history. It must look like the same
product as the dashboard, which today it does not.

Header: "Farm Analytics", subhead "Comprehensive insights into your agricultural
operations and performance metrics". Controls: a time range (7 Days / 30 Days / 90 Days
/ 1 Year), a farm switcher, an "Export Report" button.

Four KPI tiles: Soil Health "7.2/10" ("Latest generated recommendation"), Disease
Checks "14", Active Crops "6", Adoption "66%".

Two chart panels:
1. "Crop Mix" — one labelled horizontal bar per crop with a "3/4 active" count and a
   percentage badge. Empty: "No crops added yet."
2. "Soil Score Trend" — a real time-series chart with a labelled y-axis, gridlines and
   date labels. Empty: "No recommendation history yet."

"Key Insights & Recommendations": three cards, each icon + title + sentence, e.g.
"Weather History — 96 daily weather snapshots saved for this farm."

Design a genuine empty state for a farm with no history yet.
```

**Mobile variant note:** KPI tiles become a 2×2 grid, never 4-across. The header
controls wrap onto their own row below the title — today they overlap it. Charts get
full width one per row with a minimum height, and the time-range control becomes a
scrollable chip row or a dropdown.

---

### 2.10 Advisor view — `/advisor`

📎 **Upload:** `advisor-desktop.png`

```
Design an advisor screen for an agronomist supporting many farmers. This is the least
developed screen in the product — treat it as a fresh design.

Header: "Advisor Dashboard", subhead "Assigned farmer history and risk flags", with a
link back to the dashboard.

A list of assigned farmers. One entry shows: name "Ravi Kulkarni", email, "Farms: 2",
"Latest soil score: 6.8", "Disease checks in 30 days: 3", and a "View Summary" action.
Design the "No data" variant of the soil score — it is common.

Selecting a farmer opens a detail view in place, not appended below the list, showing
name, disease check count, weather snapshot count, and risk flags as chips, e.g.
"Tomato early blight". Include a "None" state.

Add what the screen lacks: search or filter by name, sort by risk, a visible count of
assigned farmers, a loading state, and an empty state for an advisor with no
assignments. Make risk scannable across many rows at once.
```

**Mobile variant note:** The farmer grid becomes a single-column list with name and
risk flag most prominent and the numeric stats secondary. The detail view opens as a
full screen with a back control. Search pins to the top.

---

### 2.11 Shared components pass

📎 **Upload:** `dashboard-desktop.png` and `government-schemes-step2-cards-desktop.png` together

```
Define AgroBot's shared component set so every screen uses the same parts. Show each
component with all states.

Buttons: primary, secondary, ghost, destructive, link. States: default, hover, active,
focus-visible, disabled, loading. Min 48px tall.

Cards: a base card plus good / caution / urgent variants. Status carried by an icon and
a label, not border color alone.

Chips: category, status (Recommended / Preliminary / Insufficient data), priority
(High / Medium / Low), source.

Forms: text, number with unit, select, date, radio row, checkbox row, segmented control
— each with label, helper text, error and focus states. Focus rings visible on every
interactive element, links and expanders included.

Uncertainty states: "Not assessed", "Not available", "Could not verify", "No data".
These appear constantly — give them one treatment.

Navigation: desktop sidebar, mobile bottom bar or drawer, page header, step indicator,
footer. Also: modal, bottom sheet, toast, progress bar, skeleton.
```

**Mobile variant note:** Show the mobile form of every navigation component, and
confirm every interactive element clears a 44×44px touch target.

---

## 3. Refinement prompts

Small, single-purpose follow-ups. Use one at a time, and re-run after each.

**Hierarchy and layout**
- "Make the hero headline larger and add more whitespace above the feature cards."
- "Make the 'Today on Your Farm' panel visually dominant — give it more size and
  contrast than the panels below it."
- "Reduce the dashboard to three levels of visual weight: primary actions, supporting
  data, and reference detail."
- "Cap body text line length at about 70 characters on wide screens."
- "Tighten the vertical rhythm on the dashboard — it should use one spacing scale."

**Color and contrast**
- "Use the accent color only for interactive elements. Move all status meaning to the
  green/amber/red scale."
- "Raise the contrast of secondary text — all body copy should clear 4.5:1."
- "Show the whole palette on a dark background and again on a light one, and confirm
  they read as one system."

**Typography**
- "Increase the base body size and check every label is at least 14px."
- "Show the Hindi (Devanagari) version of the dashboard with the same type scale."
- "Reduce the number of distinct type sizes to six."

**Components**
- "Redesign the crop recommendation card so crop name and suitability dominate, and the
  evidence detail sits behind an expander."
- "Replace the emoji difficulty dots on scheme cards with an icon plus a word."
- "Give status cards an icon and a text label instead of relying on border color."
- "Add a visible focus ring to every interactive element, including links and
  expanders."

**Mobile**
- "Show the dashboard at 390px with a bottom tab bar, and make sure Log out is
  reachable."
- "Collapse the lower dashboard sections into accordions on mobile."
- "Make every tappable row at least 56px tall in the onboarding wizard."
- "Show the analytics header at 390px with the controls wrapped below the title."

**Empty and error states**
- "Show the dashboard for a brand-new user with no crops, no soil test and no weather
  data."
- "Design the 'We need more information' state for crop recommendations as a helpful
  next step, not an error."
- "Show the mandi price screen when the market data feed is unavailable."

---

## 4. Screenshot upload map

| Prompt | Attach |
| --- | --- |
| Master | none — keep it text-only |
| 2.1 Landing | `home-desktop.png`, `home-mobile.png` |
| 2.2 Sign up / Log in | `login-desktop.png`, `signup-mobile.png` |
| 2.3 Onboarding wizard | `questionnaire-step1-desktop.png`, `questionnaire-step2-mobile.png` |
| 2.4 Dashboard | `dashboard-desktop.png`, `dashboard-mobile.png` |
| 2.5 Crop recommendations | `dashboard-desktop.png` (cropped to the recommendations panel) |
| 2.6 Disease check | `disease-checkup-step1-upload-mobile.png`, `disease-checkup-step3-result-desktop.png` |
| 2.7 Government schemes | `government-schemes-step2-cards-desktop.png`, `government-schemes-step3-detail-panel-mobile.png` |
| 2.8 Mandi prices | `mandi-prices-desktop.png`, `mandi-prices-mobile.png` |
| 2.9 Analytics | `analytics-desktop.png`, `analytics-mobile.png` |
| 2.10 Advisor | `advisor-desktop.png` |
| 2.11 Components | `dashboard-desktop.png`, `government-schemes-step2-cards-desktop.png` |

Also useful as supporting references, not as primary uploads:
`dashboard-add-crop-modal-desktop.png` (modal), `dashboard-tab-weather-desktop.png`
(weather detail), `dashboard-tab-crops-desktop.png` (crop cards),
`dashboard-empty-no-crops-mobile.png` (empty states),
`dashboard-tab-settings-desktop.png` (how thin Settings currently is).
