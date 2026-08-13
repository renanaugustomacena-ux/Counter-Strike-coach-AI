# CS Analytics/Coaching Platforms — Competitive UI/UX Teardown Dossier

**For:** Macena CS2 Analyzer (PySide6 desktop) redesign — deep navy (#0B1628 base / #121E2E cards), tactical orange #FF6A00, cyan data #00D9FF, JetBrains Mono metadata + Inter/Roboto UI, dense/dark-only.
**Date:** 2026-08-13. **Method:** Live fetches of marketing pages/blogs/help docs, raw CSS extraction via curl, review mining (Reddit/Trustpilot/Steam). Cannot log in; product-UI claims sourced from official blogs/docs/screenshots discussed in articles.

**Target screens for transplant mapping:** Home/Dashboard · AI Coach · Match History · Match Detail (Overview/Rounds/Economy/Highlights) · Performance · 2D Tactical Viewer (Ghost Mode) · Pro Player Comparison · Settings (retro themes) · Onboarding.

---

## 1. Leetify (leetify.com) — the category leader; benchmark for "coaching-flavored stats"

### (a) Information architecture
Two fundamental modes (their own framing): **post-match analysis** (one match) vs. **aggregated dashboard** (trend over time). App inventory (from official guide + blog + URL patterns):

- **Home** (added in the Jan 13, 2025 redesign): an *accomplishments feed* — "focuses on you and your own matches, highlighting the most impressive accomplishments you had recently," plus friends' accomplishments. Rationale stated: the Home page is "closer to the core value users are getting out of Leetify" (social bragging + self-tracking). Source: leetify.com/blog/new-navigation-home-page-and-adding-league-of-legends/
- **New navigation** (same Jan 2025 update) restructured to support multi-game (League of Legends added; per-game switcher) — nav became game-scoped.
- **Dashboard**: radar chart giving "a high level overview of your weaknesses"; below it, lists of weakest/strongest skill areas + **training recommendations based on your most urgent weaknesses**; time filter (recommended "Last 30 days") with **Current Period vs Previous Period** deltas; friends filter; General tab = winrate across teammates.
- **Matches** (list) + **Sessions** view (`/app/matches/session`) grouping matches played in one sitting.
- **Match Details** (`/app/match-details/{uuid}/...`) with sub-tabs incl. `details-opening-duels`; Rating Breakdown tab; Utility table; kill/death heatmaps; auto-flagged highlights.
- **Aim** page, **Utility** page (deep skill pages with "?" tooltips per stat, "How to improve" guidance, "View skill details").
- **Maps** page: per-map/per-side winrate diagnostics; **Map Zones tool** (performance per named map zone, filters: CT/T, pre/post-plant, usage %); **Map Flash tool** (clusters your flash lineups, effectiveness metrics, "compare against professional flash lineups").
- **Focus Areas** (`/app/focus-areas`, public marketing page `/public/focus-areas`): prioritized weakness queue driving practice recommendations.
- **Practice/Training**: guided in-game practice isolating Aim, Counter-Strafing, Positioning, Crosshair Placement, Utility (companion workshop maps); 10 new SCL training modes added to Pro (Mar 2026).
- **Progress Report / Recap**: shareable yearly/quarterly recap pages (`/progress-report/2023/q3/{steamid}`, `leetify.com/2025`) — Spotify-Wrapped-style.
- **Post-Match Journal** (Mar 2025): self-report after matches; correlates warmup/team dynamics/mood with winrate.
- **Data Library** (`/data-library`): public aggregate CS2 stats (content marketing).

### (b) Signature UI patterns
- **Leetify Rating**: symmetric scale centered at **0** = "did not change your team's odds of winning the round"; expressed as ± win-probability impact. Single-match tier bands: Great > +6.10, Good +2.50…+6.10, Average −2.49…+2.49, Subpar −2.50…−6.10, Poor < −6.10. Percentile framing for skill benchmarks: Poor = bottom 10%, Subpar 10–30%, Average 30–70%, Good 70–90%, Great = top 10%. (leetify.com/blog/what-is-leetify-rating/)
- **Rating Breakdown tab** (match detail) — 3 modules (leetify.com/blog/rating-breakdown/):
  1. *Rating by Round*: per-round **± bar chart** of win-probability contribution (values like +34.90, even +106.25 — can exceed 100% because contributions are cumulative within a round).
  2. *Rating Gained & Lost*: **stacked bars by category** (aim/utility/trades/etc.); hover a round → tooltip says which category you were rewarded/punished for; categories summed → strengths/weaknesses.
  3. *Consistency box*: this match vs **your own 60-match average**, split **T-side vs CT-side**.
- **Five sub-ratings** on every match: Aim, Utility, Positioning, Opening Duels, Trade efficiency — each benchmarked against *your current rank and the rank immediately above yours* (aspirational anchoring).
- **Utility Rating = geometric mean of Quantity × Quality** sub-ratings (Oct 2025 rework) — punishes one-dimensional utility play; both numbers shown in the match Utility table.
- **Duel-by-duel listing** in match detail (weapons, situation context per engagement).
- **Radar chart as dashboard hero** for weakness overview; weak/strong lists directly beneath convert the shape into a to-do list.
- **Focus Areas → practice loop**: weakness detection auto-links to a training recommendation (the "diagnose → prescribe" loop is the product's core coaching UX).
- **Aim/Utility benchmark seasons**: benchmarks recalculated vs population ("Aim Ratings increased ~6 points"), communicated as seasons (Aug 2025 "Season 3") — makes scores feel maintained/fair.
- **Auto-highlights** per match (provider swapped Jul 2026; Pro = multiple highlights/match).

### (c) Visual system (extracted live 2026-08-13)
Meta theme color + fonts from `https://leetify.com` HTML; tokens from `https://leetify.com/styles.css?80bd2e1260ab38c7.css` (519 KB build CSS):

```css
/* source: https://leetify.com/styles.css?80bd2e1260ab38c7.css */
--primary: #f84982;      /* Leetify pink — brand + positive accents */
--secondary: #25222c;    /* dark plum-gray surface */
--success: #3aa768;      /* green (good tier) */
--danger: #f85249;       /* red (poor tier) */
--warning: #e5a95c;      /* amber (subpar) */
--info: #37cde6;         /* cyan (info/average) */
--font-family-sans-serif: "Poppins", system-ui, ...;
--font-family-monospace: SFMono-Regular, Menlo, Monaco, Consolas, ...;
```

Surface family by frequency in the same stylesheet (dark, slightly purple-tinted grays): `#2f2b38` (cards, 49 hits), `#25222c`, `#2a2732`, `#24212b`, `#19171e`, `#17151b`, `#0d0c0f` (deepest). Body text `#ced7e0` (cool light gray-blue), `#f1f2f6`. Brand pink also used at alpha (`#f8498240`, `#f8498280`) for glows/fills; deeper pink ramp `#f61860`, `#c31853`, `#862b4c`. Fonts loaded in HTML head: **Antonio** (condensed display — big numerals), **Lato**, **Poppins** (UI); `Syne` appears for accent headings; icon font = Font Awesome 5. `<meta name="theme-color" content="#f84982">`; `<meta name="darkreader-lock">` → **dark-first, single-theme site**. Token layer is Bootstrap-derived (breakpoints 576/768/992/1200).

Takeaway vs our system: Leetify = one loud brand hue (pink) + tier semaphore (green/amber/red/cyan) on near-black plum surfaces; condensed display face for numbers. Direct analog: our #FF6A00 plays the role of their pink; our tier colors must stay distinguishable from the accent.

### (d) User sentiment
- **Trustpilot (leetify.com reviews, via search snippets — page itself 403s)**: recurring themes: rating feels **inconsistent** ("negative ratings when they feel they played well, and positive when they played poorly"); "match viewing takes a long time"; "premium gives basically nothing"; "mid site at best"; counterpoint: "good site to improve your cs2 gameplay for free."
- **Reddit (r/GlobalOffensive, r/cs2 recurring threads)**: rating-accuracy debates are constant (low-elo players with positive K/D getting negative LR); praise for automated demo review, objective weak-area detection, historical progress graphs, and free tier generosity relative to rivals.
- **Third-party review (thegamercodex.com/en/counter-strike-2/tools/leetify)**: strengths = "automates tedious demo review," "concrete, actionable feedback without human coaching costs," historical graphs prove/disprove practice value. Limitations quoted: "the free tier feels intentionally limited," "to really get value from Leetify you have to pay Pro" (reported $5.99–$10/mo depending on source/year), weaker Premier/MM demo coverage vs FACEIT, "algorithmic scores don't understand complex tactical context."
- Net: users trust the *skill sub-ratings and trends* more than the single headline number; transparency features (Rating Breakdown tab, formula-change changelogs like the Mar 2026 clutch-weighting post) exist specifically to defuse the distrust.

### (e) Transplantable directives
1. **Match Detail › Overview**: adopt Leetify's *Rating by Round* ±bar strip — per-round win-probability contribution bars (orange above zero-line, muted red below, JetBrains Mono values on hover) directly under the hero rating; it is the single best "why was my rating X" explainer and defuses rating distrust.
2. **Match Detail hero + Performance**: every headline number gets a **"vs your 60-match average" consistency chip**, split T/CT — Leetify's Consistency box proves self-comparison lands better than global comparison for trust.
3. **AI Coach**: copy the **diagnose → prescribe loop**: each detected weakness card must deep-link to a concrete drill/practice action (Leetify: Focus Areas → training recommendation). An insight without a prescribed action is a dead end.
4. **Home/Dashboard**: Leetify's 2025 pivot says the emotionally sticky home is an **accomplishments feed**, not a stat wall — lead our Home with "best moments since last session" cards before any aggregate chart.
5. **Onboarding/Settings**: benchmark scores against **"the rank immediately above yours"** — aspirational anchoring made Leetify's benchmarks motivating rather than judgmental; use it in our Performance percentile displays.

---

## 2. Scope.gg (scope.gg) — accessible analytics + utility/lineup powerhouse

### (a) Information architecture
Marketing nav (extracted live from scope.gg HTML class `menuList-module--*`): **Clips** · Tools submenu: **CS2 Lineups** (`/grenade-predictor`), **Tactical board** (`app.scope.gg/strategy`), **Comparing tool** (`/compare`), **Faceit stats**, **Prematch analytics** (`/prematch`), **Demo viewer** (`/replay`), **Aim Stats** (`/headshot-stats`), **CS2 Dashboard** (`/cs2-dashboard`), **Match history** · Guides · Blog · FAQ. Login via Steam or FACEIT. Claims "2 mln registered users", 8 UI languages. Headline: **"Stop guessing. Know your strengths and weaknesses in CS2"**; CTA: **"Get my performance review"** (onboarding = instant personalized report, not empty state). Feature blocks phrased as promises: "we'll sum up the… / we'll automatically… / we'll help you… / we'll compare you to… / we'll show how much… / we'll show how to be…" — second-person, service-voice IA.

### (b) Signature UI patterns
- **Dashboard**: "performance graph" tracking skill change **per every 15 matches** (improving vs plateauing); every metric shown *as a rating with context*, not a raw number; **"Aim rank comparison"** widget — evaluates whether your aim matches your **Premier rating / FACEIT Elo** (calibration framing: "is your aim at your elo?"). 3-step onboarding section ("How to start tracking progress?"). (scope.gg/cs2-dashboard/)
- **Grenade/Lineups tool**: interactive **2D tactical map with all grenade spots as icons**; click/hover an icon → **<20-second video demo**; per-grenade **copyable `setpos` console coordinates** for in-game practice; T/CT filters; one-way smokes tagged; 64/128-tick variants. (scope.gg/grenade-predictor/)
- **Comparing tool**: side-by-side **you vs friends vs tier-1 pros ("m0nesy, s1mple, or ZywOo" using official tournament statistics) vs rank-average benchmarks**; "20 metrics the game won't show you": TTK, first-bullet accuracy, Impact Rating, molly damage, flash duration, smoke precision, movement patterns; benchmarks **normalized over the last 30 matches** "to eliminate sample-size bias"; copy: "rock-solid proof and objective data instead of gut feelings." (scope.gg/compare)
- **Session summaries over granular analysis** (positioning per floatpeak.com comparison): digestible after-session digest; **economy win rates by buy type** charts; **skin portfolio tracker** bolted on (unique retention hook).
- **Prematch analytics** (Pro tier): scout upcoming opponents before the match.
- **Auto-recorded highlight clips** of multi-kill moments (their `/clips` product).
- 2D **demo viewer** in browser + **tactical strategy board** (draw plans on map).

### (c) Visual system (extracted live 2026-08-13 from scope.gg HTML — Gatsby CSS-modules build, tokens inline)
Hex frequency analysis of homepage CSS:

```css
/* source: https://scope.gg (inline Gatsby build CSS, 2026-08-13) */
/* surfaces (charcoal, slightly blue) */      #090a0b; #14171b; #1f2329; #252a31; #2b3038; #313840;
/* primary accent (violet) */                 #7661ff; #816dff; #6357b5;
/* secondary accent (acid lime, CTAs/data) */ #c5ff7b; #c5ef80;
/* aqua data tint */                          #8ee0e8; #91e2ea;
/* deep indigo feature panels */              #0d0f29; #121533; #1c2144;
/* text ramp */                               #e0e3eb; #a1aab2; #93a8bf; #828791; #737980;
```

Read: **violet primary + acid-lime energy color on near-black charcoal** — the lime is reserved for CTAs and "you improved" moments, giving a strong two-accent hierarchy (brand vs. action). Deep indigo panels (#121533 family) visually segment "pro/tactical" feature zones — close cousin of our navy #0B1628; validates navy panels + hot accent. Typography not extractable from inline CSS (custom-props absent); UI appears geometric-sans per screenshots referenced in guides.

### (d) User sentiment
- **Trustpilot (trustpilot.com/review/scope.gg, via search snippets)**: **4/5, ~39 reviews**. Praise: stat tracking quality, helpful guides, friendly community, fast support responses. Complaints: site freezing/slow loading (company claims fixed); a battle-pass event where "users reported rank decreases without communication"; "some features are free but extremely limited" — subscription needed for full toolset.
- **floatpeak.com/guides/refrag-vs-leetify-vs-scopegg/**: pros — "lowest barrier to entry," "economy analysis clearly surfaced," "identifies macro-level problems effectively," minimal onboarding, digestible session summaries. Cons — "shallow depth relative to Leetify," "rank context not always obvious," "less suitable for advanced players." Positioned for <8,000 Premier players.
- Net: Scope wins on approachability and utility training; loses on analytical depth and trust among advanced users.

### (e) Transplantable directives
1. **2D Tactical Viewer**: adopt Scope's lineup-icon interaction — grenade markers on the 2D map that expand on click into a lineup card with **copyable `setpos` console command** (we're a desktop app: add "Copy to console" button writing to clipboard). Ghost Mode already shows pro movement; this adds pro *utility* as first-class map objects.
2. **Pro Player Comparison**: label every comparison with its normalization window — "last 30 matches" chip in JetBrains Mono next to the radar — Scope explicitly markets normalization as the fairness guarantee; it's a one-line trust win.
3. **Home/Dashboard**: add an **"Aim vs Rank calibration" widget** ("your aim is at 14K Premier level; your rank is 11K") — Scope's aim-rank comparison is the most conversation-starting stat they have; fits our cyan-data + orange-delta language.
4. **Match Detail › Economy tab**: chart **win rate by buy type** (full/force/eco/pistol) as the hero economy visual — Scope proves economy digestibility beats round-by-round money tables for most users.
5. **Onboarding**: replace empty-state onboarding with Scope's **"Get my performance review"** pattern — first-run wizard ends by generating an immediate personalized report from imported demos, not a blank dashboard.

---

## 3. CSStats.gg + Tracker.gg CS2 — the raw-density references
*(Both sit behind Cloudflare — direct fetch/curl returned 403/challenge pages; findings from official pages via search snippets, their own article URLs, and third-party teardowns: theglobalgaming.com/cs/best-stats-tracker, skin.club "Best CS2 Stats Trackers 2026", play-ascend.com "Best CS2 Tracker in 2026".)*

### (a) Information architecture
**CSStats.gg** (fully free): search any player (trick: "add 'x' to the start of any steamcommunity.com URL"); Steam sign-in; sharecode ingestion (`/getting-the-sharecode`). Player page: rank + **rank-history graph**, improvement graphs over time, per-map stats (most played, highest winrate), weapon stats, utility/clutch/duel stats, **heatmaps**, **"Played With" tab with VAC/Overwatch ban tracking** ("special filter to show only players you've played with who have been banned"). Match pages: **full round details — how the round was won, clutch flags, complete kill feeds**. **Multi-player lookup** (`/player/multi`) compares several players at once. Tracks Competitive + Premier.
**Tracker.gg CS2** (part of multi-game Tracker Network; Premium $3.99/mo removes ads): profile overview (lifetime-stat focus), match list ("all previous matches at a glance," click to expand), **weapon accuracy per gun**, lifetime **map performance**, **Premier leaderboards**, articles/news hub, desktop app + mobile app, "live insights to predict how opponents will play."

### (b) Signature UI patterns
- **CSStats: pro metrics for pub players** — surfaces **HLTV-style Rating, KAST, entry frags** on regular MM/Premier matches; "visually appealing" match history rows with simple accessible columns (HS%, ADR) that expand into full **per-round kill feeds**.
- **CSStats: ban justice feed** — banned-teammate tracking is its most-cited feature in community threads (used as a data source in cheating-rate discussions). Emotional retention hook: "that guy who destroyed you got banned."
- **CSStats: rank-change timeline** — Premier rank deltas plotted over time; the improvement graph is the page hero.
- **Tracker.gg: Tracker Score** — "a personal performance rating out of **1,000 possible points** that allows you to understand your performance **in your own skill group**" (tracker.gg/cs2/articles/tracker-score-our-new-performance-rating). Normalized 0–1000 within skill cohort = instantly legible, defuses "my rating is unfair vs pros" complaints.
- **Tracker.gg: lifetime framing** — aggregate identity stats ("you, all-time") vs Leetify's recency framing; weapon-accuracy-per-gun table is its unique density artifact.
- Both: **leaderboard as acquisition surface** (Premier ladder pages rank #1 in search).

### (c) Visual system
Not directly extractable (Cloudflare). From public screenshots/articles: csstats.gg = dark gray-blue tables, rank icons as primary color moments, dense Bootstrap-like rows; described as "main emphasis is more on raw numbers than on visualization" (skin.club). Tracker.gg = Tracker Network house style: near-black #0d0d0d-family surfaces, coral-red brand accent, big stat tiles with sparkline underlays, prominent premium/ad slots. Treat both as *density ceiling* references, not palette references.

### (d) User sentiment
- CSStats praised as "fully free… no subscription plans" (skin.club) and "accurate for the data the Steam Web API exposes (rank, lifetime stats) but can't see per-round detail" vs demo-parsers (play-ascend). "Amount of available stats significantly reduced compared to Leetify and Scope."
- Tracker.gg seen as "broad but less specialized… covers a dozen other games" — CS2 users treat it as a quick-look profile, not an improvement tool. Premium is ads-removal, rarely praised.
- Community threads use csstats ban data as evidence in cheating debates — trust in its *data recording* is high even where its *analysis* is considered shallow.

### (e) Transplantable directives
1. **Match Detail › Rounds tab**: adopt csstats' **full kill-feed per round** — expandable round rows showing the literal killfeed (killer → weapon icon → victim, headshot marker), plus "how the round ended" badge (elimination/defuse/explode/time) and clutch flag. This is the density users expect from a "real" CS tool; JetBrains Mono suits it perfectly.
2. **Match History**: one-line rows at csstats density — map, score, K/D/A, ADR, HS%, HLTV-style rating, rank-change chip — expandable in place; plus a **session grouping header** (date + session aggregate) like Leetify Sessions/Tracker matches-at-a-glance.
3. **Performance**: hero = **rating-over-time graph with rank milestones annotated** (csstats' rank graph); secondary = **per-weapon accuracy table** (tracker.gg's artifact) in a dense mono grid.
4. **AI Coach / Match Detail hero**: consider Tracker Score's framing for our confidence ring — a **0–1000 score normalized within the player's own skill cohort**, labeled as such ("734 — vs 12K–15K Premier cohort"); cohort-relative normalization is the single best defense against "your rating is wrong" distrust.

---

## 4. Refrag (refrag.gg) — the "diagnose → drill" training platform

### (a) Information architecture
Marketing nav: How it Works · Features · Pricing · Blog (+10 languages). Product organized as **three pillars: Analyze → Practice → Play** ("clarity of a coach, precision of a trainer"; tagline **"Play Smarter"**). Product surface inventory (homepage + wiki + blog): **Refrag Coach** (post-match weakness analysis from Premier/FACEIT data), training modes — Crossfire, Prefire, NADR (nade practice), Recoil Trainer, Spray Transfer, Bootcamp, Blitz, Clutch, Defender, Duels, Routines — plus **Academy** (lessons), **Utility Hub** (lineups), **Restrat**, **Scrim mode**, **Creator Studio**, **2D Demo Viewer**, **Detailed Aim Stats**, Community Hub, wiki.refrag.gg docs. Pricing: Player $5.40/mo (annual), Competitor $11.50/mo, Team $60/mo (7 players, own servers); on-demand servers in **35 global locations** (listed city-by-city on the homepage — infrastructure as a feature). Claims 550,000+ users; testimonials from pros (SorPlex, floppy, Asreal, Garry, Golden); dedicated pro landing pages ("Train smart like EliGE", refrag.gg/elige/).

### (b) Signature UI patterns
- **Coach weakness panel** (refrag.gg/blog/what-is-refrag-coach/): every stat shows **"your current average alongside a target average — a benchmark derived from players performing at the level you're working toward"**; stats meeting benchmark **highlighted green**, shortfalls **"flagged in orange or red."** Pure traffic-light + target-pair pattern.
- **Four stat categories with exact metric vocabulary** (worth stealing wholesale):
  - *General*: kills/round, deaths, ADR, HS kill %, HLTV rating
  - *Aim*: HS%, **counter-strafe %**, **crosshair placement in degrees of deviation**, recoil control accuracy, spotted accuracy, **time-to-kill, time-to-damage**
  - *Utility*: enemies flashed, friends flashed, avg flash time, utility damage, **unused utility value**
  - *Entry & Trades*: opening kill success/fail, trade kill success/fail, trade death success/fail
- **Adaptive routine**: recommendations regenerate as match data shifts — "the recommendations and routine update to reflect where your game actually stands"; weakness → specific training mode mapping (the drill exists in-product, so prescriptions are actionable one-click).
- **Sessions view for training itself**: history across modes, tracking HS%, reaction time, crosshair placement **over time** — practice gets the same analytics treatment as matches.
- **Improvement proof marketing**: "71% of users see measurable FACEIT Elo improvement within 30 days" (floatpeak.com comparison); homepage screenshots of "aim charts, utility maps, and rating progression graphics."

### (c) Visual system (extracted live 2026-08-13 from refrag.gg HTML)
```css
/* source: https://refrag.gg (inline build CSS/markup hexes, 2026-08-13) */
#0f141a  /* page base — near-black blue */
#222c39, #323f51, #334257  /* slate blue-gray cards/borders */
#6a7dff, #8b90ff  /* periwinkle-violet primary accent */
#ff774d  /* hot orange secondary accent (CTAs/flags) */
#6affdb  /* mint — positive/improvement color */
```
Read: cool slate-navy field with **violet primary + orange alert + mint success** — a three-role accent system (brand / warning / progress). Notably close to our navy+orange+cyan triad; Refrag proves orange-as-flag works on navy. Typography: geometric sans (marketing), stat UI uses condensed numerals per screenshots. Wiki runs on Wiki.js default theming.

### (d) User sentiment
- Community consensus (Steam discussions, training-tool threads): "excellent training tool"; server quality praised — pro quote from homepage: "Refrag has great servers far above what I can get out of what's typically available."
- floatpeak.com comparison cons: "only useful after problem identification — less useful without prior analytics diagnosis" (i.e., Coach was built to close exactly this gap); onboarding "moderate; requires problem diagnosis before effective use."
- Positioned for serious grinders (18,000+ Premier / FACEIT L8+) and teams; casual users find the mode list overwhelming.
- No substantial Trustpilot signal found (their audience lives in Discord/Steam, not review sites).

### (e) Transplantable directives
1. **Performance screen**: adopt Refrag's **current-vs-target stat pair** as the core row anatomy — `crosshair placement 7.2° → target 5.0°` in JetBrains Mono, green when met, orange (#FF6A00) when short — with targets derived from the *next* rank cohort. This is the cleanest coaching data pattern in the entire competitive set.
2. **AI Coach**: every weakness insight ends in a **one-click prescribed drill** (workshop map launch / practice config download) — Refrag's diagnose→drill loop only works because the prescription is executable, not advisory prose.
3. **Performance/Settings**: adopt Refrag's **metric vocabulary** (counter-strafe %, crosshair placement in degrees, TTD, unused utility value) — these specific named metrics read as "pro-grade telemetry" and fit our file:line technical-annotation aesthetic.
4. **Match History**: add a parallel **"Practice Sessions" lane** — Refrag treats training sessions as first-class analytics objects with their own trend lines; our app can log workshop/DM sessions alongside matches.

---

## 5. FACEIT + Esportal — competitive platforms; progression & status-badge masters
*(faceit.com and support.faceit.com 403 direct fetches; sourced from support-article snippets, skin.club/egamersworld guides, app-store listings. Esportal fetched directly.)*

### (a) Information architecture
**FACEIT**: multi-game competitive platform ("FACEIT 2.0" = redesigned interface + performance). Core surfaces: Play (matchmaking queues, hubs, ladders, tournaments), Clubs, Party Finder ("for players who prefer teaming up rather than solo queue"), Watch, Shop (FACEIT Points; they literally sell a physical **Level 10 pin** — faceit.com/en/shop), Missions/progression, profile with stats. Mobile app rebranded **"FACEIT: CS2 Command Centre"** — "track stats, accept matches, join clubs, build teams," with a **Matchmaking Widget** (queue status) and **Elo Widget** (persistent glanceable rank) (Google Play/App Store listings). Support hub has a "Navigating FACEIT" onboarding article — the IA is complex enough to need a manual.
**Esportal**: web platform (Swedish/Nordic roots): CS2 Ladders, Matchmaking, Casual Servers, **Gathers** (its signature — player-created lobbies where captains pick teams), tournaments, streamer integration.

### (b) Signature UI patterns
- **10 skill levels over exact Elo** — the canonical dual display: "Skill Levels provide a visual tier, while Elo shows the exact position within or beyond that tier" (skin.club guide). Ranges: L1 100–500 · L2 501–750 · L3 751–900 · L4 901–1050 (start 1000) · L5 1051–1200 · L6 1201–1350 · L7 1351–1530 · L8 1531–1750 · L9 1751–2000 · L10 2001+ · **Challenger = top 1,000 per region** (seasonal leaderboard status above L10). Balanced match ≈ **±25 Elo**.
- **Progress-to-next-level**: for L1–9 the profile shows "current rank, exact Elo, and remaining points needed for advancement"; at L10 the frame switches to "Elo, country rankings, and regional position" — **the UI reframes progression once the ladder ends** (from climb → leaderboard identity).
- **Octagonal level badges** with a color ramp culminating in the iconic red-orange Level 10 octagon — so recognizable it exists as stickers, pins, icon packs (icons8, Redbubble merch). Status token worn in every match room, forum signature, and stream overlay.
- **Match room**: lobby with two team columns, captain-based map veto, ready check, server selection, level badges beside every name, post-match Elo delta per player. (Composite from platform guides; direct UI not fetchable.)
- **Widgetization** of the core loop (queue widget, elo widget) — rank is treated as ambient, always-visible state, not a stats-page destination.
- **Esportal Gathers**: lobby-first social matchmaking (captains picking teams recreates "pickup game" culture); ladder + gather history on profile.
- **NEW — FACEIT Season 8 "Match Insights" (launched Apr 22, 2026, Premium)**: **round-by-round 2D radar reconstruction directly on the match page** — kill/death coordinates, utility deployment, round performance graphs in-browser, "removing the requirement to download a demo file." Launched together with **FACEIT Rating** — "calculates how much your in-game actions changed the win probability of a match, separate from your final scoreboard placement" (support.faceit.com Season 8 FAQs; faceit.com/en/news/faceit-season-8-launch). Strategic read: **the platform layer is absorbing the analytics layer** — win-probability impact ratings and 2D round replays are now table stakes, not differentiators; third-party tools must go deeper (coaching, prescriptions, pro comparison) to stay relevant.

### (c) Visual system
- **FACEIT**: house style = near-black charcoal surfaces with **signature FACEIT orange (≈#FF5500)** accents, white type, octagon iconography; the orange-on-dark identity is so strong that "FACEIT orange" is shorthand in the community. (Not extractable live — 403; from brand assets/app screenshots.) Direct relevance: our #FF6A00-on-navy reads adjacent to FACEIT's authority aesthetic — a plus for a coaching tool targeting FACEIT grinders.
- **Esportal** (extracted live 2026-08-13):
```css
/* source: https://esportal.com (SPA shell + /assets/index-BRLUtV0I.css) */
#0f1013  /* page base — near-black */
#e8232e  /* Esportal red — primary brand */
#ff5a63  /* light red (hover/secondary) */
#9aa0a6  /* gray text */
font-family: 'Manrope', system-ui, -apple-system, sans-serif;
```
Red-on-black with a single humanist sans (Manrope) — minimal, aggressive, Nordic.

### (d) User sentiment
- **FACEIT**: default "serious CS" home; the level system is beloved status currency (merch proves it). Standing complaints across Reddit/Steam threads: elo grind anxiety, toxicity in solo queue, smurfing, and subscription upselling — but the *ranking UI itself* is rarely criticized; it is the trusted reference other tools benchmark against (Leetify/Scope/Refrag all display FACEIT Elo).
- **Esportal (Trustpilot, ~4 pages of reviews)**: harsh — anticheat called "a big joke" / "non existent"; "Swedish admins… create gathers where they pick players in a way that helps them win, and toxic players often don't get banned"; support "resolves tickets without giving an answer." Counterweight: "I've been playing on Esportal for five years and I love the matchmaking and gather system." Lesson: community features live or die on perceived fairness and admin transparency.

### (e) Transplantable directives
1. **Home + Match History**: adopt FACEIT's dual display everywhere a rating appears — **tier badge (visual) + exact number (position) + "N points to next tier"**. Our AI Coach confidence ring should carry the same triplet: ring (tier), center number (exact), sub-label (delta to next tier).
2. **Settings › retro themes / identity**: design an **octagonal tier-badge set** for our internal skill tiers (works beautifully with CS1.6/CSGO retro themes); badges must be exportable/shareable — FACEIT proves the badge *is* the retention product.
3. **Match History rows**: per-match **±Elo-style delta chip** (±25-scale) colored green/red in JetBrains Mono — the single most habit-forming number on FACEIT match lists.
4. **Home/Dashboard**: a persistent **header "elo widget" strip** (current rating + trend sparkline + next-tier progress) visible on every screen, mirroring FACEIT's widgetization of rank as ambient state.

---

## 6. Rising 2025–2026 tools

### JumpThrow.gg — free Leetify challenger; *the closest visual cousin to our design language*
- **Positioning**: "Analyze CS2 demos and FACEIT matches with round-by-round stats, economy, utility, duels, heatmaps and 2D replays for faster, clearer match review." **Currently free; core features need no account.**
- **IA**: FACEIT Match Tracker · Rankings (Global/EU/Americas/Asia) · Player Finder · Skins DB · Tools (crosshair editor, **binds generator**) · demo upload. Supports FACEIT + Premier.
- **Match report = 5 sections**: (1) Personal Review — habits & mistake patterns; (2) Movement Visualization — 2D map fight tracking; (3) Clip Extraction — auto "impact clips" + highlight reels; (4) Comparative Metrics — side-by-side vs teammates/opponents ("resolving scoreboard debate through deeper impact scoring"); (5) Progress Dashboard — aim consistency, utility effectiveness, map-specific form trends.
- **2D Replay**: interactive scrubbable map replay — movement, grenades, fights, bomb events. Economy charts track "buy decisions and financial swings across rounds."
- **Visual system (extracted live 2026-08-13)**:
```css
/* source: https://jumpthrow.gg (inline hexes) */
#1f1f22, #303033  /* near-black warm-gray surfaces */
#ff6600, #d65600  /* ORANGE primary + pressed state */
#ffc800  /* amber highlight */  #fe1f00 /* red */  #1559c4 /* blue */
```
  **Orange-on-dark identical in spirit to our #FF6A00** — validates the palette, and warns: we must differentiate through denser typography (JetBrains Mono annotations) and the navy (not warm-gray) field.
- Directive: **Match Detail**: copy JumpThrow's 5-section report spine (Personal Review → Movement → Clips → Comparison → Progress) as our tab logic sanity-check — our Overview/Rounds/Economy/Highlights maps cleanly, but we lack their "Personal Review" mistake-pattern section → fold it into AI Coach.

### Beatable (beatable.co) — AI demo analysis upstart
"Web application similar to Leetify… AI-driven analysis" differentiating on **lower-latency processing, cheaper subscriptions, and coach/team workflows** (eneba.com 2026 roundup). Public shareable analysis URLs (`beatable.co/analysis/{id}`). Signal: *speed of report generation* is now a marketed feature — our desktop app should surface parse progress + "report ready in Xs" telemetry (fits file:line technical aesthetic).

### CSNADES.gg — lineup specialist
"The best place to learn Counter-Strike 2 grenade lineups… smokes, molotovs, flashbangs, and HE grenades" (meta description). Visual system extracted live: amber **#feac00** accent on **#171717/#212121** black, text #e4e4e4 — single-accent utility-focused minimalism. Community standard for lineup browsing (map → side → nade-type filter grid → video + position screenshots). Directive: our 2D Viewer's lineup overlay should match csnades' filter grammar (map/side/type) since users arrive pre-trained on it.

### Allstar.gg — auto-clips infrastructure
"Get your own in-game highlights, magically out of thin air… Free, fast, easy clip capture with **zero FPS drop**" (CS2/LoL/Fortnite/Dota). Community shorthand: "Instagram for CS2 clips that are taken automatically." Cloud-rendered clips from demos/telemetry — no local recording; montages, overlays, mobile app. Widely understood in the community to have powered Leetify's highlights, though unconfirmed — Leetify's Jul 2026 "Highlights Provider Change" post does not name providers; either way that post marks the highlights ecosystem shifting. Palette: dark blue-gray #1c2a34 + teal #1278a1. Directive: our Highlights tab should generate **shareable clip cards** (thumbnail + kill sequence metadata) even if rendering is deferred — the *zero-effort* framing is what users buy.

### Blitz.gg CS2 — multi-game AI coach entrant
Blitz (League tooling giant) now "handles League, Valorant, CS2, Fortnite, and five more" as an AI coaching platform — big-budget UX convergence toward per-match AI advice cards. Watch for their CS2 overlay patterns.

### Sentiment snapshot for newcomers
Thin formal review coverage (young products). JumpThrow praised in tool roundups for being free/fast; Allstar has an established Trustpilot page (reviews not mined in this pass); Beatable too new for signal. No substantial review signal found for csnades beyond broad community endorsement (NadeKing-style creator recommendations of lineup sites).

---

## Top 15 transplantable patterns (ranked by impact)

Ranking weighs: trust-building power, retention/habit formation, fit to our dense/dark/technical design language, and feasibility in a PySide6 desktop app.

1. **Per-round ± win-probability impact bars** *(Leetify "Rating by Round"; now converged on by FACEIT Rating, Apr 2026)* → **Match Detail › Overview**. Directly under the hero rating, render a per-round bar strip: orange #FF6A00 above the zero-line, desaturated red below, hover = category tooltip ("+34.9 — entry kill converted"). This is the industry's proven answer to "why is my rating X" — shipping it makes our AI rating auditable instead of oracular.
2. **Diagnose → prescribe loop: every weakness ends in an executable drill** *(Leetify Focus Areas + Refrag Coach routines)* → **AI Coach**. Each insight card carries a one-click action: launch workshop map, copy practice config, queue a drill checklist. Refrag proves prescriptions must be executable, not advisory prose; Leetify proves the weakness-queue framing ("Focus Areas") beats raw stat dumps.
3. **Current-vs-target stat pairs with traffic-light state** *(Refrag Coach)* → **Performance**. Row anatomy: `counter-strafe 61% → target 75%` in JetBrains Mono; green when met, #FF6A00 flag when short; targets derived from the next rank cohort ("benchmark derived from players performing at the level you're working toward"). Adopt Refrag's metric vocabulary wholesale (crosshair placement in degrees, TTD, unused utility value) — it reads as pro telemetry.
4. **Tier badge + exact number + "N to next tier" triplet, widgetized** *(FACEIT levels/Elo + Elo Widget)* → **AI Coach confidence ring + persistent Home header strip**. Ring = tier color, center = exact value, sub-label = delta to next tier; same triplet repeated as an ambient header widget on every screen. FACEIT proves rank-as-ambient-state is the most habit-forming pattern in CS.
5. **Full kill-feed round timeline with round-end badges** *(csstats.gg)* → **Match Detail › Rounds**. Expandable round rows: literal killfeed (killer → weapon glyph → victim, HS marker), round-end badge (elim/defuse/explode/time), clutch flag, money spent. This density is the credibility bar for "a real CS tool"; mono type + file:line annotations make it ours.
6. **Consistency chip: this match vs your own 60-match average, split T/CT** *(Leetify Consistency box)* → **Match Detail hero stats**. Every headline stat gets a small ± badge vs personal average (e.g. `ADR 87 ▲ +12 vs 30d`). Self-referential comparison defuses the #1 sentiment problem found across every platform: rating distrust.
7. **Cohort-normalized 0–1000 score labeling** *(Tracker.gg Tracker Score)* → **AI Coach**. Whatever our belief-state model outputs, present it normalized within the player's skill cohort and *say so on the label* ("734 — vs 12–15K Premier cohort"). Cohort-relative framing is the cheapest trust win in the entire teardown.
8. **Accomplishments feed as the emotional Home hero** *(Leetify's Jan 2025 Home redesign)* → **Home/Dashboard**. Lead with "best moments since last session" cards (career-high ADR, clutch, ace) before any aggregate chart — Leetify explicitly rebuilt Home around this because it is "closer to the core value users are getting."
9. **Session grouping + per-match rating-delta chips** *(Leetify Sessions, FACEIT ±25 Elo, csstats rank timeline)* → **Match History**. Group rows under session headers with session aggregate; each row: map, score, K/D/A, ADR, HS%, rating, colored ± delta chip. One-line density at csstats level, expandable in place.
10. **Economy tab hero = win rate by buy type + money-swing chart** *(Scope.gg economy focus + JumpThrow economy charts)* → **Match Detail › Economy**. Top: full/force/eco/pistol win-rate bars (cyan #00D9FF data, orange highlights); below: per-round team money area chart with buy annotations. Scope proves buy-type digestibility beats raw money tables.
11. **Grenade lineup markers as first-class 2D map objects with copyable console commands** *(Scope.gg grenade predictor; csnades filter grammar map/side/type)* → **2D Tactical Viewer**. Nade icons on the map expand to lineup cards with `setpos` copy button and ≤20s clip; filter bar uses the community-standard grammar (map → side → nade type). Pairs naturally with Ghost Mode's pro overlays.
12. **Named pro presets + normalization-window chip on comparisons** *(Scope.gg compare: "m0nesy, s1mple, or ZywOo", "last 30 matches" normalization)* → **Pro Player Comparison**. Radar + head-to-head table gets a JetBrains Mono chip: `window: last 30 · source: tournament data` — labeling the fairness rules is what makes pro comparison credible rather than demoralizing.
13. **"Aim vs rank" calibration widget** *(Scope.gg aim-rank comparison)* → **Home/Dashboard or Performance**. One card: "Your aim: 14K-level · Your rank: 11K" — the single most conversation-starting, screenshot-shareable stat pattern found; perfect for our orange-delta treatment.
14. **Zero-effort highlight clip cards** *(Allstar.gg "magically out of thin air", JumpThrow impact clips, Leetify auto-highlights)* → **Match Detail › Highlights**. Auto-flag 2-3 moments per match as cards (thumbnail, kill sequence metadata, round ref) with export/share; the value is zero-effort curation, rendering can be deferred.
15. **Instant-report onboarding** *(Scope.gg "Get my performance review"; Beatable's speed positioning)* → **Onboarding wizard**. Final wizard step ingests recent demos and lands the user on a *generated first report with one highlighted weakness*, never an empty dashboard; show parse progress in technical log style (`parsing demo 3/5 … de_mirage 2.1MB/s`) to make the wait part of the aesthetic.

### Palette landscape (all extracted live, for positioning)
| Platform | Base | Accent(s) | Note |
|---|---|---|---|
| Leetify | #17151b–#2f2b38 plum-black | pink #f84982; tiers green/amber/red/cyan | Antonio condensed numerals |
| Scope.gg | #14171b charcoal + indigo #121533 panels | violet #7661ff + acid lime #c5ff7b | two-role accent (brand vs action) |
| Refrag | #0f141a slate-navy | periwinkle #6a7dff + orange #ff774d + mint #6affdb | three-role accent triad |
| JumpThrow | #1f1f22 warm black | **orange #ff6600** | nearest neighbor to us — differentiate via navy + mono density |
| csnades | #171717 black | amber #feac00 | utility minimalism |
| Esportal | #0f1013 black | red #e8232e | Manrope |
| FACEIT | charcoal | signature orange ≈#FF5500 | octagon badges |
| Ours | **navy #0B1628/#121E2E** | **orange #FF6A00 + cyan #00D9FF** | navy field + mono annotations = open positioning; no incumbent owns "tactical navy" |
