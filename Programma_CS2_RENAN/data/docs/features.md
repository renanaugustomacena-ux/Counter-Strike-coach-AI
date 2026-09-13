# Feature Guide

## Dashboard

The status strip shows **Coach** (idle or analyzing), **Service** (the background Session Engine — *Online* while its heartbeat is fresh, *Offline* otherwise) and **Matches** (your analyzed demos). Below it: your last match with a rating sparkline, the focus card, the recent-matches strip, the **Demo Analysis** and **Pro Demo Ingestion** cards with their folder pickers and Analyze buttons, Connectivity shortcuts (Profile, Steam Config, FaceIt Config), the Tactical Analysis shortcuts and the **Training Status** card: the **Train coach** action with its step presets, a **Stop** button while a run is in progress, the active model trained on this machine (or "No model trained on this machine yet"), and the live step progress, losses and ETA of the current run.

## AI Coach

**Belief State Confidence** with its drivers (the sample count is your analyzed demos), **Recent Insights** (your own coaching insights, ranked by severity, top three first) and the chat dock. Chat answers come from a local Ollama model (default `gemma4:e2b`) that receives your analytics and the pro library as context and is instructed never to describe other players' numbers as yours.

## Match History

Every analyzed match. The header caption separates *N personal · M pro reference*; each row carries rating, K/D, ADR, KAST and headshot percentage. Opening a row goes to Match Detail.

## Match Detail

Four tabs: **Overview** (hero tiles, round strip, HLTV 2.0 components, kill enrichment, utility per round), **Rounds**, **Economy** and **Highlights**. A pro match you did not play in is titled *Pro demo · player — not you* and shows that player's rows.

## Advanced Analytics

Your averages (rating, matches, K/D, ADR, KAST), your percentile rank against the pro cohort, the rating trend, strengths and weaknesses versus the pro average, per-map tiles and utility effectiveness. With no personal demos it shows an empty state plus a *Pro reference* block that averages other players' matches — reference material, not your performance.

## Tactical Analyzer

A 2D replay of a demo: players, utility, the bomb, round scrubbing and critical moments. Ghost overlays from a trained model appear only when that model is enabled in the settings.

## Pro Comparison

Compare two pro players' stat cards from the HLTV metadata; the Details button opens the pro player page.

## Settings

**Appearance** (theme, font, wallpaper), **Analysis & Paths** (demo folder, pro demo folder, ingestion mode, Start Ingestion) and **Language** (English, Italiano, Português).
