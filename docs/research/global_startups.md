# Global Gaming Analytics & Coaching Products — Design Research Dossier

Purpose: inspire redesign of a PySide6 desktop CS2 AI coaching app.
App design language: deep navy #0B1628, tactical orange #FF6A00, cyan data accent #00D9FF, JetBrains Mono annotations, dense dark UI.
App screens: dashboard, AI coach chat + insights, match history/detail, performance analytics, 2D replay viewer with pro ghost overlay, pro comparison radar, themed settings, onboarding wizard.
Unique AI architecture to exploit: self-correcting coach, belief-state confidence, ghost-mode divergence analysis, per-pro-player/tournament advice.

Research date: 2026-08-13. Method: WebSearch + WebFetch + raw CSS/bundle grep for palette hexes. Hexes marked "unverified" where scraping failed.

---

## TIER 1 — DEEP DIVES

### 1. Mobalytics (US — Marina del Rey; acquired by ESL FACEIT Group, Mar 2025)
- **What/traction:** Multi-game "personal performance analytics" companion (LoL, TFT, VALORANT, Deadlock, Marvel Rivals, more). ~$13.8M raised over 5 rounds (incl. $11.25M Series A 2020, Almaz/HP Tech Ventures/GGV); acquired by ESL FACEIT Group March 2025 — meaning FACEIT (CS2's biggest third-party ladder) now owns the best-known "skill radar" IP. Millions of users, 182 countries. Community sentiment: positive on depth, historical griping about paywalling.
- **UI/UX patterns:**
  - **GPI (Gamer Performance Index)** — the canonical skill radar: 8 skills (Fighting, Farming, Vision, Aggression, Toughness/Survivability, Teamplay, Consistency, Versatility), each 0-100, each skill built from 4-7 named sub-metrics. Radar is described as a playstyle "fingerprint"; overlays two polygons — pink = former self, yellow = current self — so improvement is visible as area growth. Score semantics are rank-anchored: "0 = Bronze-like at this skill, 100 = best Challenger players." Icons instead of text labels on the radar; hover reveals name, click opens the skill's sub-metric breakdown (3-level drill hierarchy: radar -> skill -> sub-metrics).
  - Advice framing: "focus on 1-2 weakest GPI areas" — the radar exists to drive a prioritized to-do, not just display.
  - Pre/post-match loop: pre-game lobby scouting + build import, post-game GPI delta. Daily quest-like "what to improve today" cards.
- **Visual identity:** App is dense dark UI with violet/indigo surfaces and yellow/gold highlight for "you" (marketing site is WordPress; distinctive hexes found: #382f66, #2c274f dark violets, gold #f2bf43 — app palette hex unverified beyond these). Iconography does heavy lifting (each GPI skill has a glyph).
- **Transplant directives:**
  1. Pro comparison radar: adopt the two-polygon overlay pattern but make it three: you-now (orange fill), you-30-days-ago (dim outline), target pro (cyan outline). Rank-anchor every axis (0 = Silver-like, 100 = pro-like) so numbers carry meaning.
  2. Make every radar axis clickable -> drill into 4-6 named sub-metrics with benchmark bars (GPI's 3-level hierarchy). No dead-end visualizations.
  3. Dashboard: one "today's focus" card generated from the weakest radar axis, phrased as a drill, not a stat.

### 2. Leetify (Sweden — Stockholm)
- **What/traction:** The de-facto community-standard CS2 analytics platform (also LoL since 2024). Auto-ingests matchmaking demos; free tier + Pro. Reddit/Steam sentiment: strongly positive ("clean and very useful," used by pros); Trustpilot only 2.4/5 "Poor" on a small review count (billing/cancellation complaints dominate — classic freemium friction, not product-quality signal). Founded 2019 by Vitalii Zurian and Anders Ekman; ~$2.5M seed at $30M post-money (~$3.5M total per Tracxn; Antler, Inventure, Alpine); analytics built on 2M+ ranked users' data; 200k+ MAU at seed era "almost entirely word of mouth"; no acquisitions.
- **UI/UX patterns:**
  - **Dual headline ratings, never conflated**: Leetify Rating = win-probability impact (zero-centered, economy-adjusted, recalibrated on CS2 pro matches; role-aware — Anchors, Rotators, Spacetakers, AWPers, Lurkers; CT/T split; +2.09 good, +5.12 great) vs **Aim Rating** = pure mechanics (50 = population average, 80+ elite). Impact and mechanics are separate numbers with separate scales — users always know *which kind of good* they were. Six drillable skill categories (Aim, Utility, Positioning, Clutch, Opening Duels, Trading); Utility split into quantity vs quality.
  - **Benchmark-relative 0-100 category ratings** (Aim, Utility, Positioning): every sub-stat compared to your-rank benchmarks; above benchmark pushes toward 100, below pushes toward 0. Everything is "vs people at your level," never raw.
  - **Dashboard radar of weaknesses** + explicit "Focus Areas" page: lists weak/strong areas and maps each weakness to a training recommendation. Compare page (app/compare/<you>/<friend>) does head-to-head stat tables with green/red deltas.
  - **Session/recap ritualization**: yearly wrapped-style "2025 Recap" page; personal-best celebrations; club/friends leaderboards. Improvement is made social and shareable.
- **Visual identity (verified from styles.css):** dark plum-charcoal surface stack #19171e / #25222c / #2a2732 / #2f2b38 / #212529; brand magenta-pink #f84982 (+hot #f61860) for CTAs; signal colors: green #3aa768 = above benchmark, red #f85249 = below, amber #e5a95c = neutral/warn, cyan #37cde6 = info; text #ced7e0. Typography: Poppins for UI, SFMono/monospace stack for stat numerals. The green/red benchmark coloring is applied to nearly every number on the site — the palette IS the coaching.
- **Transplant directives:**
  1. Adopt benchmark-relative coloring everywhere in analytics: every stat gets green/amber/red vs same-rank baseline; raw numbers always paired with "vs your rank" delta. (Map green->our cyan #00D9FF for "above," orange #FF6A00 reserved for action items, red for below.)
  2. Match detail: lead with one composite "impact rating" with role/side context line under it ("as CT anchor on Inferno: +4.1, great"), then category cards.
  3. Steal the "Focus Areas -> drill" mapping: each weakness card carries a concrete practice action our AI coach can queue.

### 3. Tracker Network / tracker.gg (US — Kansas City, MO)
- **What/traction:** Largest independent stat-tracking network (VALORANT, CS2, Apex, Fortnite, Destiny, Marvel Rivals...); browser + Overwolf desktop app with in-game live overlay; tens of millions of monthly users across properties. Sentiment: default choice, "original and most widely used" for VALORANT; Premium gets deeper history/MMR graphs; ad-heaviness on free tier is the recurring complaint.
- **UI/UX patterns:**
  - **Profile hero banner**: rank emblem + peak rating + K/D + win% as huge stat tiles above the fold, then dense card grid (accuracy, loadout, maps, agents). Numbers-first hierarchy — the page reads like a broadcast lower-third.
  - **Per-game skinning on one chassis**: same layout system re-themed per title (VALORANT pages use Riot's #ff4655/#0f1923; brand itself is red). One information architecture, many liveries — exactly how a multi-map/multi-mode CS app should theme.
  - **Live match overlay**: teammate ranks/stats round-by-round without leaving game; post-match auto-popup with your performance vs lobby.
  - Percentile framing ("top X%") on most stats; global/regional leaderboards one click from any stat.
- **Visual identity (verified):** near-black blue-charcoal base #0f1923, panel #1b2733, border #2c3f52, muted blue-gray text #99abbf; TRN red #e4485d / #e2263c accents; per-game accent tokens (#3ecbff cyan, #5ee790 green, gold #cbb765) used as data colors. Typography: **Saira** (semi-condensed, sporty) for display/headers + Roboto for body — the condensed display face is a big part of the "esports broadcast" feel.
- **Transplant directives:**
  1. Dashboard hero: adopt the broadcast-banner pattern — player card with rank emblem, 3-4 oversized stat tiles (Leetify-style colored), sparklines under each. JetBrains Mono numerals will give us the same technical-broadcast energy Saira gives TRN.
  2. Percentile chips ("top 12% of MG2s") on every analytics stat; make them the hover-default tooltip.
  3. Match history rows styled as broadcast scorebugs: map thumbnail, score, your impact rating chip, W/L edge-stripe (win = cyan stripe, loss = red) — scannable in a 40px row.

### 4. Blitz.gg (US — Los Angeles; Swift/TSM-owned since Jan 2019)
- **What/traction:** Companion app for LoL/TFT/VALORANT/CS2/Deadlock/Marvel Rivals; auto-imports builds, in-game overlays (jungle timers, combat score), post-match analysis. Acquired by TSM parent Swift for multi-millions (Jan 2019). Trustpilot 2.5/5 (~90 reviews): ads intrusiveness, paywall creep, memory leaks — cautionary sentiment despite polish; still praised as "fast, polished, beginner-friendly, most feature-complete."
- **UI/UX patterns:**
  - **Zero-effort automation as UX**: detects game/lobby, imports runes/builds automatically, overlay appears without configuration. The product's core promise is "you never fill a form."
  - **VALORANT Combat Overlay**: minimal in-round chip showing live Combat Score/HS%/K — deliberately non-intrusive, "no competitive advantage" framing.
  - Post-match: instant breakdown with benchmarked stats and "what to do next game" tips; win-probability timeline for LoL.
  - Onboarding: one login -> auto-detect installed games -> per-game overlay toggles with previews.
- **Visual identity:** near-black charcoal app chrome with saturated red CTA (#ff003d family seen on homepage) and per-game accent theming (VALORANT #ff4654, gold #d5a038); large numerals, compact rows; hex for app internals unverified (Electron app). Motion: quick slide/fade of overlay chips, no decorative animation.
- **Transplant directives:**
  1. Onboarding wizard: Blitz's auto-detect flow — detect CS2 install + Steam account, preview each overlay/feature as a toggle card with a live thumbnail, one-click done.
  2. Our replay viewer HUD: a Blitz-style minimal live chip (round win-prob, your impact delta) that can also run as an in-game overlay later.
  3. Anti-pattern to avoid: monetization chrome (ads/upsell modals) inside coaching surfaces — it is the #1 driver of Blitz's 2.5 Trustpilot despite superior features. Keep coaching screens commerce-free.

### 5. OP.GG (South Korea — Seoul, est. 2013)
- **What/traction:** Korea's dominant game-data platform (LoL + VALORANT/TFT/PUBG...), "chosen by 55M+ users worldwide," top-tier global gaming-web traffic; mobile apps ~4.5 stars at scale; desktop app w/ overlay. The mass-market benchmark for stat UX.
- **UI/UX patterns:**
  - **OP Score**: 0-10 per-player match score computed on a timeline (every 5 min; every 3 in ARAM); final value becomes the match score. **MVP badge** (best on winning team) / **ACE badge** (best on losing team) — losing well is explicitly celebrated, which keeps the metric motivating.
  - **Timeline graph of OP Score** per match with side-by-side champion comparison, plus **14 auto-generated keywords** ("Tenacity," "Unstoppable," "Indomitable Will") derived from the *shape* of the graph — turning curves into words. This is the closest thing in mass-market UX to our belief-state narration.
  - Match history rows: instantly scannable color semantics — blue row = win, red row = loss — plus per-row KDA, items, OP Score badge. Dense but never cluttered; the row is the atom of the whole product.
  - Desktop "2025 Awards" wrapped feature; champion/agent one-pagers with tier badges (OP/1/2/3 tiers).
- **Visual identity (verified from app CSS):** dark theme #1c1c1f base, panels #282830/#31313c/#202d37, text gray #9aa4af, borders #424254; **win-blue #5383e8** (their most famous color decision; loss-red family present as #ff6c81/#e84057-adjacent tokens), gold #eb9c00 for MVP/legend accents. Light theme is default on web; desktop app dark (users complain there is *no light mode* there — theming toggle matters). KR-standard clean sans (Pretendard-class; hex/typography of KR font unverified).
- **Transplant directives:**
  1. Match history: commit to a hard two-color row semantic (win/loss tint on the row edge + background wash at 5-8% alpha). Add MVP/ACE-style badges from our impact rating — including an "ACE" for best-on-losing-team to reward good play in losses.
  2. Match detail: plot our round-by-round belief-state/impact as a timeline graph and auto-generate keyword chips from its shape ("comeback," "fast starter," "eco-round specialist") — OP.GG proves curve->word compression works for lay users.
  3. Ship a year-end/season "Awards" recap screen — retention ritual, near-zero engineering cost with our existing stats.

### 6. DEEPLOL.GG (South Korea)
- **What/traction:** #2-tier Korean LoL stat site differentiating on AI: **AI-Score** per match (contribution estimate beyond KDA), **AI tier prediction** ("where you'll land"), matchup/synergy analytics, pro-player pages (LCK section is a first-class citizen). Core audience Korea; solid regional traffic (semrush-tracked), no US-style funding story found.
- **UI/UX patterns:**
  - AI-Score presented exactly where OP Score sits — same slot, "smarter number" positioning. Rating + rank prediction gives users a *forecast*, not just a report: "at this trajectory you'll be Plat II."
  - Pro-player integration into a ladder tool: browsing LCK pros' live solo-queue games next to your own history normalizes "watch how a pro does it from inside your own stats app."
  - Champion pages carry matchup-specific ability tips (micro-coaching embedded in data tables).
- **Visual identity:** dark navy-on-charcoal with blue/teal accents, KR information density (tight tables, many numbers per row); hex unverified.
- **Transplant directives:**
  1. Add a forecast element to our analytics: "projected rank in 30 days if aim trend holds" with confidence band — DEEPLOL shows prediction is a loved feature, and our belief-state machinery makes it honest (show the band, not just the point).
  2. Fold pro content into player screens: on any map/weapon stat, a one-line "how <pro you follow> does it" row with jump-to-ghost-replay — DEEPLOL's pro-pages-inside-stats pattern, upgraded by our per-pro advice engine.

### 7. Aimlabs / Aim Lab (US — Statespace, NYC; founded by NYU neuroscientists)
- **What/traction:** #1 aim trainer, 45M+ players, official VALORANT VCT partner, pro-designed tasks (ScreaM, yay). $15M+ raised (2020). Steam sentiment long-term very positive; recent grumbling about ranking rework. (Its coaching-marketplace sibling ProGuides was shut down May 2024 — see Tier 2.)
- **UI/UX patterns:**
  - **Skill radar over trainable axes**: profile rank + radar across Flicking, Tracking, Speed, Perception, Cognition (+switching) — every axis maps 1:1 to a drill category, so the radar is a training menu, not a report card.
  - **Rank = floor of weakest axis**: your displayed rank (9 tiers x4 divisions, Bronze->Grandmaster) is dragged down by your least-developed skill — mechanically forcing balanced training. Brutal but motivating; community debates it, which proves they read it.
  - Per-task post-screens: score, percentile, per-quadrant screen heatmap of accuracy (their neuroscience DNA: visual-field analysis), then "queue next drill."
  - "Import your VALORANT crosshair" — tiny-friction personalization that makes practice feel continuous with the real game.
- **Visual identity (verified):** theme-color **#47D8D7 cyan** on near-black #1f1f1f; teal secondary #00a99d; clinical-lab aesthetic (thin rules, scientific charts) softened by esports gradients. Motion: score count-ups, radar draw-in.
- **Transplant directives:**
  1. Our pro-comparison radar axes must each be trainable (Entry, Trade, Utility, Crosshair placement, Positioning, Clutch) with a "practice this" button per axis — Aimlabs proves radars convert when axes = drills.
  2. Adopt a "weakest-link rank" secondary metric ("your ceiling is set by Utility: 41") to focus attention; our coach can explain it in chat.
  3. Replay viewer: per-quadrant/zone accuracy heatmap overlays (their visual-field analysis transplanted to map zones — e.g., accuracy when holding A-site vs retaking).

### 8. Noesis (Denmark — Bang & Jensen ApS, Copenhagen)
- **What/traction:** Interactive CS2 demo-analysis web app: 2D viewer, multi-round aggregation, heatmaps, utility inspection; €9.99/mo, 14-day trial; used by broadcast analysts, team coaches, high-level players. Niche but respected ("what normally takes hours is visible in seconds"); noted learning curve.
- **UI/UX patterns:**
  - **Rounds-as-dataset**: filter engine ("all T-side gun rounds on Mirage vs pistols") -> merge many rounds into one tactical top-down view. The unit of analysis is the *pattern across rounds*, not the single round — no mainstream competitor does this.
  - Instant time-scrubbing in the 2D viewer; side-by-side comparison of rounds from *different matches*; kill/death position layers; grenade trajectory inspection.
  - Praised as "simplistic and not overtuned" — a restrained pro tool: white-on-dark map linework, few colors, data density from overlay layers rather than chrome.
- **Visual identity:** modern dark theme, tactical-minimal (hex unverified); the radar map IS the interface — everything else is filter chips and timelines.
- **Transplant directives:**
  1. Our 2D replay viewer needs a round-filter bar (map/side/buy-type/outcome) plus "stack rounds" mode drawing 20 rounds' paths at 15% alpha under the current round — this is the Noesis killer feature and pairs perfectly with ghost divergence ("your 20 B-holds vs pro's 20").
  2. Treat scrubbing latency as a design KPI: instant seek anywhere on the round timeline; frame-accurate jumps from kill-feed events.
  3. Keep viewer chrome monochrome; reserve hue strictly for data layers (our orange = you, cyan = pro ghost, white = teammates, red = enemies).

### 9. Chess.com Game Review + Insights (US — global; the coaching-UX gold standard)
- **What/traction:** 250M+ registered users (Feb 2026); Game Review is the most-used "AI coach explains your game" flow in any game; Insights is the Diamond-tier analytics dashboard.
- **UI/UX patterns:**
  - **Move classification badges**: every move stamped with an icon+color: Brilliant (!! teal), Great (! blue), Best/Excellent/Good (greens), Book (opening-theory tan), Inaccuracy (?! yellow), Mistake (? orange), Miss (red-orange), Blunder (?? red). One glyph system turns a wall of moves into an emotional narrative. (Colors are the product's most recognizable asset; "Brilliant" is a community meme = aspirational metric done right.)
  - **Coach at top of screen** guiding through Key Moments; per-move: engine classification + alternative line + **Retry** ("try to find the better move yourself") — the review is a *playable exercise*, not a lecture.
  - Accuracy % + estimated game Elo per game; evaluation graph (advantage swings) as the match's emotional arc; phase breakdown (opening/middlegame/endgame accuracy).
  - **Insights dashboard**: accuracy by phase, by time-of-day/day-of-week, most-played openings W/L, tactics found-vs-missed (forks, pins, mates, hanging pieces) — every stat doubles as a lesson pointer.
  - Brilliant-move criteria were *re-tuned to match human intuition* after feedback (must sacrifice material, near-best) — they treat metric feel as a design surface.
- **Visual identity:** warm dark UI (charcoal + wood-tones), friendly rounded sans, the badge color system above; coach avatar with speech bubble; confetti on wins. Hexes unverified (site is app-shell), but badge hues are universally recognized: teal/blue/green/tan/yellow/orange/red ramp.
- **Transplant directives:**
  1. Build a **round classification glyph system** for match detail + replay timeline: e.g., Brilliant round (teal), Great decision (blue), Standard (green), Book (executed known strat, tan), Inaccuracy (yellow), Mistake (orange), Throw/Blunder (red) — stamped on the round scrubber and in the AI-coach chat. Tune thresholds so "Brilliant" stays rare and coveted.
  2. Add **Retry moments**: at a flagged decision, pause the 2D replay, hide the outcome, ask "where do you rotate?" — click the map, then reveal pro ghost + coach explanation. This converts review into practice (chess.com's single best trick).
  3. Analytics screen: copy Insights' "every stat is a door" rule — accuracy by phase (pistol/eco/gun rounds = our opening/middlegame/endgame), by map area, by time-of-day; each row deep-links to filtered replays + a coach note.

### 10. Garmin Catalyst + Trophi.ai (US/Garmin hardware; Trophi: Saint John, Canada + Driver61/UK — a16z-backed, ~$3.3M)
- **What/traction:** The two benchmark "ghost coaching" products outside esports. Catalyst (2020, Catalyst 2 in 2024): in-car driving coach; reviewers call it the best lap-timer UX ever made. Trophi.ai: AI sim-racing coach (iRacing etc.), widely reviewed as "found 2 seconds a lap"; tiers Premium -> Professional (human 1:1 added).
- **UI/UX patterns (Catalyst):**
  - **True Optimal Lap**: composites your *actually driven* best sectors into an achievable target — never a fantasy lap. All deltas are vs. this achievable self, so advice is always credible.
  - **Opportunities screen**: post-session, exactly **three** most-improvable sectors, each with a video clip of *your own best* execution of that sector. Advice = "you've already done it; do it again."
  - Real-time audio coach with 3 verbosity modes ("Race Coach / Advanced / Lap Times Only"); cues are terse imperatives ("brake later," "apex later") + praise ("good job"); two-option home screen (Drive / Review).
  - Racing line auto-drawn from 10Hz GNSS; sector/lap jump navigation with no scrubbing needed.
- **UI/UX patterns (Trophi):**
  - Live telemetry overlay comparing your inputs vs reference driver *as you drive* (their braking point, throttle %, gear) — the ghost is data, not just a car model.
  - Post-session report: prioritized fix list with time-loss quantified per corner ("Turn 3: -0.4s, brake 15m later"); multi-lap consistency analysis; voice coach calls out recurring mistakes live.
- **Visual identity:** Catalyst: automotive black/white/red, huge numerals, glanceable at 150mph. Trophi: dark UI, telemetry-green/cyan traces on black (hex unverified). Both: zero decorative elements; every pixel is a decision aid.
- **Transplant directives (highest-value section for our ghost mode):**
  1. **Compose an "Optimal You" ghost** from the player's own best executions (best B-hold, best A-execute) alongside the pro ghost. Two selectable references: "your best self" (credible) and "pro" (aspirational) — Catalyst proves the self-ghost drives adoption because it never feels impossible.
  2. Divergence report = Opportunities pattern: after each match, exactly **3 moments**, each quantified ("this rotation cost 2.1s / 18% win-prob"), each with a clip of you doing it right previously (or the pro ghost), ranked by expected impact. Resist listing 15 issues.
  3. Coach verbosity modes in settings: Full explain / Terse callouts / Stats only — Catalyst ships three levels; our chat + replay annotations should honor the same user dial.
  4. Quantify every divergence in time and win-probability ("peeked 0.8s early, -12% round WP") — Trophi's per-corner time-loss is the credibility engine.

### 11. STRATZ (US — Dota 2; design-benchmark tier-1.5)
- **What/traction:** Dota 2 analytics famous for the prettiest dashboard in esports stats; positioning (2026 site): "highly personalized data visualizations, AI-powered match predictions, robust API, rapid release cycle." GraphQL API is an ecosystem staple; a STRATZ MCP server for AI agents exists (2026). STRATZ+ subscription. (The often-cited "Gameplay IQ" name is not verifiable on the 2026 site — the shipped system is IMP.)
- **UI/UX patterns:** **adaptive dashboard** — dynamic cards appear/disappear based on your playstyle and recent outcomes (personalization at layout level, not just numbers); **IMP score** (Individual Match Performance): neural-net impact score on a 0-255 scale (100 = average), computed continuously through the match, from ~27 contextual factors (hero/lane/role/bracket/duration), plus team-level TMP; **Match Performance Simulation**: adjust any of 22 stat inputs to see how the change would have shifted win probability — an interactive counterfactual; item-build tables with dual time sliders; consistent card grammar across player/hero/meta pages.
- **Visual identity (verified from homepage):** deep blue-teal darks #0c1f23 / #0f292f, cyan-teal accents #1b9fb8 / #127486, pale text #cfd8db; Noto Sans; restrained gradients, glassy cards. Proof that a teal-on-dark identity (adjacent to our cyan) can feel premium rather than "hacker terminal."
- **Transplant directives:**
  1. Dashboard = card system with a strict grammar (title, hero number, sparkline, one action link) and user-arrangeable interest cards — STRATZ's "what you need when you need it" framing.
  2. Grade lanes -> grade our map areas: per-site/per-role letter grades (A+ holding B apps, C- on retakes) as entry points into filtered analytics.
  3. Steal Match Performance Simulation for the AI coach: an interactive counterfactual card in chat ("if your opening-duel win rate were 55%, projected round win rate +6%") — sliders backed by our win-prob model.

### 12. Metafy (US — Pittsburgh; human-coaching marketplace, light dive)
- **What/traction:** Coaching marketplace (SSBU, Pokemon, LoL, VALORANT...); $33.5M raised (Forerunner, 776, Tiger); $3M seed extension Mar 2025; absorbed refugees when ProGuides died. Model pivoting toward "guides + async coaching + communities."
- **UI/UX patterns** (site blocked fetching; patterns from product knowledge, hexes verified via curl): coach cards fronted by human faces, verified-pro badges, response-time and student-count proof; async VOD-review purchase flow (send replay -> timestamped annotations back); pay-per-session, no subscription wall. Coaching presented as a *relationship*, not a report.
- **Visual identity (verified from homepage):** near-black #0e0e11 base with pastel accent set — cream #ffe7b7, ice #d4f2fe, pink #f9ced5, purple #b75bff; playful editorial typography and illustration; deliberately warm/human vs the genre's mil-spec coldness.
- **Transplant directives:**
  1. Give our AI coach a *persona surface* borrowed from human-coach UX: avatar, name, "specializes in," session history ("worked with you on utility since March") — Metafy shows trust comes from continuity cues.
  2. Deliver AI analysis as *timestamped annotations on the replay* (async-VOD-review pattern), not only as chat text: a rail of coach comments pinned to round timestamps.

---

## TIER 2 — REGIONAL COVERAGE (QUICK HITS)

### Americas / platform quick hits
- **Overwolf (Israel/US, platform):** 113M MAU network, 178k creators, $300M creator payouts in 2025 (Forbes); CurseForge mods + app store for overlays (hosts tracker.gg app, OP.GG desktop and Blitz-class companions). Design takeaway: the winning distribution surface for game companions is the *in-game overlay*; a desktop coaching app should treat "second-screen vs overlay" as a first-class layout mode. Also proof users tolerate companion apps only when CPU/RAM cost is invisible — performance is a UX feature.
- **ProGuides (US) — DEAD:** shut down May 29, 2024 (after Statespace merged it with Aimlabs+; users migrated to Coachify/Metafy). Lesson: human-coaching subscriptions bundled to content paywalls churn hard; billing complaints wrecked its Trustpilot. Design lesson for us: coaching value must be self-evident inside the product, not gated behind a "book a human" wall.
- **omeda.city -> pred.gg (community, Predecessor):** volunteer-built stats for a niche MOBA; hero builds, leaderboards, claim-your-profile + Discord-bot integration as community-native onboarding. Takeaway: even tiny scenes expect OP.GG-grade stat UX now.
- **Dotabuff (US, Dota 2):** the OG dark stats site (signature red on charcoal); Plus tier is a ready-made widget catalog: Damage/CC Breakdown, Interactive Vision Map, Death Map and Log, Item Build Timeline, Gold/XP Charts, Kill and Death Economy, Comparative Farm Charts (your curve vs another player's, two lines one chart). Enduring pattern: every stat row links to a filtered match list — nothing is a dead end. Transplants: death/utility heatmap layers toggleable on our radar; "kill and death economy" reframed as money-traded-per-engagement; comparative curves for user-vs-pro econ/damage. (See STRATZ in Tier 1 for the design-forward Dota benchmark.)
- **Lichess (France, open-source):** free engine analysis for all; "Learn From Your Mistakes" mode replays only your errors and makes you find the right move before continuing; puzzles auto-generated from *your own* games. Spartan UI, zero ads, beloved for it. Transplant: generate practice scenarios directly from the player's own failed rounds ("your mistakes" queue in the AI-coach screen), and note that a commerce-free coaching surface is itself a differentiator users evangelize.

### Asia sweep

#### FOW.KR -> fow.lol (Korea)
- **What/traction:** Oldest Korean LoL stat site (~2013, pre-OP.GG); now redirects to fow.lol, alive 2026. KR community sentiment: OP.GG is better organized, but FOW is faster and its MMR estimate is considered more accurate; won early loyalty by offering match replays before the client did.
- **UI/UX patterns:** speed-first instant search; dense tier tables with patch-delta arrows (up/down vs last patch); lobby multi-search (paste all players, get all cards); live spectator lookup.
- **Visual identity:** minimalist, light, tier-colored icons only; hex unverified.
- **Transplant directives:** (1) lobby multi-search — paste a CS2 scoreboard/share-code, render all 10 player cards. (2) patch-delta arrows on every weapon/map stat. (3) instant-result search before signup; link accounts after value is shown.

#### DAK.GG (Korea — PlayXP Inc., Seoul)
- **What/traction:** Multi-game stats portal (LoL, TFT via LOLCHESS.GG, VALORANT, PUBG, Eternal Return...); official PUBG featured app; official Eternal Return companion where missions grant in-game rewards (publisher-blessed loop); Overwolf + mobile apps. Alive and current 2026.
- **UI/UX patterns:** per-game tiles feeding one consistent chassis; platform-switcher modal; rating-history graph + match timeline profiles; mode matrix tables; ER "high-win-rate route recommendations" — prescriptive routing, not just stats; Favorites/tracked-players rail everywhere.
- **Visual identity (verified from CSS):** 7-step charcoal elevation ladder #161618 / #1b1b1e / #212227 / #27282e / #2d2f37 / #333339 / #363944; brand yellow #fbdb51; orange accent #ff6a3c (nearly our tactical orange); muted blue-gray text #9fa5b9.
- **Transplant directives:** (1) ghost overlay of statistically-best T-side default routes for map/rank (their route-recommendation pattern). (2) dashboard Favorites rail of tracked teammates/pros with delta badges. (3) adopt a 6-7 step navy elevation ladder instead of one flat panel color — density stays readable because of it.

#### YOUR.GG (Korea — Gigitix; acquired by Gen.G Esports, Apr 2024)
- **What/traction:** LoL playstyle-analysis startup; LCK data partnerships; Gen.G uses its AI engine for academy scouting. Vendor survey: 86% endorse PLAYREPORT, 50% claim tier-up in a month (treat as marketing). Alive 2026.
- **UI/UX patterns:** pentagon playstyle radar with tier-average as ghost shape (bulges/dents = instant strengths/weaknesses); "which pro plays like you" similarity matching; PLAYREPORT: five-chapter time-sequential match narrative; tier-trajectory prediction; coaching delivered as per-phase missions with completion tracking, not prose; zero-setup onboarding (type name -> tailored report).
- **Visual identity (verified):** brand blue #318eef dominant; win/loss green #008a00 / red #e60000; near-black neutrals #0b0b0b / #242526; SUIT + Pretendard Korean geometric sans; calm, report-like.
- **Transplant directives:** (1) pro radar: user polygon filled orange, pro/rank-average as cyan outline ghost — dents are training targets. (2) coach outputs missions per game phase (pistol/gun/closing rounds) with completion state. (3) dashboard rank-trajectory widget ("on current form: DMG in ~3 weeks").

#### WanPlus / 玩加电竞 (China — Beijing)
- **What/traction:** Esports data + community platform (LoL, Dota2, HoK, CS, VCT/LPL/KPL coverage) with B2B data layer and industry events; apps on iOS/Android. Alive 2026.
- **UI/UX patterns:** schedule-first IA — home is live/upcoming pro fixtures in a logo grid; match-report pages (verdict headline -> key numbers -> full data); hot-topics sidebar; everything organized by competition.
- **Visual identity:** dark, team-logo-forward; hex unverified.
- **Transplant directives:** (1) dashboard pro-fixture rail deep-linking to study material ("watch how NAVI plays your best map"). (2) match detail as match-report template: verdict headline first. (3) pro-scene aggregates (veto/win trends) beside personal stats.

#### MAX+ / 刀塔MAX (China — Qingfeng Beijing)
- **What/traction:** Default Chinese Dota2+CS app; v5.0.351 (May 2026), 2.6M downloads on Tencent MyApp (3.9 stars), iOS 4.0 (898 ratings). Top complaint: Chinese-only.
- **UI/UX patterns:** bottom tabs bundling data / pro events / community / news — stats and forum one tap apart (the retention engine); skin-inventory query as a daily non-performance hook; community posts embed match data.
- **Visual identity:** dark chrome, green/teal MAX branding; hex unverified.
- **Transplant directives:** (1) interleave a light feed (patch notes, pro results) between dashboard stat modules. (2) ship language switching day one. (3) inventory-value card beside performance data as an emotional hook.

#### Tencent first-party: WeGame / 王者营地 / 掌上英雄联盟 (China)
- **What/traction:** Largest-scale analytics family anywhere (Honor of Kings 100M+ DAU); all alive 2026. 王者营地 (HoK companion) is the pattern-rich one.
- **UI/UX patterns:** 团队分析 team analysis = per-match economy curve + key-event timeline; 对局先知 "match oracle" reveals all players' records at game start; mid-match lineup-based advice; **营地AI — chat assistant grounded in your own match database** (smart retrieval, deep match-record Q&A). LoL CN app: match records as first-class bottom tab.
- **Visual identity:** gold-on-dark-royal-blue (HoK); WeGame orange-red on light; hex unverified.
- **Transplant directives:** (1) strongest Asian reference for our AI coach chat: ground chat in the user's own rounds with retrieval ("why did I lose Mirage yesterday?" -> cites round 7), not a generic tips bot. (2) pre-round intel card of enemy tendencies (match-oracle pattern). (3) economy curve + key-event timeline as the replay scrubber — click an event, the 2D view jumps there.

#### Japan scene (community-run)
- **What/traction:** No dominant commercial JP tracker — Tracker.gg owns JP VALORANT (cottage industry of Japanese usage guides). stat.ink (Splatoon log aggregator, personal project, alive 2026); UniteAPI (Pokemon Unite); シャドラボ (Shadowverse); GameWith embeds a stat tool inside guide content.
- **UI/UX patterns:** stat.ink: battle-log-centric chronology, aggregate breakdowns by weapon/map/rule, public shareable profile pages, open CSV/JSON export + community API (data-ownership ethos).
- **Transplant directives:** (1) raw CSV/JSON export of all rounds in settings — a trust feature power users evangelize. (2) public read-only share-profile URLs for coaches/teammates. (3) attach a micro-guide to the first stat a new user sees ("what is a good ADR at your rank?").

### Europe sweep

#### Market-structure news (verified Aug 2026)
- **Bayes Esports (DE) — DEAD:** filed insolvency May 2025 (Berlin court declared illiquid Aug 2025) after Riot, EWCF and ESL FACEIT Group defected to GRID; **GRID acquired Bayes' IP assets Sept 2025** (BODEX, live-data widget lineage). Its pro-team sister **Shadow.gg is also dead** (DNS unresolvable).
- **gosu.ai — DEAD:** deadpooled per Tracxn 2026; ~$5.1M raised, only site remnants remain.
- **pley.gg (DK) — PIVOTED:** now an esports news/affiliate media site (Pley Media Group), not an analytics product.
- **Esportal (SE) — REBRANDED:** PGL acquired assets Aug 2024; esportal.com now redirects to **Fragnet Arena** (arena.fragnet.net). Trustpilot 243 reviews mixed-negative (cheaters/support vs praise for servers and anti-toxicity).

#### GRID Esports (Germany) — the consolidated B2B data leader
- **What/traction:** Official data platform of Riot, Ubisoft, KRAFTON + BLAST/ESL FACEIT Group; Open Access program gives free official CS2/Dota2 GraphQL data to 250+ community projects. B2B, no consumer reviews.
- **UI/UX patterns:** developer-first portal (GraphQL + docs + project gallery as social proof); official-server-data trust positioning; game-segmented landing pages.
- **Visual identity:** dark marketing site, near-black + white, partner-logo grids; hex unverified.
- **Transplant directives:** (1) provenance badges on stats ("server demo" vs "GC parse") — trust labeling is rare in consumer CS2 tools. (2) power-user query builder (entity x metric x timeframe) beside canned charts. (3) onboarding gallery-of-outcomes: show 3 real example insights before asking for Steam login.

#### Esports Charts (Ukraine)
- **What/traction:** escharts.com — the reference for viewership analytics (~90k tournaments, 371k matches); free + PRO tiers; constantly press-cited in 2026. B2B/media.
- **UI/UX patterns:** dense live wall (live counters, ranking tables); event "Viewership Hub" aggregating one event into a single destination; **final figures published after a stated 02:00 UTC validation pass — a visible "validated data" timestamp as trust pattern**; headline numbers free, deep slices paywalled.
- **Visual identity:** professional blues/grays, card modules; hex unverified (curl blocked).
- **Transplant directives:** (1) "demo parsed / insights validated 14:32" state chips in match history. (2) dashboard "this week" hub aggregating sessions, rating delta, rank movement, next practice block. (3) ranking-table density with a cyan pulse accent for live states.

#### Esportal / Fragnet Arena (Sweden) — stat-UX legacy worth keeping
- **UI/UX patterns:** profile with matches, K/D, HS%, streaks; its most distinctive decision: **showing per-match "Win% Chance" — the matchmaker's own fairness calculation — instead of average enemy Elo**; rank via 5 placement matches; seasonal ladders; community "gathers."
- **Transplant directives:** (1) retrospective win-probability header on match detail ("you had 38% — upset win") to contextualize coaching. (2) 5-match calibration in onboarding with "calibrating..." placeholders on the radar. (3) visible season-reset markers in history so progress narratives don't blur.

#### scope.gg (Cyprus/ex-CIS, CS.MONEY group)
- **What/traction:** CS2 analytics for MM+FACEIT; claims 2M registered users; Trustpilot ~4.0-4.2 (32-39 reviews; praised simple/accurate, billing/Discord-support complaints). Positioned 2026 as the accessible entry point vs Leetify (depth) and Refrag (drills).
- **UI/UX patterns:** Dashboard (ADR, HLTV 2.1, KAST + aim block: TTK, HS%, first-bullet accuracy + utility block: flash duration, nade damage); **My Progress: rolling 30-match trend split "previous 15 vs current 15"** — an honest improvement frame; Map Performance T/CT splits; 2D demo viewer with **grenade icons pinned to the round timeline**; Grenade Predictor/Lineups (side- and type-filtered interactive map with video tutorials); Tactical Board (draw strategies); head-to-head Comparing Tool; pre-match opponent scouting; auto-recorded cloud clips of aces/clutches.
- **Visual identity (curl-verified):** graphite #14171b / #1f2329 / #252a31 with deep-navy sections #121533 / #1c2144; primary violet #7661ff; lime #c5ff7b; cyan #8ee0e8; alert red #f7344b; text ramp #e0e3eb -> #828791.
- **Transplant directives:** (1) adopt 15-vs-15 rolling comparison as the default trend unit (cyan = current 15, dim = previous 15). (2) pin utility icons to our replay round-timeline + side/type-filtered lineup picker; coach chat deep-links "this smoke at 1:14" into the replay. (3) lead dashboard with session/economy tiles; bury HLTV-style tables one level down.

#### Skybox (Denmark — Copenhagen; pro-grade)
- **What/traction:** founded 2018 by caster Anders Blume; demo-review suite used by tier-1 CS teams/tournaments; now pressured by rival CS2.CAM ($120/mo pro tier). Copenhagen + Noesis = a Danish CS-analytics cluster.
- **UI/UX patterns:** 3D playback with free camera synced to 2D radar; **Tactic-spotter AI auto-detects and labels team strategies from demos**; Veto Simulator for BO1/3/5 pick scenarios; multi-demo organization for coach workflows.
- **Transplant directives:** (1) auto-detected tactic labels ("A-split," "B rush," "default") as filterable chips on rounds — the most coach-like feature in the pro stack. (2) synced first-person/3D thumbnail under the 2D radar cursor. (3) lightweight veto-sim card in match prep.

#### 3D Aim Trainer (Belgium) + G2 Army + NAVI (fan layer)
- **3D Aim Trainer (BE):** 12M+ players claim, SteelSeries partnership; zero-friction browser play before any account; game-matched sensitivity/FOV presets so training transfers. Transplant: one free analysis before signup; drills parameterized with the user's actual sensitivity/crosshair.
- **G2 Army (DE, Dec 2025, XBorg FanBase platform):** quests, battlepass, dual currency (spendable points vs status XP), monthly+yearly leaderboards, and a "Copilot" that auto-launches engagement campaigns on trigger events. Transplant: **proactive coach triggers** — the AI coach opens a thread when something notable happens ("new personal best entry-kill rate — want a T-side drill?"); dual-currency progression (XP badge vs spendable analysis credits).
- **NAVI (UA):** no "PRO app" exists (memory artifact — it's a merch line); fan stack = Socios fan token (polls/quizzes/leaderboard), navi.gg content grid, black + signature yellow identity. Transplant: onboarding fandom seeding — pick your favorite pro/team first; it presets the radar target and default ghost.

### Rising 2025-2026 AI coaching startups

#### Refrag / Refrag Coach (HQ undisclosed) — the CS2 diagnose-to-drill leader
- **What/traction:** CS2 training SaaS (private practice servers) + "Refrag Coach" auto-analysis of Premier/FACEIT history that "builds a custom training routine around those weaknesses." Claims 550k+ users; Coach included in all tiers; a Steam bot DMs a link to your match breakdown right after each match.
- **UI/UX patterns:** detected weakness -> one-click auto-generated in-game routine (diagnosis down to "poor crosshair placement in specific map sectors"); post-match push + deep link.
- **Visual identity (curl-verified):** background **#0f141a near-black navy; slate panels #222c39/#323f51; periwinkle #6a7dff; orange accent #ff774d; mint-cyan #6affdb** — a shipped CS2 product running nearly our exact navy/orange/cyan triad. Direct market validation of our design language.
- **Transplant directives:** (1) every AI-detected weakness gets a "Generate drill" CTA emitting a concrete practice artifact (server command/practice config). (2) post-analysis notification with deep link the moment a demo finishes parsing. (3) reserve orange strictly for "fix this" CTAs, cyan for positive/insight highlights — exactly how Refrag deploys theirs.

#### iTero (UK — LoL AI coach)
- **What/traction:** Desktop + Overwolf; self-claims 500k+ downloads, 4.4 rating; free with ads, premium "customise the AI models."
- **UI/UX patterns:** drafting simulator; 1-click apply builds; overlay timers as thin glanceable strips; post-game **"Macro Coach" outputs a persistent strategic playbook tailored to your playstyle** — narrative macro advice, not raw stats.
- **Visual identity (curl-verified):** teal #00d7c2 / #7de8e2 on near-black #0a0a0a/#171717/#262626; alert red #fb2c36; gold #edb200.
- **Transplant directives:** (1) steal the playbook: a persistent per-player strategy document the chat references and revises after every match, instead of disposable tips. (2) premium tier = tune the AI (aggression bias, focus areas). (3) timeline stripes for utility/economy windows in the replay.

#### Omnic.AI / Omnic Forge (US — Maine; Rich Miner-backed)
- **What/traction:** Computer-vision analysis of gameplay video (VALORANT, Fortnite, RL, OW2, Madden); verified pro/B2B traction: M80 partnership (Mar 2025), exclusive "Performance Intelligence Partner" of NACE collegiate esports (Jul 2026).
- **UI/UX patterns:** post-game advice with **auto-cut highlight clips attached as evidence**; 7-metric aim suite (Time To Target, Pre-Aim Ratio, Head Targeting Ratio...); collectible leveling "Player Cards"; "1v1 Compare"; **"Plays Like" pro-similarity feature**.
- **Transplant directives:** (1) attach an auto-cut clip to every AI insight — evidence-first coaching. (2) "Plays Like <pro>" nearest-neighbor readout on the radar with one sentence of why. (3) cosmetic player card leveling with training streaks — gamification that never distorts stats.

#### NVIDIA Project G-Assist (US — shipped 2025, free in NVIDIA App)
- **UI/UX patterns:** Alt+G summons in-game chat overlay (voice+text); replies **embed real-time charts** (FPS-over-time, latency); **executes actions, not just advice** (applies optimized settings, installs its own plugins on request, drives peripherals); 2026 Plug-In Hub with mod.io.
- **Transplant directives:** (1) global hotkey summon/dismiss for our coach overlay. (2) every diagnostic card carries an executable remedy button ("apply practice config," "queue drill"). (3) when the coach cites a stat in chat, inline the mini time-series in the reply bubble.

#### Backseat AI (US — Tyler1's LoL voice buddy) and voice coaching
- **What/traction:** Riot-approved live voice companion with streamer personas (Tyler1, Emiru); free+premium; niche scale. **STATUP.GG / Gamer Republic (KR)**: vision-recognition + RL + voice-synthesis live voice coach for LoL, B2B team training, TIPS-backed, opened Seattle office 2025.
- **Pattern:** voice coaching is bifurcating — personality companions (Backseat, Razer Ava) market well; terse live copilots (STATUP, Trophi, G-Assist) ship and retain.
- **Transplant directives:** (1) optional voice persona with a tone dial (strict IGL <-> hype duo), default professional. (2) live callouts as short spoken phrases, never mid-round text walls. (3) vision-based capture is the robust path where demo data is thin — architect replay to fuse demo parsing with optional screen capture later.

#### UpForge (Valorant-first, beta) + PureSkill.gg (US, CS2)
- **UpForge:** auto-records ranked matches, returns a **"match debrief" in 10-30 min: capped at 3 priority fixes**, each linked to a key-fight moment + drill; AI-to-human coach escalation when the same pattern recurs; honest per-row processing states ("analyzing — ready in ~15 min"). Transplant all three: 3-fix cap, recurring-pattern quest cards, visible processing states.
- **PureSkill.gg:** "the only automated coach for CS2" (self-claim); fully automated demo pipeline; **public docs explaining how the ML judges you** — transparency as trust device. Transplant: a "how the AI judges you" link near every verdict.

#### Track Titan (UK — $5M seed Dec 2025, Partech) — where AI-coach capital actually landed
- **What/traction:** "Strava of motorsport": auto-records sim-racing telemetry, compares laps to pros, tells you where you lose time; MOZA/Fanatec integrations.
- **Transplant directives:** (1) side-by-side timing readouts at map waypoints between you and the pro ghost (spawn->site seconds, first-contact time). (2) per-zone delta tables ("where you lose time vs pro" per map area).

#### Razer Project Ava (Singapore/US) — cautionary
- CES 2025 "AI esports coach" -> CES 2026 re-revealed as $20-reservation 3D hologram desk companion; GDC 2026 "agentic" chapter; unshipped as of Aug 2026; press mocking ("AI waifu" confusion). Lesson: embodiment/personality without a shipped skill loop reads as gimmick. Keep our coach disembodied with one consistent avatar mark for continuity.

#### Dead pool / scan-level (verification notes)
- **GGPredict (Poland, CS AI coach): defunct** — the direct cautionary precedent for consumer CS-AI-coach economics (compete on evidence + drills, not generic "AI tips").
- Skill Capped / GameLeap: video-subscription businesses, no shipped AI coach. Voltaic: human coaching + Aimlabs benchmarks. SenpAI.gg (TR/YC S21): status unclear — site behind JS challenge, no 2025-26 news. Insights.gg (CA): alive, VOD review with timestamped comment rail + telestration, **no AI features** — its comment-rail UX is still worth stealing for our replay annotations.
- Long tail of tiny LoL/VALORANT AI tools: Hakko AI, Meeko.ai, LoL Sensei, valocoach.ai, CoachCamel.

---

## GLOBAL PATTERN SYNTHESIS
What world-class gaming analytics UIs consistently do:

1. **One composite headline metric, endlessly drillable.** Leetify Rating, OP Score, GPI, IMP, AI-Score, Accuracy% — a single number leads every surface, always role/rank-contextualized, and every level below it is clickable. Nothing dead-ends.
2. **Benchmark-relative everything.** Raw stats are never shown naked: green/red vs same-rank baseline (Leetify), percentile chips "top X%" (tracker.gg), rank-anchored 0-100 scales (GPI). The comparison IS the information.
3. **Radar = playstyle fingerprint, and axes = drills.** The radar earns its place only when overlaid (you-now vs you-before vs target) and when each axis has a "practice this" exit (Aimlabs, Mobalytics, Leetify).
4. **Match history rows are scorebugs.** Hard two-color W/L semantics (OP.GG blue/red), 40px scannable rows, one impact chip + badges; the row is the product's atom.
5. **Curves get compressed into words.** OP Score timeline -> 14 keyword chips; chess.com eval graph -> Key Moments. Mass-market users read narratives, not graphs — generate the narrative from the graph.
6. **Glyph taxonomies for moments, with one rare aspirational badge.** Chess.com's Brilliant/Blunder color ramp, MVP/ACE. A coveted, rare badge (Brilliant) is a retention engine; "ACE on a losing team" keeps losses motivating.
7. **Advice ships as a prioritized shortlist of ~3, each quantified, evidenced, and actionable.** Garmin's 3 Opportunities, UpForge's 3-fix debrief, Trophi's per-corner time-loss, Leetify Focus Areas -> drill. Every finding carries a cost figure, an attached evidence clip (Omnic's strongest pattern), and a next action. Never 15 findings.
8. **The winning 2025-26 loop is diagnose -> generate artifact, not diagnose -> paragraph.** Weakness becomes a drill/routine/config (Refrag, Aimlabs, UpForge), a retry-able moment (chess.com), or a revisable playbook (iTero). Best-in-class coaches also *initiate*: proactive threads on trigger events (G2 Copilot pattern), post-analysis pings with deep links (Refrag's Steam bot), and executable remedy buttons instead of advice text (G-Assist).
9. **The credible reference is your best self; the aspirational one is the pro.** Catalyst's True Optimal Lap composites the user's own driven sectors; only then does a pro reference feel fair (Trophi).
10. **Dark theme, one brand accent, semantic hues for data, elevation ladders, mono numerals.** Verified palettes cluster on near-black blue-charcoal bases (#0f1923 TRN, #1c1c1f OP.GG, #0c1f23 STRATZ, #19171e Leetify, #0f141a Refrag) + one saturated brand hue + green/red/amber strictly for meaning; DAK.GG runs a 7-step charcoal elevation ladder that keeps density readable; replay/map surfaces stay monochrome so data layers own all color (Noesis). Typography: sporty condensed display + mono/tabular numerals (Saira at TRN, Poppins+SFMono at Leetify, SUIT/Pretendard at YOUR.GG) — our JetBrains Mono choice is on-trend. Refrag shipping #0f141a navy + #ff774d orange + #6affdb cyan is direct market validation of our exact triad.
11. **Dashboards are card grammars.** Fixed anatomy (title, hero number, sparkline, one action), user-arrangeable interest cards (STRATZ adaptive cards appear/disappear with your situation), per-game re-skins on one chassis (tracker.gg).
12. **Automation-first onboarding; value before signup; calibration made visible.** Auto-detect installs/accounts, zero forms (Blitz); show a real analyzed result before asking for login (3D Aim Trainer, FOW instant search, GRID's gallery-of-outcomes); then a 5-match calibration period with "calibrating..." placeholders on the radar (Esportal placements) so early numbers don't overclaim.
13. **Ritualized progress: recaps, personal bests, social compare.** Wrapped-style year/season recaps (Leetify 2025, OP.GG Awards), PB celebrations, friends/club leaderboards, head-to-head compare pages, rolling "previous 15 vs current 15" trend windows (scope.gg) as the honest default improvement frame.
14. **Respect the play session.** Overlay vs second-screen as explicit modes (Overwolf ecosystem), coach verbosity dials (Catalyst's 3 levels), invisible resource footprint; voice coaching ships as terse copilot, not personality theater (G-Assist/Trophi vs Razer Ava) — and never inject ads/upsell into coaching surfaces (Blitz's 2.5/5 Trustpilot is the cautionary tale).
15. **Trust is a designed surface.** Provenance badges on stats (GRID "official server data"), validated-at timestamps (Esports Charts' 02:00 UTC validation pass), honest processing states ("analyzing — ready in ~15 min," UpForge), sample-size visibility, raw CSV/JSON export (stat.ink), and "how the AI judges you" method links (PureSkill.gg). Coaching products live or die on believed numbers.

## WHAT NOBODY DOES YET — WHITE SPACE FOR OUR AI ARCHITECTURE

Nearest existing neighbors, for honesty: Tencent's 营地AI (HoK) already ships a chat assistant grounded in the user's own match records (CN-only, no confidence display, no self-correction); YOUR.GG and Omnic Forge do "which pro plays like you" similarity matching (no replay/ghost integration); ghost-delta coaching exists in racing only (Garmin Catalyst, Trophi, Track Titan); STRATZ ships counterfactual simulation (no conversational layer); Refrag closes the diagnose->drill loop (no uncertainty, no pro ghosts). No product combines grounded chat + visible uncertainty + self-correction + spatial ghost divergence — that combination is ours to take.

### 1. Self-correcting coach (visible model updates)
No product on the market shows its coach *changing its mind*. Chess.com re-tuned "Brilliant" silently; Leetify recalibrates ratings via blog post. White space:
- **Prediction ledger**: coach advice cards carry a resolution state ("I advised X on Aug 2 -> your entry success went 41%->54% -> keeping this advice" / "-> no change -> revising"). An "advice changelog" panel in the AI-coach screen.
- **Calibration as UI**: a small "coach accuracy" tile (how often its predictions verified) — trust through admitted error, which no competitor dares to surface.
- Visual: revision events rendered as diff-style annotations (old advice struck through in muted gray, new advice in orange) with JetBrains Mono timestamps — fits our technical identity perfectly.

### 2. Belief-state confidence (uncertainty as a first-class visual)
Every competitor ships point estimates (OP Score 7.2, +3.1 rating, "you'll hit Plat II"). None show uncertainty. White space:
- **Confidence bands on every claim**: forecast ribbons on trend charts; "evidence: 14 rounds" sample-size chips; low-evidence stats auto-dimmed instead of hidden.
- **Hedge-tiered coach language** bound to belief state: "certain / likely / hunch" prefixes with distinct chip styles in chat; replay annotations rendered at opacity proportional to confidence.
- **Belief timeline in replay**: our round graph can show what the AI believed mid-round (e.g., "78% you should rotate") — nobody else even has the data model for this. OP.GG proves timeline+keywords is readable; we add the confidence dimension.

### 3. Ghost-mode divergence analysis (FPS positioning ghosts)
Ghost coaching is solved in racing (Catalyst, Trophi, Track Titan — where 2025-26 coaching capital landed) and absent in FPS at consumer level. Noesis stacks rounds but has no reference model; Skybox labels tactics but doesn't diff them; no CS/VALORANT tool overlays a pro ghost with quantified divergence. White space:
- **Divergence quantified in win-probability and seconds** at each fork ("held W 0.8s late: -12% round WP"), Trophi-style per-corner loss transplanted to map nodes.
- **Divergence heatmap** aggregated across 20+ rounds (Noesis stacking + ghost): where your pathing *systematically* departs from the pro's on this map/side/buy-type.
- **Retry-the-fork**: pause at divergence point, hide outcome, let the player click their move, then reveal ghost + coach explanation (chess.com Retry transplanted to a 2D map).
- Color law: you = orange trail, pro ghost = cyan trail, divergence wedge shaded between them — our exact palette, unused by anyone in the genre.

### 4. Per-pro-player / per-tournament advice
OP.GG/DEEPLOL surface pro builds and live pro games generically; nobody personalizes them. White space:
- **Pro mentor selector**: pick a pro (per role/map); he becomes the radar's target polygon, the default ghost source, and the coach's example library ("here's how NiKo held this angle in round 19 vs FaZe").
- **Tournament-meta cards**: "since the Major patch, B-site smokes moved — 71% of pro rounds now use X" with jump-to-pro-round evidence; advice expires/updates with the meta (ties into the self-correcting changelog).
- **Style-match**: "your playstyle fingerprint is closest to ropz (83% match)" — Mobalytics' fingerprint radar + our per-pro data = a shareable identity feature no one offers.

### Cross-cutting native advantage
Every deep-dived product is a web/Electron app except Catalyst (dedicated hardware). A PySide6 native desktop app can win on: instant demo scrubbing (Noesis's KPI), 144Hz replay rendering, offline analysis, and zero-ad professional chrome — the "Garmin of CS coaching" positioning.

---

## KEY SOURCES (verification trail)

**Tier-1 fetches/searches (this session):** mobalytics.gg/gpi + support.mobalytics.gg (GPI mechanics) · esportsinsider.com/2025/03/esl-faceit-group-mobalytics-acquisition · leetify.com/blog/leetify-rating-update + leetify.com/blog/leetify-rating-explained + northdata.com Leetify AB + trustpilot.com/review/leetify.com · tracker.gg/valorant + trackercdn.com CSS bundles (palette/typography) + play-ascend.com/blog/best-valorant-tracker · blitz.gg + trustpilot.com/review/blitz.gg + espn.com/gaming (Swift buys Blitz 2019) + medium.com/blitz-press (Combat Overlay) · op.gg + c-lol-web.op.gg CSS (palette) + help.op.gg (OP Score/MVP-ACE) + en.namu.wiki/w/OP.GG · deeplol.gg + deeplol.net/deeplol-features · aimlabs.com (theme-color) + aimlabs.com/articles (benchmarks rank) + techcrunch.com Statespace $15M · noesis.gg (product + Bang & Jensen ApS, Copenhagen) + bo3.gg demo-analyzer roundup · chess.com/news/view/game-review-design-update + chess.com JETINATE guide + support.chess.com (Insights) + adweek.com (250M users) · garmin.com Catalyst 2 press + speedsf.com Catalyst review + windingroad.com · trophi.ai + tracxn/pitchbook Trophi + simracingcockpit.gg review · stratz.com (HTML palette) + medium.com/stratz (dashboard, IMP) · metafy.gg (curl palette) + techcrunch/crunchbase Metafy funding · esportsadvocate.net (ProGuides shutdown) · forbes.com (Overwolf $300M payouts 2025).

**Asia sweep (agent-verified):** fow.lol · fmkorea.com/2971466058 · dak.gg + DAK.GG ER App Store + PUBG developer portal featured apps · your.gg + invenglobal.com PLAYREPORT + etnews.com/20240429000050 (Gen.G acquires Gigitix) · wanplus.cn · sj.qq.com MAX+ listing + maxjia.com · baike.baidu.com 王者营地 + apps.apple.com id1102305688 · en.wikipedia.org/wiki/WeGame · stat.ink/faq · uniteapi.dev/jp · svlabo.jp · gamewith.jp SV:WB tool · dotabuff.com/plus · stratz.com + mcpmarket.com/server/stratz.

**Europe sweep (agent-verified):** esportsadvocate.net/2025/08/bayes-esports-files-for-insolvency · yogonet.com (GRID acquires Bayes IP, Sept 2025) · grid.gg/open-access · escharts.com + EWC 2026 Viewership Hub press · hltv.org/news/39727 (PGL acquires Esportal) + arena.fragnet.net + trustpilot.com/review/esportal.com · tracxn gosu.ai deadpool · pley.gg/about · scope.gg + trustpilot.com/review/scope.gg + esports.gg scope review · esportsinsider.com/2025/12 (G2 x XBorg) + g2army.g2esports.com · socios.com NAVI token + navi.gg · skybox.gg + cs2.cam/compare/skybox · 3daimtrainer.com + Crunchbase · floatpeak.com refrag-vs-leetify-vs-scopegg.

**AI-startup scan (agent-verified):** refrag.gg/coach + wiki.refrag.gg (palette curl-verified) · itero.gg (palette curl-verified) · omnic.ai/forge + mainestartupsinsider.com ($750k Rich Miner) + esportsinsider.com (M80, Mar 2025) + gamespress.com (NACE, Jul 2026) · ycombinator.com/companies/senpai-gg + dailysabah.com Falcon AI · backseat.gg + esports.gg Tyler1 announcement · nvidia.com G-Assist + tweaktown.com (self-installing plugins) + NVIDIA RTX AI Garage Gamescom 2025 · razer.com Project Ava CES/GDC 2026 blogs + gizmodo.com skepticism · pureskill.gg · voltaic.gg + vlr.gg/510494 · insights.gg · techfundingnews.com (Track Titan $5M, Dec 2025) · greater-seattle.com (Gamer Republic/STATUP, Sept 2025) · beyondgames.biz (trophi $3.3M) · upforge.gg · techcrunch.com/2026/05/25 (Lucra) · axios.com/2026/06/26 (General Intuition).
