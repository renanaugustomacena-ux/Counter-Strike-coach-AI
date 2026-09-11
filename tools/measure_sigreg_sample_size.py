#!/usr/bin/env python3
"""Sample-size behaviour of the SIGReg / Epps-Pulley statistic used for TEMPORAL SIGReg.

Context: CORREZIONE_NUCLEO_NEURALE_PARTE_II.md §2.3.2 (Epps-Pulley, Teorema 4, Teorema 6,
implementazione le-wm) and §2.3.3 (SIGReg temporale: i T token di UNA finestra sono il campione,
LeNEPA eq. 2). The v2 plan uses T = 48 tokens per window (Parte I §7.5, Parte III §4.6/§4.7);
LeNEPA uses ~200 tokens per window. This script is a pure simulation (no database, no GPU):

  (a) mean/std of the statistic under H0 (z ~ N(0, I_d)) for N in N_GRID, d = 64, R repetitions
      with a fresh sample AND fresh directions each repetition;
  (b) the same under alternatives A1 (temporal collapse), A2 (AR(1) slow features, rho = 0.9),
      A3 (rank-8 subspace of R^64), A4 (Student-t, 3 dof, unit variance, i.i.d. per coordinate)
      plus an extra A4mv (multivariate-t: one scale per token, heavy tails in EVERY direction);
  (c) separation index (mean_alt - mean_H0) / std_H0;
  (d) gradient noise: for fixed samples z, gradient of the statistic wrt z under G direction seeds;
      relative std of the gradient norm and mean pairwise cosine between gradients;
  (e) Teorema 6 minibatch bias (1/n) * int w(t) (1 - |phi(t)|^2) dt evaluated with the exact
      quadrature of the implementation, compared with the measured H0 mean;
  (f) pooled variant: k concatenated windows of 48 tokens from independent AR(1) processes
      (k in 1, 2, 4) vs a single contiguous AR(1) window of 48k tokens vs H0 at 48k.

The statistic is a literal copy of lucas-maes/le-wm module.py (as in
tools/verify_math_claims.py::sigreg_epps_pulley): M = 1024 unit directions, 17 trapezoid knots
on [0, 3], Gaussian window exp(-t^2/2); the direction generator is seedable and batched.

Usage (repo root, CPU):
  CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/measure_sigreg_sample_size.py \
      --out docs/research/sigreg_sample_size_2026-09-05.json
  add --quick for a smoke run (R = 20, 5 gradient seeds).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
import numpy as np  # noqa: E402
import torch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

# --- fixed design constants (Parte I App. A.1, Parte III §4.2) -----------------------------------
D_PROJ = 64  # projector output dim (128 -> 256 -> 64)
NUM_PROJ = 1024  # M directions
KNOTS = 17
T_MAX = 3.0
N_GRID = [16, 32, 48, 64, 96, 128, 200, 256, 512]
WINDOW_T = 48  # tokens per window in the v2 plan
RHO_AR1 = 0.9
RANK_DEFICIENT = 8
STUDENT_DOF = 3
COLLAPSE_NOISE = 1e-3
POOL_K = [1, 2, 4]
ELEMENT_BUDGET = (
    40_000_000  # max elements of the (R, N, M) projection tensor per chunk (~160 MB fp32)
)
GRAD_SEED_CHUNK = 10  # direction seeds batched per autograd pass in (d)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}", flush=True)


# --- statistic ------------------------------------------------------------------------------------
def quadrature(
    knots: int = KNOTS, t_max: float = T_MAX
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Knots t_k, Gaussian CF phi(t_k) = exp(-t^2/2), trapezoid weights * window (le-wm module.py)."""
    t = torch.linspace(0, t_max, knots)
    dt = t_max / (knots - 1)
    weights = torch.full((knots,), 2 * dt)
    weights[[0, -1]] = dt
    phi = torch.exp(-t.square() / 2.0)
    return t, phi, weights * phi


def directions(seed: int, d: int = D_PROJ, m: int = NUM_PROJ) -> torch.Tensor:
    """Unit-norm columns, same call order as verify_math_claims.sigreg_epps_pulley (seedable)."""
    g = torch.Generator().manual_seed(seed)
    a = torch.randn(d, m, generator=g)
    return a / a.norm(p=2, dim=0, keepdim=True)


def directions_batch(seeds: List[int], d: int = D_PROJ, m: int = NUM_PROJ) -> torch.Tensor:
    return torch.stack([directions(s, d, m) for s in seeds])  # (S, D, M)


def ep_per_direction(z: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
    """Epps-Pulley statistic per direction. z: (..., N, D); a: (..., D, M) -> (..., M).

    Literal le-wm: x_t = (zA) (x) t; err_k = (mean cos - phi_k)^2 + (mean sin)^2; stat = N * sum_k w_k err_k.
    Evaluated knot by knot (same arithmetic, peak memory (..., N, M) instead of (..., N, M, K)).
    """
    t, phi, w = quadrature()
    p = z @ a  # (..., N, M)
    errs = []
    for k in range(KNOTS):
        x = p * t[k]
        errs.append((x.cos().mean(-2) - phi[k]).square() + x.sin().mean(-2).square())
    err = torch.stack(errs, -1)  # (..., M, K)
    return (err @ w) * z.size(-2)  # (..., M)


def ep_stat(z: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
    """Mean over the M directions -> (...,)."""
    return ep_per_direction(z, a).mean(-1)


def sigreg_reference(proj: torch.Tensor, seed: int = 0) -> float:
    """Single-sample path identical to verify_math_claims.sigreg_epps_pulley (parity check)."""
    return float(ep_stat(proj, directions(seed, proj.size(-1))))


def stats_batched(z: torch.Tensor, dir_seeds: List[int]) -> tuple[torch.Tensor, torch.Tensor]:
    """z: (R, N, D) with a fresh direction set per repetition. Returns (stat (R,), std over directions (R,))."""
    r, n, _ = z.shape
    chunk = max(1, min(r, ELEMENT_BUDGET // (n * NUM_PROJ)))
    out, dir_std = [], []
    for i in range(0, r, chunk):
        a = directions_batch(dir_seeds[i : i + chunk])
        per_dir = ep_per_direction(z[i : i + chunk], a)  # (rc, M)
        out.append(per_dir.mean(-1))
        dir_std.append(per_dir.std(-1))
    return torch.cat(out), torch.cat(dir_std)


# --- samplers (each returns (R, N, D), float32) -----------------------------------------------------
def sample_h0(r: int, n: int, d: int, g: torch.Generator) -> torch.Tensor:
    return torch.randn(r, n, d, generator=g)


def sample_a1_collapsed(r: int, n: int, d: int, g: torch.Generator) -> torch.Tensor:
    centre = torch.randn(r, 1, d, generator=g)  # each window collapses on its own point
    return centre + COLLAPSE_NOISE * torch.randn(r, n, d, generator=g)


def sample_a2_ar1(r: int, n: int, d: int, g: torch.Generator, rho: float = RHO_AR1) -> torch.Tensor:
    """Stationary AR(1) per coordinate, unit marginal variance: z_t = rho z_{t-1} + sqrt(1-rho^2) eps_t."""
    eps = torch.randn(r, n, d, generator=g)
    z = torch.empty(r, n, d)
    z[:, 0] = eps[:, 0]
    s = math.sqrt(1.0 - rho * rho)
    for t in range(1, n):
        z[:, t] = rho * z[:, t - 1] + s * eps[:, t]
    return z


def sample_a3_rank8(
    r: int, n: int, d: int, g: torch.Generator, k: int = RANK_DEFICIENT
) -> torch.Tensor:
    z = torch.zeros(r, n, d)
    z[..., :k] = torch.randn(r, n, k, generator=g)
    return z


def _chi2(shape: tuple[int, ...], dof: int, g: torch.Generator) -> torch.Tensor:
    return torch.randn(*shape, dof, generator=g).square().sum(-1)


def sample_a4_student_coord(
    r: int, n: int, d: int, g: torch.Generator, dof: int = STUDENT_DOF
) -> torch.Tensor:
    """i.i.d. Student-t(dof) per coordinate, scaled to unit variance: t/sqrt(dof/(dof-2)) = g/sqrt(chi2_dof)*sqrt(dof-2)."""
    gauss = torch.randn(r, n, d, generator=g)
    return gauss * math.sqrt(dof - 2) / _chi2((r, n, d), dof, g).sqrt()


def sample_a4_student_mv(
    r: int, n: int, d: int, g: torch.Generator, dof: int = STUDENT_DOF
) -> torch.Tensor:
    """Multivariate-t: one chi2 scale per token (shared across the d coordinates), unit variance."""
    gauss = torch.randn(r, n, d, generator=g)
    return gauss * math.sqrt(dof - 2) / _chi2((r, n, 1), dof, g).sqrt()


SAMPLERS: Dict[str, Callable[..., torch.Tensor]] = {
    "H0_gaussian": sample_h0,
    "A1_collapsed": sample_a1_collapsed,
    "A2_ar1_rho0.9": sample_a2_ar1,
    "A3_rank8": sample_a3_rank8,
    "A4_student3_coord": sample_a4_student_coord,
    "A4mv_student3_token": sample_a4_student_mv,
}


# --- theory -----------------------------------------------------------------------------------------
def c0_quadrature() -> float:
    """int w(t)(1 - phi(t)^2) dt with the implementation's quadrature = E[stat] under H0 for EVERY N."""
    _, phi, w = quadrature()
    return float((w * (1.0 - phi.square())).sum())


def c0_closed_form() -> float:
    """int_R exp(-t^2/2)(1 - exp(-t^2)) dt = sqrt(2 pi) - sqrt(2 pi / 3)."""
    return math.sqrt(2 * math.pi) - math.sqrt(2 * math.pi / 3)


def c0_truncated(t_max: float = T_MAX) -> float:
    from scipy.integrate import quad

    val, _ = quad(lambda t: math.exp(-t * t / 2) * (1 - math.exp(-t * t)), -t_max, t_max)
    return float(val)


def theory_mean_a1(n: int) -> float:
    """Point mass at m with m ~ N(0,1) over random directions: E cos(tm) = phi -> E[stat] = N * c0."""
    return n * c0_quadrature()


def theory_mean_a2(n: int, rho: float = RHO_AR1) -> float:
    """Gaussian AR(1), unit marginal: E|phi_hat - psi|^2 = (1/N^2) sum_{j,l} (e^{-t^2(1-rho^{|j-l|})} - e^{-t^2})."""
    t, _, w = quadrature()
    idx = torch.arange(n)
    lag = (idx[:, None] - idx[None, :]).abs().float()
    corr = rho**lag  # (N, N)
    total = torch.zeros(KNOTS)
    for k in range(KNOTS):
        tk2 = float(t[k]) ** 2
        total[k] = (torch.exp(-tk2 * (1.0 - corr)) - math.exp(-tk2)).sum() / n
    return float((w * total).sum())


def theory_mean_a3(
    n: int, k: int = RANK_DEFICIENT, d: int = D_PROJ, mc: int = 200_000, seed: int = 123
) -> float:
    """Projection variance s^2 = |a_{1:k}|^2 ~ Beta(k/2, (d-k)/2); phi_P = exp(-s^2 t^2/2); average over s^2."""
    g = torch.Generator().manual_seed(seed)
    a = torch.randn(mc, d, generator=g)
    s2 = a[:, :k].square().sum(-1) / a.square().sum(-1)  # (mc,)
    t, phi, w = quadrature()
    phi_p = torch.exp(-0.5 * s2[:, None] * t[None, :].square())  # (mc, K)
    term1 = n * (w * (phi_p - phi).square()).sum(-1)
    term2 = (w * (1.0 - phi_p.square())).sum(-1)
    return float((term1 + term2).mean())


# --- measurements -------------------------------------------------------------------------------------
def summarize(x: torch.Tensor) -> dict:
    xn = x.double()
    q = torch.quantile(xn, torch.tensor([0.05, 0.5, 0.95], dtype=torch.float64))
    return {
        "mean": float(xn.mean()),
        "std": float(xn.std(unbiased=True)),
        "min": float(xn.min()),
        "max": float(xn.max()),
        "q05": float(q[0]),
        "median": float(q[1]),
        "q95": float(q[2]),
        "n_rep": int(x.numel()),
    }


def measure_distributions(reps: int, seed: int) -> dict:
    """(a)(b)(c): per N, per distribution: summary of the statistic over R repetitions."""
    out: Dict[str, dict] = {}
    for n in N_GRID:
        out[str(n)] = {}
        raw: Dict[str, torch.Tensor] = {}
        t0 = time.time()
        for j, (name, sampler) in enumerate(SAMPLERS.items()):
            g = torch.Generator().manual_seed(seed * 7919 + n * 131 + j)
            z = sampler(reps, n, D_PROJ, g)
            dir_seeds = [seed * 1_000_003 + n * 10_007 + j * 100_003 + r for r in range(reps)]
            stat, dir_std = stats_batched(z, dir_seeds)
            raw[name] = stat
            s = summarize(stat)
            s["std_over_directions_within_sample_mean"] = float(dir_std.mean())
            out[str(n)][name] = s
        h0 = out[str(n)]["H0_gaussian"]
        for name in SAMPLERS:
            if name == "H0_gaussian":
                continue
            alt = out[str(n)][name]
            alt["separation_index"] = (alt["mean"] - h0["mean"]) / h0["std"]
            # one-sided empirical power at alpha = 5%: fraction of alternative draws above the H0 95th percentile
            # (alternative draws and directions are independent of the H0 draws that define the threshold)
            alt["power_at_alpha05"] = float((raw[name] > h0["q95"]).double().mean())
            alt["separation_index_alt_std"] = (alt["mean"] - h0["mean"]) / max(alt["std"], 1e-12)
        _log(
            f"N={n:4d}  H0 mean={h0['mean']:.4f} std={h0['std']:.4f}  "
            f"A1={out[str(n)]['A1_collapsed']['mean']:.1f}  A2={out[str(n)]['A2_ar1_rho0.9']['mean']:.3f}  "
            f"A3={out[str(n)]['A3_rank8']['mean']:.2f}  A4={out[str(n)]['A4_student3_coord']['mean']:.4f}  "
            f"A4mv={out[str(n)]['A4mv_student3_token']['mean']:.4f}  ({time.time() - t0:.1f}s)"
        )
    return out


def gradient_noise(
    n: int, n_fixed: int, n_seeds: int, seed: int, sampler: Callable[..., torch.Tensor]
) -> dict:
    """(d): fixed sample z (N, D); gradient of the M-averaged statistic wrt z under n_seeds direction seeds."""
    per_sample = []
    for f in range(n_fixed):
        g = torch.Generator().manual_seed(seed * 31 + n * 7 + f)
        z0 = sampler(1, n, D_PROJ, g)[0]
        grads = []
        stat_last = 0.0
        for s0 in range(0, n_seeds, GRAD_SEED_CHUNK):
            seeds = [
                seed * 500_009 + f * 1009 + s for s in range(s0, min(n_seeds, s0 + GRAD_SEED_CHUNK))
            ]
            # one copy of z per seed: stat_s depends only on copy s, so d(sum_s stat_s)/d z_s = d stat_s / d z
            z = z0.unsqueeze(0).repeat(len(seeds), 1, 1).requires_grad_(True)
            stat = ep_stat(z, directions_batch(seeds))  # (S,)
            (grad,) = torch.autograd.grad(stat.sum(), z)
            grads.append(grad.reshape(len(seeds), -1))
            stat_last = float(stat[-1].detach())
        gm = torch.cat(grads).double()  # (S, N*D)
        norms = gm.norm(dim=1)
        unit = gm / norms[:, None]
        cos = unit @ unit.T
        off = cos[~torch.eye(n_seeds, dtype=torch.bool)]
        mean_dir = gm.mean(0)
        per_sample.append(
            {
                "grad_norm_mean": float(norms.mean()),
                "grad_norm_rel_std": float(norms.std(unbiased=True) / norms.mean()),
                "mean_pairwise_cosine": float(off.mean()),
                "cosine_to_seed_average": float((unit @ (mean_dir / mean_dir.norm())).mean()),
                "per_token_grad_norm_mean": float(gm.view(n_seeds, n, D_PROJ).norm(dim=2).mean()),
                "max_abs_grad_entry": float(gm.abs().max()),
                "stat_value": stat_last,
            }
        )
    agg = {k: float(np.mean([p[k] for p in per_sample])) for k in per_sample[0]}
    agg["per_fixed_sample"] = per_sample
    agg["n_fixed_samples"] = n_fixed
    agg["n_direction_seeds"] = n_seeds
    return agg


def measure_gradients(n_fixed: int, n_seeds: int, seed: int) -> dict:
    out: Dict[str, dict] = {}
    for dist_name in ("H0_gaussian", "A2_ar1_rho0.9", "A3_rank8"):
        out[dist_name] = {}
        fixed = (
            n_fixed if dist_name == "H0_gaussian" else 1
        )  # alternatives are an extra: one fixed sample
        for n in N_GRID:
            t0 = time.time()
            r = gradient_noise(n, fixed, n_seeds, seed, SAMPLERS[dist_name])
            out[dist_name][str(n)] = r
            _log(
                f"grad {dist_name:20s} N={n:4d}  |g|={r['grad_norm_mean']:.4f} rel_std={r['grad_norm_rel_std']:.4f} "
                f"cos={r['mean_pairwise_cosine']:.4f}  ({time.time() - t0:.1f}s)"
            )
    return out


def measure_bias(dist: dict) -> dict:
    """(e): Teorema 6. stat = N * L_hat_N; E[stat|H0] = c0 for all N; bias of L_hat_N = c0 / N."""
    c0 = c0_quadrature()
    rows = {}
    for n in N_GRID:
        h0 = dist[str(n)]["H0_gaussian"]
        mc_se = h0["std"] / math.sqrt(h0["n_rep"])
        rows[str(n)] = {
            "theorem6_bias_of_unscaled_loss": c0 / n,
            "measured_unscaled_loss_mean": h0["mean"] / n,
            "measured_stat_mean_minus_c0": h0["mean"] - c0,
            "monte_carlo_se_of_stat_mean": mc_se,
            "z_score_vs_c0": (h0["mean"] - c0) / mc_se,
        }
    return {
        "c0_quadrature_17_knots_0_3": c0,
        "c0_closed_form_R": c0_closed_form(),
        "c0_truncated_minus3_3": c0_truncated(),
        "note": "stat = N * L_hat_N (le-wm multiplies by N). Under H0 E[stat] = c0 exactly for every N; "
        "the O(1/n) bias of Teorema 6 applies to the unscaled loss L_hat_N = stat / N whose "
        "population value under H0 is 0.",
        "per_N": rows,
    }


def measure_theory(dist: dict) -> dict:
    rows = {}
    for n in N_GRID:
        rows[str(n)] = {
            "A1_collapsed": {
                "theory": theory_mean_a1(n),
                "measured": dist[str(n)]["A1_collapsed"]["mean"],
            },
            "A2_ar1_rho0.9": {
                "theory": theory_mean_a2(n),
                "measured": dist[str(n)]["A2_ar1_rho0.9"]["mean"],
            },
            "A3_rank8": {"theory": theory_mean_a3(n), "measured": dist[str(n)]["A3_rank8"]["mean"]},
        }
        for v in rows[str(n)].values():
            v["rel_err"] = (v["measured"] - v["theory"]) / v["theory"]
    return rows


def measure_pooled(reps: int, seed: int) -> dict:
    """(f): k concatenated independent AR(1) windows of 48 tokens vs one contiguous AR(1) window of 48k vs H0."""
    out = {}
    for j, k in enumerate(POOL_K):
        n_tot = WINDOW_T * k
        g = torch.Generator().manual_seed(seed * 811 + j)
        # pooled: k independent windows of 48 tokens, concatenated along the sample axis
        windows = sample_a2_ar1(reps * k, WINDOW_T, D_PROJ, g).view(reps, k, WINDOW_T, D_PROJ)
        pooled = windows.reshape(reps, n_tot, D_PROJ)
        # contiguous: a single AR(1) run of 48k tokens
        contiguous = sample_a2_ar1(reps, n_tot, D_PROJ, g)
        # H0 at 48k
        h0 = sample_h0(reps, n_tot, D_PROJ, g)
        base = seed * 3_000_017 + j * 300_007
        s_pool, _ = stats_batched(pooled, [base + r for r in range(reps)])
        s_cont, _ = stats_batched(contiguous, [base + 10_000 + r for r in range(reps)])
        s_h0, _ = stats_batched(h0, [base + 20_000 + r for r in range(reps)])
        # per-window statistics of the same k windows (what the LeNEPA loss averages over the batch)
        flat = windows.reshape(reps * k, WINDOW_T, D_PROJ)
        s_win, _ = stats_batched(flat, [base + 30_000 + r for r in range(reps * k)])
        s_win_avg = s_win.view(reps, k).mean(1)
        h0_win = sample_h0(reps * k, WINDOW_T, D_PROJ, g)
        s_h0_win, _ = stats_batched(h0_win, [base + 40_000 + r for r in range(reps * k)])
        s_h0_win_avg = s_h0_win.view(reps, k).mean(1)
        sp, sc, sh = summarize(s_pool), summarize(s_cont), summarize(s_h0)
        sw, shw = summarize(s_win_avg), summarize(s_h0_win_avg)
        out[str(k)] = {
            "n_tokens_total": n_tot,
            "pooled_k_windows": sp,
            "contiguous_single_window": sc,
            "H0_same_N": sh,
            "per_window_stats_averaged_over_k": sw,
            "H0_per_window_averaged_over_k": shw,
            "separation_pooled": (sp["mean"] - sh["mean"]) / sh["std"],
            "separation_contiguous": (sc["mean"] - sh["mean"]) / sh["std"],
            "separation_per_window_average": (sw["mean"] - shw["mean"]) / shw["std"],
            "theory_mean_pooled": theory_mean_a2(WINDOW_T),
            "theory_mean_contiguous": theory_mean_a2(n_tot),
        }
        _log(
            f"pooled k={k} (N={n_tot}): pooled {sp['mean']:.3f}±{sp['std']:.3f} sep={out[str(k)]['separation_pooled']:.2f} | "
            f"contiguous {sc['mean']:.3f}±{sc['std']:.3f} sep={out[str(k)]['separation_contiguous']:.2f} | "
            f"per-window avg sep={out[str(k)]['separation_per_window_average']:.2f} | H0 {sh['mean']:.3f}±{sh['std']:.3f}"
        )
    return out


def parity_check() -> dict:
    """Compare the batched reimplementation with tools/verify_math_claims.py::sigreg_epps_pulley."""
    z = torch.randn(48, D_PROJ, generator=torch.Generator().manual_seed(7))
    mine = sigreg_reference(z, seed=3)
    result = {"this_script": mine}
    try:
        sys.path.insert(0, str(REPO))
        from tools.verify_math_claims import (  # loads torch + JEPA modules, no main()
            sigreg_epps_pulley,
        )

        ref = sigreg_epps_pulley(z, num_proj=NUM_PROJ, knots=KNOTS, t_max=T_MAX, seed=3)
        result.update(
            {
                "verify_math_claims": ref,
                "rel_diff": abs(mine - ref) / max(abs(ref), 1e-12),
                "ok": abs(mine - ref) / max(abs(ref), 1e-12) < 1e-5,
            }
        )
    except (
        Exception
    ) as exc:  # noqa: BLE001 - parity is informative; the simulation does not depend on it
        result.update({"verify_math_claims": None, "error": repr(exc), "ok": False})
    # batched path == single path for the same seed
    zb = torch.stack([z, z * 0.5])
    batched = stats_batched(zb, [3, 3])[0]
    result["batched_equals_single"] = bool(
        abs(float(batched[0]) - mine) < 1e-4 * max(1.0, abs(mine))
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default=str(REPO / "docs/research/sigreg_sample_size_2026-09-05.json"))
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--grad-seeds", type=int, default=50)
    ap.add_argument("--grad-fixed-samples", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--threads",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="keep small: OpenMP barriers collapse under oversubscription when siblings run",
    )
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.reps, args.grad_seeds, args.grad_fixed_samples = 20, 5, 1

    t_start = time.time()
    parity = parity_check()
    torch.set_num_threads(args.threads)  # verify_math_claims caps threads at 8 on import; restore
    torch.manual_seed(args.seed)
    _log(f"parity: {parity}")
    _log(
        f"config: d={D_PROJ} M={NUM_PROJ} knots={KNOTS} t_max={T_MAX} N_GRID={N_GRID} reps={args.reps} "
        f"grad_seeds={args.grad_seeds} threads={torch.get_num_threads()}"
    )

    _log("(a)(b)(c) distributions")
    dist = measure_distributions(args.reps, args.seed)
    _log("(e) Teorema 6 bias")
    bias = measure_bias(dist)
    _log(
        f"c0 quadrature={bias['c0_quadrature_17_knots_0_3']:.5f} closed-form={bias['c0_closed_form_R']:.5f} "
        f"truncated[-3,3]={bias['c0_truncated_minus3_3']:.5f}"
    )
    theory = measure_theory(dist)
    _log("(d) gradient noise")
    grads = measure_gradients(args.grad_fixed_samples, args.grad_seeds, args.seed)
    _log("(f) pooled windows")
    pooled = measure_pooled(args.reps, args.seed)

    runtime = time.time() - t_start
    result = {
        "meta": {
            "date": "2026-09-05",
            "script": "tools/measure_sigreg_sample_size.py",
            "statistic": "Epps-Pulley SIGReg, le-wm module.py (M=1024 unit directions, 17 trapezoid knots on [0,3], window exp(-t^2/2), x N)",
            "d": D_PROJ,
            "M": NUM_PROJ,
            "knots": KNOTS,
            "t_max": T_MAX,
            "N_grid": N_GRID,
            "reps": args.reps,
            "grad_seeds": args.grad_seeds,
            "grad_fixed_samples": args.grad_fixed_samples,
            "seed": args.seed,
            "window_T": WINDOW_T,
            "rho_ar1": RHO_AR1,
            "rank_deficient": RANK_DEFICIENT,
            "student_dof": STUDENT_DOF,
            "collapse_noise": COLLAPSE_NOISE,
            "pool_k": POOL_K,
            "torch": torch.__version__,
            "numpy": np.__version__,
            "threads": torch.get_num_threads(),
            "runtime_seconds": runtime,
            "quick": args.quick,
            "alternatives": {
                "A1_collapsed": "z_t = c + 1e-3 eps_t, c ~ N(0,I_d) per window (temporal collapse on a point)",
                "A2_ar1_rho0.9": "z_t = 0.9 z_{t-1} + sqrt(1-0.81) eps_t per coordinate, stationary, unit marginal variance",
                "A3_rank8": "z_t = (g_t in R^8, 0 in R^56), g ~ N(0, I_8)",
                "A4_student3_coord": "i.i.d. Student-t(3)/sqrt(3) per coordinate (unit variance)",
                "A4mv_student3_token": "extra: multivariate-t(3): g_t * sqrt(dof-2) / sqrt(chi2_dof) with ONE chi2 per token shared across d, unit variance",
            },
        },
        "parity": parity,
        "distributions": dist,
        "theorem6_bias": bias,
        "theory_vs_measured_means": theory,
        "gradient_noise": grads,
        "pooled_windows": pooled,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    _log(f"wrote {out}  ({runtime:.1f}s)")

    print("\nSUMMARY (d=64, M=1024, 17 knots on [0,3])")
    print(
        f"{'N':>5} {'H0 mean':>8} {'H0 std':>7} | {'sep A1':>9} {'sep A2':>8} {'sep A3':>8} {'sep A4':>7} {'sep A4mv':>8} | "
        f"{'|g|':>7} {'relstd':>7} {'cos':>6}"
    )
    for n in N_GRID:
        h0 = dist[str(n)]["H0_gaussian"]
        gr = grads["H0_gaussian"][str(n)]
        print(
            f"{n:>5} {h0['mean']:>8.4f} {h0['std']:>7.4f} | "
            f"{dist[str(n)]['A1_collapsed']['separation_index']:>9.1f} "
            f"{dist[str(n)]['A2_ar1_rho0.9']['separation_index']:>8.2f} "
            f"{dist[str(n)]['A3_rank8']['separation_index']:>8.2f} "
            f"{dist[str(n)]['A4_student3_coord']['separation_index']:>7.2f} "
            f"{dist[str(n)]['A4mv_student3_token']['separation_index']:>8.2f} | "
            f"{gr['grad_norm_mean']:>7.4f} {gr['grad_norm_rel_std']:>7.4f} {gr['mean_pairwise_cosine']:>6.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
