Factory models — what ships in the installer (WP4c, DOCTRINE D-32)

Everything in this folder matching *.pt and *.pt.meta.json is bundled by
packaging/cs2_analyzer_win.spec into _internal/Programma_CS2_RENAN/models/global/
and is what persistence.load_nn falls back to when the user has not trained a
model locally yet. Ship each checkpoint WITH its sidecar: load_nn refuses a .pt
without its .pt.meta.json.

The app's Train action writes the user's own models to
%LOCALAPPDATA%\MacenaCS2Analyzer\models\global\ (or the data folder chosen in
the setup wizard); those take precedence over the factory copies.

Expected for the current neural core (jepa_v2):
  jepa_v2_encoder.pt + jepa_v2_encoder.pt.meta.json   served encoder
  jepa_v2_full.pt    + jepa_v2_full.pt.meta.json      optional, lets Train resume

Legacy v1 checkpoints (jepa_brain, rap_coach, latest) are frozen (D-01) and
only used with ALLOW_LEGACY_NEURAL_TRAINING; leave them out of a release.

The build script warns when this folder holds no .pt file. This README keeps
the directory in git; the checkpoints themselves are gitignored.
