"""
Generate the figures for the hand-in. Imports the model, runs it, and writes
PNGs under ./figures/.

Figures produced:
  1. npv_distribution.png   — histogram of per-draw NPV savings (uncertainty)
  2. npv_by_track.png       — mean NPV saving split by starting track
  3. tornado_sensitivity.png— one-way sensitivity (which assumption matters most)
  4. discount_schedule.png  — how the declining discount rate erodes far-future kr.
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")            # headless / file output only
import matplotlib.pyplot as plt

from early_retirement_savings_model import (
    Params, FP, RES, STATE_NAMES,
    generate_population, simulate, summarize,
    one_way_sensitivity, discount_factors,
)

FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")


def _kr(x: float) -> str:
    return f"{x/1000:,.0f}k"


def fig_npv_distribution(p: Params, res: dict, s: dict) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = res["saving_ensemble"]
    # clip the extreme tail for readability, keep the bulk
    lo, hi = np.percentile(data, [0.5, 99.5])
    ax.hist(np.clip(data, lo, hi), bins=60, color="#4C72B0", alpha=0.85)
    ax.axvline(0, color="grey", lw=1, ls=":")
    ax.axvline(s["mean_per_participant"], color="#C44E52", lw=2,
               label=f"mean {_kr(s['mean_per_participant'])} DKK")
    ax.axvline(s["median_per_participant"], color="#55A868", lw=2,
               label=f"median {_kr(s['median_per_participant'])} DKK")
    ax.set_title("Distribution of lifetime NPV saving per participant\n"
                 "(synthetic Monte-Carlo draws)")
    ax.set_xlabel("NPV saving, DKK")
    ax.set_ylabel("Monte-Carlo draws")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "npv_distribution.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_npv_by_track(p: Params, s: dict) -> str:
    fig, ax = plt.subplots(figsize=(6, 4.5))
    names = list(s["by_track"].keys())
    vals = [s["by_track"][k] for k in names]
    colors = ["#8172B3", "#CCB974"]
    bars = ax.bar(names, vals, color=colors[:len(names)])
    ax.axhline(0, color="grey", lw=1)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v,
                f"{_kr(v)}", ha="center",
                va="bottom" if v >= 0 else "top")
    ax.set_title("Mean NPV saving per participant, by starting track")
    ax.set_ylabel("NPV saving, DKK")
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "npv_by_track.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_tornado(p: Params, base_mean: float) -> str:
    sens = one_way_sensitivity(p)
    # order by total swing (impact)
    sens = sorted(sens, key=lambda r: abs(r[2] - r[1]))
    labels = [r[0] for r in sens]
    lows = np.array([r[1] for r in sens])
    highs = np.array([r[2] for r in sens])

    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(labels))
    for i in range(len(labels)):
        left, right = sorted((lows[i], highs[i]))
        ax.barh(y[i], right - left, left=left, color="#4C72B0", alpha=0.8)
    ax.axvline(base_mean, color="#C44E52", lw=2,
               label=f"base case {_kr(base_mean)} DKK")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Mean NPV saving per participant, DKK")
    ax.set_title("One-way sensitivity (tornado): which assumption moves the result")
    ax.legend(loc="lower right")
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "tornado_sensitivity.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_discount(p: Params) -> str:
    horizon = p.folkepension_age - p.age_min
    df = discount_factors(horizon, p)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(range(len(df)), df, color="#937860", lw=2)
    ax.set_title("Finansministeriet declining discount schedule\n"
                 "(value today of 1 DKK received in year t)")
    ax.set_xlabel("Years into the future")
    ax.set_ylabel("Discount factor")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "discount_schedule.png")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)
    p = Params()
    rng = np.random.default_rng(p.seed)
    pop = generate_population(p, rng)
    res = simulate(p, pop, rng)
    s = summarize(p, res)

    paths = [
        fig_npv_distribution(p, res, s),
        fig_npv_by_track(p, s),
        fig_tornado(p, s["mean_per_participant"]),
        fig_discount(p),
    ]
    print("Saved figures:")
    for pth in paths:
        print("  -", pth)


if __name__ == "__main__":
    main()
