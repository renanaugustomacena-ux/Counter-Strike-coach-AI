# Strategy Taxonomy — `coachingexperience.strategy_label`

GAP-09 (plan §4 Phase D, AUDIT §10). Closed taxonomy of tactical strategies
used to label `CoachingExperience` rows for retrieval-by-playbook coaching.
The label is nullable: legacy rows stay `NULL` until a backfill / classifier
job assigns them. New mining jobs (`backend/knowledge/pro_demo_miner.py`)
should populate it at insertion time.

Filtering this column is a hot retrieval path — the migration
`c3d4e5f6a7b8_add_strategy_label_to_coachingexperience` indexes it.

## Label format

`{family}.{strategy}` — lowercase, dot-separated. Two-level only. The
family is one of the five fixed buckets below. Adding a new family is a
schema change (the RAG retriever and the coach LLM prompt both inspect
families); adding a new strategy under an existing family is just a label.

## Families

### `setpiece` — site-execute set-pieces (T-side bomb-plant routines)
Predefined utility + entry sequences for taking a bomb-site. Typically
~25 seconds of coordinated smokes/molotovs/flashes followed by a forced
entry. RAP coach surfaces these by pro_player_name when the user's team
economy + side + map match.

| Label | Map(s) | Description |
|---|---|---|
| `setpiece.a_default_execute` | any | Standard A-site take with smoke + molly + flash on default angles |
| `setpiece.b_default_execute` | any | Same for B-site |
| `setpiece.a_split` | any | Two-pronged A-site take from main + ramp/connector |
| `setpiece.b_split` | any | Two-pronged B-site take |
| `setpiece.fast_execute` | any | Sub-12s burst with minimal utility (econ-conservative) |
| `setpiece.slow_default` | any | 25–35 s setup with maximum utility |
| `setpiece.contact_play` | any | No-utility close-range entry |
| `setpiece.fake_a_take_b` | any | Utility/sound feint on opposite site |
| `setpiece.fake_b_take_a` | any | Same, reversed |
| `setpiece.mid_to_a` | any | Mid-control conversion to A |
| `setpiece.mid_to_b` | any | Mid-control conversion to B |

### `economy` — round-economy decisions
Buy-shape strategies tied to team_economy / round_phase / score state.
Selected per round, not per moment. Maps to PlayerTickState.team_economy.

| Label | Description |
|---|---|
| `economy.full_buy` | Full kit + utility |
| `economy.full_save` | Pistol/knife only, preserve next round |
| `economy.eco_with_pistol` | Save kit, equip armor + utility on a pistol |
| `economy.force_buy` | Sub-optimal kit to deny opponent reset |
| `economy.semi_buy` | Mixed-kit hybrid (some rifles, some pistols) |
| `economy.anti_eco_setup` | CT positioning specifically vs an enemy eco |
| `economy.gun_round_loss_save` | Drop kit on losing gun round to preserve next |
| `economy.bonus_money_force` | Use loss-bonus surplus to break opponent eco |

### `rotation` — mid-round repositioning
Decisions about leaving a current position to reinforce another. Tied to
bomb_planted state, alive counts, and tick-level positional aggression.

| Label | Description |
|---|---|
| `rotation.solo_to_bomb` | Single CT cross-map rotation to defuse |
| `rotation.stack_a` | Pre-round CT stack on A |
| `rotation.stack_b` | Pre-round CT stack on B |
| `rotation.late_rotation` | Reactive rotation after enemy commit confirmed |
| `rotation.fake_rotation` | Sound-bait rotation to draw enemy commit |
| `rotation.retake_default` | Standard 4-way CT retake post-plant |
| `rotation.retake_split` | Two-direction simultaneous retake |
| `rotation.contact_retake` | No-utility rush retake (low time on bomb) |

### `playbook` — map-specific named plays
Named plays from the pro scene that bind a specific utility lineup to a
specific map area. Always includes `map_name` filter at retrieval.

| Label | Map | Description |
|---|---|---|
| `playbook.mirage_apartments_smoke` | de_mirage | Apps fast-take with apps smoke + jungle flash |
| `playbook.mirage_a_split_palace` | de_mirage | A-take with palace + ramp split |
| `playbook.inferno_banana_takeover` | de_inferno | T-side banana control with coffin + dark smokes |
| `playbook.inferno_a_apps_take` | de_inferno | A-take through apartments + balcony |
| `playbook.dust2_a_long_take` | de_dust2 | Long-A push with cross + xbox smoke |
| `playbook.dust2_b_tunnels_take` | de_dust2 | B-tunnels burst with mid-doors smoke |
| `playbook.nuke_outside_take` | de_nuke | T outside control with secret + heaven utility |
| `playbook.nuke_lower_take` | de_nuke | T lower-tunnel push |
| `playbook.overpass_b_short_take` | de_overpass | B short-stairs take with monster smoke |
| `playbook.overpass_a_short_long` | de_overpass | A long + short coordinated take |
| `playbook.anubis_b_canal_take` | de_anubis | B canal control with main + water utility |
| `playbook.ancient_a_main_take` | de_ancient | Main-A take with default smoke wall |
| `playbook.train_a_main_take` | de_train | A-main rush with bomb-train smokes |

### `individual` — per-player tactical micro
Single-player decisions that don't involve team coordination. Used by the
coach to label "skill axes" in player feedback.

| Label | Description |
|---|---|
| `individual.held_angle` | Pre-aiming a specific angle from a static position |
| `individual.peek_jiggle` | Quick-peek to gather information without committing |
| `individual.lurk` | Solo flank away from main team push |
| `individual.entry_frag` | First-contact aggressive entry |
| `individual.support_trade` | Positioned to trade-kill teammate's death |
| `individual.utility_lineup` | Solo lineup throw (smoke / molly / he) from a memorized spot |
| `individual.awp_hold` | Static long-range hold with AWP |
| `individual.awp_aggressive_peek` | Aggressive AWP peek away from team |
| `individual.clutch_1v1` | Solo 1v1 clutch attempt |
| `individual.clutch_1v2` | Solo 1v2 clutch attempt |
| `individual.clutch_1v3plus` | Solo clutch vs 3+ enemies |
| `individual.fake_defuse` | CT defuse-bait while teammates retake |

## Backfill plan (post-retrain, deferred)

1. Pro-demo miner classifier: heuristic + Hopfield-prototype distance to
   assign labels at insertion.
2. RAG retrieval: filter by `strategy_label IN (...)` when the user's
   query maps to a recognized family (intent classifier outputs the
   family; labels at retrieval time are an OR within the family).
3. Coach prompt: when retrieved experiences share a label, the LLM is
   told the label name as part of the system prompt context block —
   tightens narrative coherence in tutor-mode responses.

## Adding a new label

Within an existing family: edit this file + open a PR. No migration.
The column accepts any string; the index supports filtering on it.

Adding a new family: requires
- a new entry in the table above with explicit description
- a code change in the retriever (intent → family mapping)
- a coach-prompt template update referencing the family

## Cross-references

- DB column: `coachingexperience.strategy_label`
- Migration: `alembic/versions/c3d4e5f6a7b8_add_strategy_label_to_coachingexperience.py`
- ORM: `Programma_CS2_RENAN/backend/storage/db_models.py:CoachingExperience`
- Plan §4 Phase D step 9 / GAP-09 in `~/.claude/plans/hello-my-brother-can-twinkly-stream.md`
- AUDIT §10.2 / §10.3
