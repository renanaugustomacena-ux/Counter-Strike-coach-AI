# Onboarding — New User Flow Management

> **Authority:** Rule 3 (Frontend & UX), Rule 4 (Data Persistence)

This module manages the new user onboarding workflow, tracking progression through the initial setup stages and gating access to coaching features based on data readiness.

## File Inventory

| File | Lines | Purpose | Key Classes |
|------|-------|---------|-------------|
| `new_user_flow.py` | ~135 | Onboarding stage management | `UserOnboardingManager`, `OnboardingStatus` |

## How It Works

The onboarding system tracks how many demos a user has ingested and maps that to readiness stages:

```
OnboardingStatus
├── stage: str          # Current onboarding stage name
├── demos_ingested: int # How many demos have been processed
├── readiness: float    # 0.0 to 1.0 coaching readiness score
└── can_coach: bool     # Whether coaching features are available
```

### Stages

Based on the "10/10 Rule" from user documentation:

1. **Setup** — No demos ingested yet. User needs to configure paths.
2. **Calibrating** — 1-49 demos. Coaching is available but confidence is low.
3. **Learning** — 50-199 demos. Coaching confidence is moderate.
4. **Mature** — 200+ demos. Full coaching capability with high confidence.

### Database Query

The manager queries `PlayerMatchStats` to count non-pro demos:
```python
SELECT COUNT(*) FROM PlayerMatchStats WHERE is_pro = False
```

## Integration

- **UI:** Connected to `HomeScreen` and `WizardScreen` to show readiness indicators
- **Coaching:** `CoachingService` checks readiness before generating high-confidence insights
- **Database:** Reads from `PlayerMatchStats` (read-only, no mutations)

## Development Notes

- `UserOnboardingManager` is stateless — recalculates stage on every call
- Stage thresholds should match `data/docs/getting_started.md` documentation
- Never gate features completely — always allow coaching, just with confidence warnings
- The `readiness` float is used for confidence scaling in `coaching/correction_engine.py`
