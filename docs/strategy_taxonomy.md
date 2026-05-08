# Strategy Taxonomy — `coachingexperience.strategy_label`

GAP-09 (plan §4 Phase D, AUDIT §10). Closed taxonomy of tactical strategies
used to label `CoachingExperience` rows for retrieval-by-playbook coaching.

As of 2026-05-07, **61,894 rows** carry labels across **66 mined
strategies** and **9 maps**, produced by `tools/mine_shard_strategies.py`
from 258 pro-match shards. An additional **~100 strategies** are defined
below but not yet emitted by the heuristic miner (marked "—"); most are
detectable from existing shard data and will ship when `classify_round()`
is extended. Total taxonomy: **180 distinct labels** (28 setpiece, 24 economy,
17 rotation, 79 playbook, 32 individual). The label column
is nullable: legacy rows stay `NULL` until a backfill / classifier
assigns them.

Filtering this column is a hot retrieval path — indexed, and the
ExperienceBank retrieval chain supports `strategy_family` filtering
on all 4 code paths (FAISS + brute-force × retrieve_similar +
retrieve_pro_examples).

## Label format

`{family}.{strategy}` — lowercase, dot-separated. Two-level only. The
family is one of the five fixed buckets below. Adding a new family is a
schema change (the RAG retriever and the coach LLM prompt both inspect
families); adding a new strategy under an existing family is just a label.

## Families

### `setpiece` — round-level tactical shape (9,486 rows)
Utility usage patterns and round tempo classification. Applies to both
T-side executes and CT-side holds/retakes.

| Label | Count | Description |
|---|---|---|
| `setpiece.utility_heavy` | 4,342 | ≥3 utility events in first 30s — coordinated site take or deep hold |
| `setpiece.fast_rush` | 2,112 | All deaths within 10s of first contact — speed execute or rush |
| `setpiece.site_execute` | 1,818 | 1-2 utility events + bomb plant — structured site take |
| `setpiece.retake` | 604 | CT retake after bomb plant (CT won, bomb was planted then defused) |
| `setpiece.default_hold` | 525 | CT hold that denied bomb plant entirely |
| `setpiece.dry_execute` | 47 | Zero utility, bomb planted — dry take |
| `setpiece.slow_default` | 38 | Round lasted >25s before first death — slow map control |
| `setpiece.a_default_execute` | — | Standard A-site take with smoke + molly + flash on default angles |
| `setpiece.b_default_execute` | — | Same for B-site |
| `setpiece.a_split` | — | Two-pronged A-site take from main + ramp/connector |
| `setpiece.b_split` | — | Two-pronged B-site take |
| `setpiece.contact_play` | — | No-utility close-range entry |
| `setpiece.fake_a_take_b` | — | Utility/sound feint on opposite site |
| `setpiece.fake_b_take_a` | — | Same, reversed |
| `setpiece.mid_to_a` | — | Mid-control conversion to A |
| `setpiece.mid_to_b` | — | Mid-control conversion to B |
| `setpiece.utility_stack` | — | ≥5 utility events in first 20s — heavy coordinated execute (stricter than utility_heavy) |
| `setpiece.post_plant_passive` | — | Bomb planted, T holds angles without pushing — passive post-plant |
| `setpiece.post_plant_aggressive` | — | Bomb planted, T pushes CT during retake — aggressive post-plant |
| `setpiece.post_plant_molotov` | — | Molotov on bomb site after plant — deny defuse |
| `setpiece.timeplay` | — | First death >45s into round — T clock-burning strategy |
| `setpiece.delayed_execute` | — | Utility events after 30s mark, then site take — late execute |
| `setpiece.eco_rush` | — | Fast-rush timing + eco-round economy — eco rush |
| `setpiece.anti_eco_stack` | — | Heavy utility used against eco opponents |
| `setpiece.double_utility_lineup` | — | 2+ utility events within 2s — coordinated lineup throw |
| `setpiece.full_execute` | — | All 5 T commit to same site — full team execute (needs positional) |
| `setpiece.default_spread` | — | 5 T spread across map for first 30s (needs positional classifier) |
| `setpiece.retake_utility` | — | CT utility combo (smoke+flash+molly) during retake phase |

Labels without counts are defined in the taxonomy but not yet emitted by
the heuristic miner. Labels marked "needs positional" require Phase 1C
Hopfield classifier; all others are detectable from existing shard data.

### `economy` — round-economy decisions (12,263 rows)
Buy-shape strategies tied to team_economy / round_phase / score state.
Selected per round, not per moment. Maps to PlayerTickState.team_economy.

| Label | Count | Description |
|---|---|---|
| `economy.full_buy` | 6,304 | Average equipment ≥$4000 — full rifles + utility |
| `economy.force_buy` | 1,035 | $2000-$4000 range — sub-optimal kit to contest |
| `economy.bonus_round` | 916 | Post-win round with ≥$4000 equipment surplus |
| `economy.anti_eco` | 902 | Facing opponents with <$2000 avg equip — anti-eco setup |
| `economy.pistol_default` | 900 | Rounds 1 or 13 — pistol round |
| `economy.half_buy` | 697 | $2000-$3000 range, sub-force |
| `economy.team_save` | 535 | Average equipment <$2000, not a pistol round — eco |
| `economy.eco_win` | 411 | Won round despite team_save/eco equipment |
| `economy.eco_round` | 405 | <$1500 average — deep eco |
| `economy.hero_buy` | 58 | Single player has ≥$4500 while team avg <$2000 |
| `economy.full_save` | — | Pistol/knife only, preserve next round |
| `economy.eco_with_pistol` | — | Save kit, equip armor + utility on a pistol |
| `economy.semi_buy` | — | Mixed-kit hybrid (some rifles, some pistols) |
| `economy.glass_cannon` | — | Rifle/AWP + no armor — money constraint weapon-over-armor |
| `economy.smg_farming` | — | SMG weapon + ≥2 kills — kill-reward farming strategy |
| `economy.deagle_force` | — | Desert Eagle primary + team avg money <$2500 |
| `economy.upgraded_pistol` | — | Five-SeveN/CZ/Tec-9 + armor — upgraded pistol buy |
| `economy.awp_save` | — | Player survives losing round while holding AWP |
| `economy.second_round_force` | — | Round 2 or 14 + force-buy money range |
| `economy.reset_round` | — | 3+ consecutive losses + deep eco — economy reset pattern |
| `economy.double_awp` | — | Two AWPs on same team in same round |
| `economy.pistol_armor` | — | Armor + pistol only buy (not full eco, not rifle buy) |
| `economy.galil_famas_buy` | — | Budget rifle (Galil/FAMAS) — $2500-$3500 equipment range |
| `economy.loss_bonus_max` | — | Team at max loss bonus ($3400) — impacts buy capacity |

### `rotation` — mid-round repositioning (1,205 rows)
Decisions about leaving a current position to reinforce another.

| Label | Count | Description |
|---|---|---|
| `rotation.ct_aggression` | 1,205 | CT team pushed ≥2 utility events + won — aggressive CT hold or push |
| `rotation.solo_to_bomb` | — | Single CT cross-map rotation to defuse |
| `rotation.stack_a` | — | Pre-round CT stack on A |
| `rotation.stack_b` | — | Pre-round CT stack on B |
| `rotation.late_rotation` | — | Reactive rotation after enemy commit confirmed |
| `rotation.fake_rotation` | — | Sound-bait rotation to draw enemy commit |
| `rotation.retake_default` | — | Standard 4-way CT retake post-plant |
| `rotation.retake_split` | — | Two-direction simultaneous retake |
| `rotation.contact_retake` | — | No-utility rush retake (low time on bomb) |
| `rotation.anchor_hold` | — | Single CT holds site vs 2+ T without rotating (needs positional) |
| `rotation.fast_rotate` | — | CT rotation within 5s of enemy contact on other site |
| `rotation.ct_stack_punish` | — | T executes on site with 1 CT while 3+ CT stacked elsewhere |
| `rotation.save_round` | — | Team saves instead of retake/fight — save rotation |
| `rotation.info_play` | — | Player peeks for information without committing (needs positional) |
| `rotation.ct_passive` | — | CT plays deep positions, gives up map control (needs positional) |
| `rotation.ct_forward` | — | CT takes aggressive forward map-control positions (needs positional) |
| `rotation.flank_kill` | — | Kill from behind enemy team — successful flank rotation |

### `playbook` — map-specific patterns (5,151 rows)
Map-qualified outcome patterns from pro matches. Format:
`playbook.{map}_{pattern}`. Always includes `map_name` filter at retrieval.

| Label | Count | Map | Description |
|---|---|---|---|
| `playbook.mirage_ct_denial` | 536 | mirage | CT hold denied bomb plant |
| `playbook.mirage_t_bomb_win` | 452 | mirage | T-side bomb plant → explosion win |
| `playbook.nuke_ct_denial` | 416 | nuke | CT hold denied bomb plant |
| `playbook.inferno_ct_denial` | 394 | inferno | CT hold denied bomb plant |
| `playbook.inferno_t_bomb_win` | 360 | inferno | T-side bomb plant → explosion win |
| `playbook.nuke_t_bomb_win` | 323 | nuke | T-side bomb plant → explosion win |
| `playbook.dust2_ct_denial` | 303 | dust2 | CT hold denied bomb plant |
| `playbook.overpass_ct_denial` | 292 | overpass | CT hold denied bomb plant |
| `playbook.dust2_t_bomb_win` | 260 | dust2 | T-side bomb plant → explosion win |
| `playbook.ancient_ct_denial` | 248 | ancient | CT hold denied bomb plant |
| `playbook.overpass_t_bomb_win` | 241 | overpass | T-side bomb plant → explosion win |
| `playbook.ancient_t_bomb_win` | 216 | ancient | T-side bomb plant → explosion win |
| `playbook.anubis_ct_denial` | 197 | anubis | CT hold denied bomb plant |
| `playbook.anubis_t_bomb_win` | 170 | anubis | T-side bomb plant → explosion win |
| `playbook.vertigo_ct_denial` | 95 | vertigo | CT hold denied bomb plant |
| `playbook.mirage_ct_defuse` | 82 | mirage | CT retake + defuse |
| `playbook.vertigo_t_bomb_win` | 78 | vertigo | T-side bomb plant → explosion win |
| `playbook.inferno_ct_defuse` | 73 | inferno | CT retake + defuse |
| `playbook.nuke_ct_defuse` | 72 | nuke | CT retake + defuse |
| `playbook.overpass_ct_defuse` | 61 | overpass | CT retake + defuse |
| `playbook.dust2_ct_defuse` | 54 | dust2 | CT retake + defuse |
| `playbook.ancient_ct_defuse` | 47 | ancient | CT retake + defuse |
| `playbook.anubis_ct_defuse` | 33 | anubis | CT retake + defuse |
| `playbook.mirage_eco_upset` | 29 | mirage | Eco round win (avg equip <$2000) |
| `playbook.train_ct_denial` | 25 | train | CT hold denied bomb plant |
| `playbook.inferno_eco_upset` | 19 | inferno | Eco round win |
| `playbook.dust2_eco_upset` | 15 | dust2 | Eco round win |
| `playbook.vertigo_ct_defuse` | 15 | vertigo | CT retake + defuse |
| `playbook.nuke_eco_upset` | 12 | nuke | Eco round win |
| `playbook.ancient_eco_upset` | 12 | ancient | Eco round win |
| `playbook.overpass_eco_upset` | 12 | overpass | Eco round win |
| `playbook.train_t_bomb_win` | 11 | train | T-side bomb plant → explosion win |
| `playbook.anubis_eco_upset` | 8 | anubis | Eco round win |
| `playbook.vertigo_eco_upset` | 5 | vertigo | Eco round win |
| `playbook.train_ct_defuse` | 2 | train | CT retake + defuse |
| `playbook.mirage_t_elimination` | — | mirage | T wins by eliminating all CTs (no bomb explosion) |
| `playbook.inferno_t_elimination` | — | inferno | T wins by eliminating all CTs |
| `playbook.nuke_t_elimination` | — | nuke | T wins by eliminating all CTs |
| `playbook.dust2_t_elimination` | — | dust2 | T wins by eliminating all CTs |
| `playbook.ancient_t_elimination` | — | ancient | T wins by eliminating all CTs |
| `playbook.overpass_t_elimination` | — | overpass | T wins by eliminating all CTs |
| `playbook.anubis_t_elimination` | — | anubis | T wins by eliminating all CTs |
| `playbook.vertigo_t_elimination` | — | vertigo | T wins by eliminating all CTs |
| `playbook.train_t_elimination` | — | train | T wins by eliminating all CTs |
| `playbook.mirage_force_buy_win` | — | mirage | Force-buy team wins ($2000-$4000 avg equip) |
| `playbook.inferno_force_buy_win` | — | inferno | Force-buy team wins |
| `playbook.nuke_force_buy_win` | — | nuke | Force-buy team wins |
| `playbook.dust2_force_buy_win` | — | dust2 | Force-buy team wins |
| `playbook.ancient_force_buy_win` | — | ancient | Force-buy team wins |
| `playbook.overpass_force_buy_win` | — | overpass | Force-buy team wins |
| `playbook.anubis_force_buy_win` | — | anubis | Force-buy team wins |
| `playbook.vertigo_force_buy_win` | — | vertigo | Force-buy team wins |
| `playbook.train_force_buy_win` | — | train | Force-buy team wins |
| `playbook.mirage_pistol_t` | — | mirage | T wins pistol round |
| `playbook.inferno_pistol_t` | — | inferno | T wins pistol round |
| `playbook.nuke_pistol_t` | — | nuke | T wins pistol round |
| `playbook.dust2_pistol_t` | — | dust2 | T wins pistol round |
| `playbook.ancient_pistol_t` | — | ancient | T wins pistol round |
| `playbook.overpass_pistol_t` | — | overpass | T wins pistol round |
| `playbook.anubis_pistol_t` | — | anubis | T wins pistol round |
| `playbook.vertigo_pistol_t` | — | vertigo | T wins pistol round |
| `playbook.train_pistol_t` | — | train | T wins pistol round |
| `playbook.mirage_pistol_ct` | — | mirage | CT wins pistol round |
| `playbook.inferno_pistol_ct` | — | inferno | CT wins pistol round |
| `playbook.nuke_pistol_ct` | — | nuke | CT wins pistol round |
| `playbook.dust2_pistol_ct` | — | dust2 | CT wins pistol round |
| `playbook.ancient_pistol_ct` | — | ancient | CT wins pistol round |
| `playbook.overpass_pistol_ct` | — | overpass | CT wins pistol round |
| `playbook.anubis_pistol_ct` | — | anubis | CT wins pistol round |
| `playbook.vertigo_pistol_ct` | — | vertigo | CT wins pistol round |
| `playbook.train_pistol_ct` | — | train | CT wins pistol round |
| `playbook.mirage_anti_eco_hold` | — | mirage | CT denies eco-round T push |
| `playbook.inferno_anti_eco_hold` | — | inferno | CT denies eco-round T push |
| `playbook.nuke_anti_eco_hold` | — | nuke | CT denies eco-round T push |
| `playbook.dust2_anti_eco_hold` | — | dust2 | CT denies eco-round T push |
| `playbook.ancient_anti_eco_hold` | — | ancient | CT denies eco-round T push |
| `playbook.overpass_anti_eco_hold` | — | overpass | CT denies eco-round T push |
| `playbook.anubis_anti_eco_hold` | — | anubis | CT denies eco-round T push |
| `playbook.vertigo_anti_eco_hold` | — | vertigo | CT denies eco-round T push |
| `playbook.train_anti_eco_hold` | — | train | CT denies eco-round T push |
| `playbook.mirage_overtime_round` | — | mirage | Round played in overtime (rounds >30) |
| `playbook.inferno_overtime_round` | — | inferno | Round played in overtime |
| `playbook.nuke_overtime_round` | — | nuke | Round played in overtime |
| `playbook.dust2_overtime_round` | — | dust2 | Round played in overtime |
| `playbook.ancient_overtime_round` | — | ancient | Round played in overtime |
| `playbook.overpass_overtime_round` | — | overpass | Round played in overtime |
| `playbook.anubis_overtime_round` | — | anubis | Round played in overtime |
| `playbook.vertigo_overtime_round` | — | vertigo | Round played in overtime |
| `playbook.train_overtime_round` | — | train | Round played in overtime |

### `individual` — per-player tactical micro (33,789 rows)
Single-player decisions or outcomes. Used by the coach to label "skill
axes" in player feedback.

| Label | Count | Description |
|---|---|---|
| `individual.trade_kill` | 5,621 | Kill within 128 ticks (2s) of a teammate death — trade frag |
| `individual.entry_frag` | 4,563 | First kill of the round on the winning side |
| `individual.opening_death` | 4,563 | First death of the round on the losing side |
| `individual.smoke_execute` | 4,043 | Smoke event within 32 ticks of a kill — smoke + kill execution |
| `individual.molotov_deny` | 4,013 | Molotov event in the round — area denial |
| `individual.exit_frag` | 4,011 | Last kill by the losing side — exit frag |
| `individual.awp_aggression` | 2,396 | Kill with AWP or SSG — sniper aggression |
| `individual.multi_kill` | 2,005 | 3+ kills in a single round |
| `individual.flash_assist` | 1,397 | Flash detonate within 32 ticks of a teammate kill |
| `individual.nade_kill` | 896 | HE grenade detonate within 32 ticks of a kill |
| `individual.ace` | 281 | 5 kills in a single round |
| `individual.held_angle` | — | Pre-aiming a specific angle from a static position |
| `individual.peek_jiggle` | — | Quick-peek to gather information without committing |
| `individual.lurk` | — | Solo flank away from main team push |
| `individual.support_trade` | — | Positioned to trade-kill teammate's death |
| `individual.utility_lineup` | — | Solo lineup throw from a memorized spot |
| `individual.awp_hold` | — | Static long-range hold with AWP |
| `individual.clutch_1v1` | — | Solo 1v1 clutch attempt |
| `individual.clutch_1v2` | — | Solo 1v2 clutch attempt |
| `individual.clutch_1v3plus` | — | Solo clutch vs 3+ enemies |
| `individual.fake_defuse` | — | CT defuse-bait while teammates retake |
| `individual.weapon_save` | — | Survived losing round with equipment >$4500 — weapon economy |
| `individual.pistol_ace` | — | 5 kills in pistol round (rounds 1/13) |
| `individual.clutch_win` | — | Won 1vX clutch (any X) — generic clutch victory |
| `individual.clutch_loss` | — | Lost 1vX clutch attempt |
| `individual.first_blood` | — | Opening kill of round regardless of round outcome |
| `individual.traded_death` | — | Death followed by teammate kill within 128 ticks — was traded |
| `individual.double_kill` | — | 2 kills within 128 ticks (2s) — rapid double |
| `individual.quad_kill` | — | 4 kills in a single round |
| `individual.post_plant_kill` | — | Kill after bomb_planted event — post-plant frag |
| `individual.retake_kill` | — | CT kill after bomb plant during retake phase |
| `individual.bomb_plant` | — | Player plants the bomb (planter identification) |
| `individual.bomb_defuse` | — | Player defuses the bomb (defuser identification) |
| `individual.solo_site_hold` | — | CT holds site alone vs 2+ T attackers (needs positional) |
| `individual.no_kill_round` | — | Player gets 0 kills in round — passive/saving round |

## Mining sources

### Active: `tools/mine_shard_strategies.py` (Path B — shard-direct)
Reads 270 `match_*.db` shards at `/DEMO_PRO_PLAYERS/match_data/`.
Heuristic classifier on tick data + events. Last run 2026-05-07:
258 shards, 5,025 rounds, 62,184 labels, 66 distinct strategies.

**Expansion path:** ~87 additional labels in this taxonomy are detectable
from existing shard columns (`matchtickstate` + `match_event_state`)
by extending `classify_round()` with new heuristics. Key areas:
economy sub-types (weapon detection), playbook map-outcome combinations,
individual round-level stats (double-kill, clutch, post-plant), and
setpiece timing patterns (timeplay, delayed execute). See
`docs/research/strategy_label_research_2026-05-07.md` for full
detectability assessment.

### Future: `tools/mine_coaching_experience.py` (Path A — monolith)
Reads from `RoundStats` in the monolith DB. Currently only 5 pattern
types and does NOT set strategy_label. Requires monolith rebuild (~22h).

### Future: Hopfield-prototype classifier (Phase 1C)
Use trained Hopfield prototypes to assign fine-grained labels based on
embedding distance, splitting broad labels (e.g., `setpiece.utility_heavy`)
into site-specific or player-role-specific variants. ~20 labels in this
taxonomy marked "needs positional" are targets for this classifier.

## Retrieval integration

- `ExperienceBank.retrieve_similar(strategy_family="economy")` filters
  by `strategy_label.startswith("economy.")` on all 4 retrieval paths
- `ExperienceBank.retrieve_pro_examples(strategy_family="setpiece")`
  same filtering on FAISS and brute-force paths
- Coach prompt includes strategy_label when retrieved experiences share one

## Adding a new label

Within an existing family: edit this file + open a PR. No migration.
The column accepts any string; the index supports filtering on it.

Adding a new family: requires
- a new entry in the table above with explicit description
- a code change in the retriever (intent → family mapping)
- a coach-prompt template update referencing the family

## Cross-references

- DB column: `coachingexperience.strategy_label`
- ORM: `Programma_CS2_RENAN/backend/storage/db_models.py:CoachingExperience`
- Miner: `tools/mine_shard_strategies.py`
- Retrieval: `Programma_CS2_RENAN/backend/knowledge/experience_bank.py`
- Plan: Phase 1 of Academic AI Infrastructure Audit
