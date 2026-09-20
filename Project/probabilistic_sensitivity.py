"""
Probabilistic sensitivity analysis (PSA) for the fiscal-savings model.

Instead of varying one assumption at a time (the tornado in
early_retirement_savings_model.py), this samples ALL uncertain parameters
*jointly* from probability distributions, re-runs the microsimulation for each
draw, and produces a full uncertainty fan for the headline result.

Outputs:
  - data/psa_draws.csv              : every parameter draw + its cohort-mean saving
  - figures/psa_fan.png             : distribution of mean NPV saving / participant
  - figures/psa_prcc.png            : which inputs drive the output (rank correlation)
  - console summary                 : mean, 95% credible interval, P(saving > 0)

Distributions are chosen to bracket the literature-anchored point values used as
defaults in Params (see docs/methods.md §6 and the SOURCES block in the model).
"""

from __future__ import annotations

import os
from dataclasses import replace
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from early_retirement_savings_model import (
    Params, generate_population, simulate, summarize,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")

N_PSA = 800          # number of joint parameter draws
N_IND = 500          # synthetic individuals per draw (light, for speed)
N_MC = 60            # MC replications per individual per draw
MASTER_SEED = 2025


def _beta_from_mean(mean: float, conc: float = 40.0) -> tuple[float, float]:
    """Beta(a, b) with the given mean and concentration a+b (for probabilities)."""
    a = max(mean * conc, 1e-3)
    b = max((1.0 - mean) * conc, 1e-3)
    return a, b


def sample_params(rng: np.random.Generator) -> dict:
    """Draw one joint set of uncertain parameters around the model defaults.

    Returns a dict of the sampled values so they can be logged to CSV.
    """
    base = Params()

    def beta(mean, conc=40.0):
        a, b = _beta_from_mean(mean, conc)
        return float(rng.beta(a, b))

    # destination split via Dirichlet (keeps the three shares summing to 1)
    dest = rng.dirichlet(np.array([base.p_employment, base.p_fleksjob,
                                   base.p_other_benefit]) * 30.0)

    draw = {
        "share_permanent": beta(base.share_permanent, 30),
        "share_track_res": beta(base.share_track_res, 30),
        # FP exit: baseline and the treated arm (enforce treated >= baseline)
        "q0_per_review": beta(base.q0_per_review, 120),
        "q_fp_uplift": float(rng.uniform(0.005, 0.030)),   # additive Δq, treated-control
        # RES dynamics
        "q_res_work0": beta(base.q_res_work0, 60),
        "q_res_work_uplift": float(rng.uniform(0.01, 0.09)),
        "q_res_to_fp0": beta(base.q_res_to_fp0, 60),
        "q_res_to_fp_reduction": float(rng.uniform(0.0, 0.05)),  # prevention
        "res_expiry_to_fp": beta(base.res_expiry_to_fp, 20),
        "relapse_per_year": beta(base.relapse_per_year, 80),
        # destination split + costs
        "p_employment": float(dest[0]),
        "p_fleksjob": float(dest[1]),
        "p_other_benefit": float(dest[2]),
        "net_cost_employment": float(rng.normal(-70_000, 25_000)),
        "net_cost_fleksjob": float(rng.normal(120_000, 25_000)),
        "net_cost_other": float(rng.normal(150_000, 20_000)),
        "program_cost_per_participant": float(np.clip(
            rng.normal(10_000, 5_000), 1_000, None)),
        # structural / horizon
        "folkepension_age": int(rng.integers(67, 73)),
        "flat_discount": float(rng.uniform(0.02, 0.05)),
    }
    return draw


def params_from_draw(draw: dict) -> Params:
    """Map a sampled draw onto a Params instance for the simulation."""
    q1 = draw["q0_per_review"] + draw["q_fp_uplift"]
    q_res_work1 = draw["q_res_work0"] + draw["q_res_work_uplift"]
    q_res_to_fp1 = max(0.0, draw["q_res_to_fp0"] - draw["q_res_to_fp_reduction"])
    return Params(
        n_individuals=N_IND,
        mc_draws=N_MC,
        seed=MASTER_SEED,  # population seed fixed; uncertainty comes from params
        share_permanent=draw["share_permanent"],
        share_track_res=draw["share_track_res"],
        p_employment=draw["p_employment"],
        p_fleksjob=draw["p_fleksjob"],
        p_other_benefit=draw["p_other_benefit"],
        net_cost_employment=draw["net_cost_employment"],
        net_cost_fleksjob=draw["net_cost_fleksjob"],
        net_cost_other=draw["net_cost_other"],
        q0_per_review=draw["q0_per_review"],
        q1_per_review=q1,
        q_res_work0=draw["q_res_work0"],
        q_res_work1=q_res_work1,
        q_res_to_fp0=draw["q_res_to_fp0"],
        q_res_to_fp1=q_res_to_fp1,
        res_expiry_to_fp=draw["res_expiry_to_fp"],
        relapse_per_year=draw["relapse_per_year"],
        folkepension_age=draw["folkepension_age"],
        discount_schedule=((10_000, draw["flat_discount"]),),
        program_cost_per_participant=draw["program_cost_per_participant"],
    )


def run_psa() -> pd.DataFrame:
    rng = np.random.default_rng(MASTER_SEED)
    records = []
    for i in range(N_PSA):
        draw = sample_params(rng)
        p = params_from_draw(draw)
        sim_rng = np.random.default_rng(MASTER_SEED + i)  # vary MC noise per draw
        pop = generate_population(p, sim_rng)
        res = simulate(p, pop, sim_rng)
        s = summarize(p, res)
        draw["mean_saving"] = s["mean_per_participant"]
        records.append(draw)
        if (i + 1) % 100 == 0:
            print(f"  PSA draw {i + 1:>4}/{N_PSA} ...")
    return pd.DataFrame.from_records(records)


def fig_fan(df: pd.DataFrame) -> str:
    vals = df["mean_saving"].values
    lo, hi = np.percentile(vals, [2.5, 97.5])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(vals, bins=45, color="#4C72B0", alpha=0.85)
    ax.axvline(0, color="grey", lw=1, ls=":")
    ax.axvline(vals.mean(), color="#C44E52", lw=2,
               label=f"mean {vals.mean()/1000:,.0f}k")
    ax.axvspan(lo, hi, color="#55A868", alpha=0.15,
               label=f"95% CI [{lo/1000:,.0f}k, {hi/1000:,.0f}k]")
    ax.set_title("Probabilistic sensitivity: uncertainty fan for\n"
                 "mean NPV saving per participant (all parameters joint)")
    ax.set_xlabel("Cohort-mean NPV saving / participant, DKK")
    ax.set_ylabel("PSA draws")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "psa_fan.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_prcc(df: pd.DataFrame) -> str:
    """Partial-rank-correlation-style driver ranking (Spearman on ranks)."""
    y = df["mean_saving"]
    drivers = [c for c in df.columns if c != "mean_saving"]
    corr = {}
    for c in drivers:
        if df[c].nunique() > 1:
            corr[c] = stats.spearmanr(df[c], y).correlation
    order = sorted(corr, key=lambda k: abs(corr[k]))
    vals = [corr[k] for k in order]
    colors = ["#C44E52" if v < 0 else "#4C72B0" for v in vals]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(order, vals, color=colors)
    ax.axvline(0, color="grey", lw=1)
    ax.set_xlabel("Spearman rank correlation with mean saving")
    ax.set_title("PSA driver ranking: which uncertain inputs move the result")
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "psa_prcc.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    print(f"Running PSA: {N_PSA} joint draws "
          f"({N_IND} individuals x {N_MC} MC each) ...")
    df = run_psa()

    csv_path = os.path.join(DATA_DIR, "psa_draws.csv")
    df.to_csv(csv_path, index=False)

    vals = df["mean_saving"].values
    lo, hi = np.percentile(vals, [2.5, 97.5])
    print("\n" + "=" * 64)
    print(" PROBABILISTIC SENSITIVITY ANALYSIS — headline result")
    print("=" * 64)
    print(f" PSA draws.......................... {len(df):>12,}")
    print(f" Mean of mean-saving................ {vals.mean():>12,.0f} DKK")
    print(f" Median............................. {np.median(vals):>12,.0f} DKK")
    print(f" 95% credible interval.............. [{lo:,.0f} ; {hi:,.0f}] DKK")
    print(f" P(mean saving > 0)................. {(vals > 0).mean():>11.1%}")
    print("=" * 64)

    paths = [fig_fan(df), fig_prcc(df)]
    print("\nSaved:")
    print("  -", csv_path)
    for pth in paths:
        print("  -", pth)


if __name__ == "__main__":
    main()
