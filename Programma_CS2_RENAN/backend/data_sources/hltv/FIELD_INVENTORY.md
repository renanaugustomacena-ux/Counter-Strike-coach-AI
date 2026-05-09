# HLTV Player Stats — Complete Field Inventory
# Verified 2026-05-07 against woxic (8574, Rating 1.0) and m0NESY (19230, Rating 2.0)

## Overview Page (no date filter)
### Profile
- nickname: .player-summary-stat-box-left-nickname
- real_name: .player-summary-stat-box-left-player-name
- age: .player-summary-stat-box-left-player-age  (text: "21 years")
- country: .player-summary-stat-box-left-flag img.flag[title]

### Rating
- rating_value: .player-summary-stat-box-rating-data-text  (e.g. "1.25")
- rating_version: .player-summary-stat-box-data-description-text  (text contains "Rating 1.0" or "Rating 2.0")
- rating_tier: .player-summary-stat-box-rating-text  (e.g. "Good", "Suspect")

### Summary Boxes (6 boxes, same structure for Rating 1.0 and 2.0)
- selector: .player-summary-stat-box-data-wrapper
- value: child .player-summary-stat-box-data  (text content)
- label: child .player-summary-stat-box-data-text  (first text node only, exclude tooltip)
- above_avg: wrapper has class "aboveAverage"
- Fields: Round swing, DPR, KAST, Multi-kill, ADR, KPR
- Note: "Round swing" and "Multi-kill" may show "-" for some players

### Legacy Stats (14 rows)
- selector: .stats-row
- structure: two span children [label, value]
- Fields: Total kills, Headshot %, Total deaths, K/D Ratio, Damage/Round, Grenade dmg/Round,
          Maps played, Rounds played, Kills/round, Assists/round, Deaths/round,
          Saved by teammate/round, Saved teammates/round, Rating 1.0

### Role Stats (120 entries = 40 stats × 3 sides)
- selector: .role-stats-row
- sides: .stats-side-combined, .stats-side-ct, .stats-side-t
- each row: .role-stats-top > .role-stats-title (stat name) + .role-stats-data (value)
- data attributes on .role-stats-data: data-original-value, data-per-24-round-title, data-per-24-round-value
- 40 stats per side across 7 sections

### Section Scores (7 sections)
- selector: .role-stats-section-title
- extract: section name (first text) + "XX/100" score via regex
- Sections: Firepower, Sniping, Opening, Utility, Clutching, Positioning, Eco

## Individual Page (/stats/players/individual/{id}/{nick}?startDate=...&endDate=...)
### 23 stats via .stats-row (verified 2026-05-07 against woxic)
- Kills, Deaths, Kill / Death, Kill / Round
- Rounds with kills
- Total opening kills, Total opening deaths, Opening kill ratio, Opening kill rating
- Team win percent after first kill, First kill in won rounds
- 0 kill rounds, 1 kill rounds, 2 kill rounds, 3 kill rounds, 4 kill rounds, 5 kill rounds
- Rifle kills, Sniper kills, SMG kills, Pistol kills, Grenade, Other

## Career Page (/stats/players/career/{id}/{nick}?startDate=...&endDate=...)
### Year-by-year rating table
- selector: .stats-table tbody tr
- columns: Period, All, Online, LAN, Majors
- rows: one per year (e.g. 2018-2026) + "Career" total row
- 13 typical rows

## Weapons Page (/stats/players/weapon/{id}/{nick}?startDate=...&endDate=...)
### Per-weapon kill counts — CHART ONLY (verified 2026-05-07)
- NOTE: URL path is singular "weapon", not "weapons"
- Data is rendered as Raphaël.js SVG bar chart — NO table/text DOM
- Kill counts not available via BeautifulSoup text parsing
- **USE individual page weapon categories instead** (rifle_kills, sniper_kills, etc.)
- Sub-page fetch REMOVED from stat_fetcher.py to avoid wasting a request

## Opponents Page (/stats/players/opponents/team/{id}/{nick}?startDate=...&endDate=...)
### Per-team stats
- NOTE: URL has extra "team" segment between "opponents" and player ID (verified 2026-05-07)
- selector: .stats-table tbody tr
- columns: Team, Maps, K-D Diff, K/D, Rating 2.0
- ~100 team entries

## Clutches Page (/stats/players/clutches/{id}/{tier}/{nick}?startDate=...&endDate=...)
### Per-match event table
- tiers: all, 1on1, 1on2, 1on3, 1on4, 1on5
- selector: .stats-table tbody tr
- columns: Date, Team1, Team2, T1, T2, Map, Status, Type, Round
- ~100 rows per tier
- For JSON: store event COUNT per tier, not individual events

## Multikills Page (/stats/players/multikills/{id}/{tier}/{nick}?startDate=...&endDate=...)
### Per-match event table
- tiers: two, three, four, five
- selector: .stats-table tbody tr
- columns: Date, Team1, Team2, T1, T2, Map, Round
- ~100 rows per tier
- For JSON: store event COUNT per tier, not individual events

## Storage Strategy
- ProPlayer: update real_name, country, age from overview profile
- ProPlayerStatCard dedicated columns: rating_2_0, dpr, kast, impact (from legacy stats), adr, kpr, headshot_pct, maps_played, opening_kill_ratio, opening_duel_win_pct
- ProPlayerStatCard.clutch_win_count: sum of clutch events across tiers
- ProPlayerStatCard.multikill_round_pct: from legacy stats or computed
- ProPlayerStatCard.detailed_stats_json (MAX 32KB): {
    rating_version, rating_tier,
    summary_boxes: {label: {value, above_avg}},
    legacy_stats: {label: value},
    role_stats: {combined: {}, ct: {}, t: {}},
    section_scores: {section: score},
    individual: {stat: value},
    career: {year: {all, online, lan, majors}},
    weapons: [{rank, name, kills}],  (all ~50)
    opponents: [{team, maps, kd_diff, kd, rating}],  (all ~100)
    clutch_counts: {tier: count},
    multikill_counts: {tier: count}
  }
