"""
Synthetic fiscal-savings model for young Danes on labour-market disability
support, age 18-30, in the context of Social Sundhed's "Social Brobygger"
(social bridge-building) initiative.

TWO TRACKS ARE MODELLED
-----------------------
  FP  = førtidspension   (permanent disability pension)
  RES = ressourceforløb  (time-limited "resource clarification" course that
        under-40s normally pass through *before* FP can be granted)

The RES track matters because the single most expensive event for this age
group is *progression into FP*: a 25-year-old who lands on permanent FP can
draw benefits for ~45 years. An initiative that keeps a RES participant from
progressing into FP — or moves them into work/fleksjob — therefore avoids a
very long discounted expenditure stream. The model values exactly that.

WHAT THIS DOES
--------------
Builds a *synthetic* cohort spanning both tracks and runs a Monte-Carlo
microsimulation that estimates the present value (NPV) of public expenditure
AVOIDED if the initiative (a) raises the probability of exiting FP at the
mandatory 3-yearly re-evaluation, (b) raises the probability that a RES
participant exits to work/fleksjob, and (c) lowers the probability that a RES
participant progresses into FP.

The framing mirrors the mink-compensation logic referenced by the user: just as
the state valued the *present value of lost future revenue streams* for mink
farmers (~DKK 29.2 bn, FVM Jan-2025), here we value the *present value of
avoided future expenditure streams* (benefits no longer paid, plus tax revenue
gained) net of the programme's own cost.

IMPORTANT: transparent decision-support / advocacy model on SYNTHETIC data.
Every figure tagged [ASSUMPTION] or [NEEDS EVIDENCE] must be replaced with a
register- or literature-based estimate before any claim is made. The model's
purpose is to make those assumptions explicit and to show how sensitive the
headline saving is to each of them. See docs/methods.md and
docs/data_dictionary.md.

Author: (your name)
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np


# ---------------------------------------------------------------------------
# 1. PARAMETERS  (single source of truth — change these, not the code)
# ---------------------------------------------------------------------------
@dataclass
class Params:
    # --- population ---------------------------------------------------------
    n_individuals: int = 1500          # size of synthetic cohort
    mc_draws: int = 200                # Monte-Carlo replications per individual
    seed: int = 42
    age_min: int = 18
    age_max: int = 30
    share_single: float = 0.55         # [ASSUMPTION] single vs cohabiting -> benefit level
    share_track_res: float = 0.50      # [ASSUMPTION] fraction starting in ressourceforløb

    # Fraction of the FP subgroup whose work capacity is effectively permanent
    # (severe/developmental cases). Post-2013 reform, permanent FP for under-40s
    # is only granted when capacity "obviously" cannot develop, so most young
    # grants are genuinely permanent and have ~0 exit probability. Anchored to
    # the fact that revocations (frakendelser) are a very small share of the
    # young FP stock. [LIT: Reform 2013; STAR/DST frakendelse statistics] (S1)
    share_permanent: float = 0.55      # was 0.45; raised to reflect rare revocation

    # --- benefit levels (annual gross transfer, DKK, 2024-ish) --------------
    benefit_fp_single: float = 245_000     # [ASSUMPTION] FP, enlig (~20.4k kr/md)
    benefit_fp_cohab: float = 208_000      # [ASSUMPTION] FP, samlevende/gift
    benefit_res_single: float = 145_000    # [ASSUMPTION] ressourceforløbsydelse, enlig
    benefit_res_cohab: float = 110_000     # [ASSUMPTION] ressourceforløbsydelse, samlevende
    tax_back_fp: float = 0.38              # [ASSUMPTION] effective tax clawed back on FP
    tax_back_res: float = 0.30             # [ASSUMPTION] effective tax clawed back on RES

    # --- post-exit destinations & their NET annual public cost (DKK) --------
    # Realistic Danish exit pattern: among people who leave FP/RES, fleksjob (not
    # ordinary unsupported employment) is the dominant destination, ordinary jobs
    # are a minority, and a real share lands on other benefits. [LIT: STAR/
    # jobindsats ressourceforløb result statistics] (S2)
    p_employment: float = 0.20         # share of exits -> ordinary (unsupported) job (S2)
    p_fleksjob: float = 0.45           # share -> fleksjob / partial capacity (S2)
    p_other_benefit: float = 0.35      # share -> other benefit (S2)
    net_cost_employment: float = -70_000   # NEGATIVE = state RECEIVES net tax (often part-time) [ASSUMPTION]
    net_cost_fleksjob: float = 120_000     # fleksløntilskud net of tax/earnings [ASSUMPTION]
    net_cost_other: float = 150_000        # other benefit (kontanthjælp-like) [ASSUMPTION]

    # --- FP transition probabilities ---------------------------------------
    review_interval: int = 3           # mandatory FP re-evaluation cadence (years)
    # Revocation of an awarded FP is rare even at the mandatory review; only a
    # small fraction of the responsive subgroup actually exits. Baseline ~1.5%
    # per review is consistent with the very low frakendelse counts; the
    # initiative roughly doubles it (still small in absolute terms), in line with
    # the lower-to-mid range of IPS employment effects. (S1, S3)
    q0_per_review: float = 0.015       # baseline FP exit / review (S1)
    q1_per_review: float = 0.030       # FP exit / review WITH initiative (S1, S3)

    # --- RES transition probabilities (annual, during the course) ----------
    # Of completed ressourceforløb, roughly a third progress to FP and a quarter
    # to fleksjob over an average ~2-3 year course; ordinary employment is rare.
    # Converted to approximate ANNUAL hazards below. (S2)
    res_max_years: int = 5             # statutory max duration of a ressourceforløb
    q_res_work0: float = 0.10          # annual RES -> work/fleksjob, baseline (S2)
    q_res_work1: float = 0.15          # annual RES -> work/fleksjob, initiative (S2, S3)
    q_res_to_fp0: float = 0.10         # annual RES -> FP progression, baseline (S2)
    q_res_to_fp1: float = 0.075        # annual RES -> FP progression, initiative (S2, S3)
    res_expiry_to_fp: float = 0.60     # [ASSUMPTION] course expires unresolved -> FP (else OTH)

    relapse_per_year: float = 0.04     # [ASSUMPTION] annual prob of returning to FP after exit

    # --- horizon & discounting ---------------------------------------------
    # Folkepension age for today's 18-30 cohort will realistically be ~70-72
    # under the indexation rule, so the avoided-benefit stream is 40-52 years
    # long -> NPV is highly sensitive to the discount schedule (the same reason
    # the long-horizon mink valuation is a fair analogy).
    folkepension_age: int = 70         # [ASSUMPTION, indexed]
    # Finansministeriet declining social discount rate (2021 guidance):
    discount_schedule: tuple = ((35, 0.035), (70, 0.025), (10_000, 0.015))

    # --- programme cost -----------------------------------------------------
    # Social Sundhed is volunteer-driven, so the marginal cost per participant is
    # mainly coordination + professional supervision. [ASSUMPTION; replace with
    # the organisation's own per-participant cost accounting]
    program_cost_per_participant: float = 10_000  # marginal coordination cost [ASSUMPTION]


# ---------------------------------------------------------------------------
# SOURCES for the literature-anchored parameters above
# ---------------------------------------------------------------------------
# These are the public, named sources the default values lean on. They are
# DIRECTIONAL anchors for a student decision-support model, NOT exact register
# extractions. Before any external claim, replace each with the precise figure
# pulled for the 18-30 cohort from the live source (see docs/methods.md §3, §7).
#
# (S1) Reform of førtidspension and fleksjob (Lov nr. 1380 af 23/12/2012, in
#      force 1 Jan 2013): permanent FP for under-40s only when work capacity
#      "obviously" cannot be developed; otherwise ressourceforløb. Combined with
#      DST/STAR statistics showing that annual revocations (frakendelser) are a
#      very small share of the FP stock -> low q0_per_review and high
#      share_permanent.
# (S2) STAR / jobindsats.dk result statistics for completed ressourceforløb and
#      Rigsrevisionen, "Beretning om ressourceforløb" (9/2019): few participants
#      reach ordinary employment; fleksjob and progression into FP dominate the
#      outcome mix -> p_employment/p_fleksjob/p_other and the RES hazards.
# (S3) IPS (Individual Placement and Support) evidence — international
#      meta-analyses and the Danish IPS trials — employment effects on the order
#      of +10-15 pp for hard-to-place groups; used as an UPPER anchor for the
#      initiative's incremental effect (Δq). Social Sundhed's bridging model is
#      lighter-touch than full IPS, so defaults sit in the lower part of that
#      range.
# ---------------------------------------------------------------------------


# State codes used throughout the microsimulation
FP, RES, EMP, FLEX, OTH = 0, 1, 2, 3, 4
STATE_NAMES = {FP: "førtidspension", RES: "ressourceforløb",
               EMP: "employment", FLEX: "fleksjob", OTH: "other_benefit"}


# ---------------------------------------------------------------------------
# 2. DISCOUNTING  (Finansministeriet declining-rate schedule)
# ---------------------------------------------------------------------------
def discount_factors(n_years: int, p: Params) -> np.ndarray:
    """Cumulative discount factor DF[t] for t = 0..n_years (t=0 -> 1.0)."""
    df = np.ones(n_years + 1)
    for t in range(1, n_years + 1):
        rate = next(r for cutoff, r in p.discount_schedule if t <= cutoff)
        df[t] = df[t - 1] / (1.0 + rate)
    return df


# ---------------------------------------------------------------------------
# 3. SYNTHETIC POPULATION
# ---------------------------------------------------------------------------
def generate_population(p: Params, rng: np.random.Generator) -> dict:
    """Create a synthetic cohort spanning the FP and RES tracks."""
    n = p.n_individuals

    # Age: skew slightly toward the older end of 18-30 (more grants at 25-30).
    age_weights = np.linspace(0.6, 1.4, p.age_max - p.age_min + 1)
    age_weights /= age_weights.sum()
    age = rng.choice(np.arange(p.age_min, p.age_max + 1), size=n, p=age_weights)

    is_single = rng.random(n) < p.share_single
    track = np.where(rng.random(n) < p.share_track_res, RES, FP)

    # Potential annual NET public cost in each "on-support" state, per row.
    cost_fp = np.where(is_single, p.benefit_fp_single, p.benefit_fp_cohab) * (1 - p.tax_back_fp)
    cost_res = np.where(is_single, p.benefit_res_single, p.benefit_res_cohab) * (1 - p.tax_back_res)

    # FP responsiveness (permanent cases never exit). Only meaningful for FP-origin
    # rows, but RES rows that later progress to FP also need a value -> draw for all.
    responsive = rng.random(n) >= p.share_permanent

    # Remaining ressourceforløb duration (years) for RES-origin rows.
    res_years_left = rng.integers(1, p.res_max_years + 1, size=n)

    program_cost = np.full(n, float(p.program_cost_per_participant))

    return {
        "age": age.astype(int),
        "is_single": is_single,
        "track": track.astype(np.int8),
        "cost_fp": cost_fp.astype(float),
        "cost_res": cost_res.astype(float),
        "responsive": responsive,
        "res_years_left": res_years_left.astype(int),
        "program_cost": program_cost,
    }


# ---------------------------------------------------------------------------
# 4. MICROSIMULATION  (vectorised Monte-Carlo, two arms)
# ---------------------------------------------------------------------------
def _annual_net_cost(state: np.ndarray, ens: dict, p: Params) -> np.ndarray:
    """Net public cost for one year given each row's current state."""
    cost = np.zeros(state.shape, dtype=float)
    cost[state == FP] = ens["cost_fp"][state == FP]
    cost[state == RES] = ens["cost_res"][state == RES]
    cost[state == EMP] = p.net_cost_employment
    cost[state == FLEX] = p.net_cost_fleksjob
    cost[state == OTH] = p.net_cost_other
    return cost


def _simulate_arm(arm: dict, ens: dict, df: np.ndarray,
                  p: Params, rng: np.random.Generator) -> np.ndarray:
    """Discounted lifetime net public cost per ensemble row for one arm.

    `arm` carries the three policy-sensitive probabilities:
        q_fp_review, q_res_work, q_res_to_fp
    """
    E = ens["age"].size
    years_to_go = (p.folkepension_age - ens["age"]).astype(int)
    Tmax = int(years_to_go.max())

    state = ens["track"].astype(np.int8).copy()      # start on FP or RES
    res_left = ens["res_years_left"].copy()
    cost = np.zeros(E)

    # cumulative thresholds for the exit-destination draw
    p_emp = p.p_employment
    p_flex = p.p_employment + p.p_fleksjob

    def _assign_exit(mask: np.ndarray) -> None:
        """Send rows in `mask` to EMP/FLEX/OTH by the destination split."""
        if not mask.any():
            return
        dd = rng.random(E)
        dest = np.where(dd < p_emp, EMP, np.where(dd < p_flex, FLEX, OTH))
        state[mask] = dest[mask].astype(np.int8)

    for t in range(Tmax):
        active = t < years_to_go                      # still below folkepension age

        # --- RES dynamics (annual, during the course) ---
        in_res = (state == RES) & active
        if in_res.any():
            # exit to work/fleksjob
            to_work = in_res & (rng.random(E) < arm["q_res_work"])
            _assign_exit(to_work)
            # progression into FP (among those still in RES this year)
            still_res = (state == RES) & active
            to_fp = still_res & (rng.random(E) < arm["q_res_to_fp"])
            state[to_fp] = FP
            # course clock ticks for everyone who began the year in RES
            res_left[in_res] -= 1
            # expiry: course ran out while still unresolved
            expired = (state == RES) & active & (res_left <= 0)
            if expired.any():
                go_fp = expired & (rng.random(E) < p.res_expiry_to_fp)
                state[go_fp] = FP
                _assign_exit(expired & ~go_fp)        # remainder -> OTH-ish exit

        # --- FP dynamics: mandatory re-evaluation ---
        is_review = (t > 0) and (t % p.review_interval == 0)
        if is_review:
            elig = (state == FP) & active & ens["responsive"]
            exit_now = elig & (rng.random(E) < arm["q_fp_review"])
            _assign_exit(exit_now)

        # --- relapse back to FP from work/fleksjob/other ---
        off_support = np.isin(state, (EMP, FLEX, OTH)) & active
        relapse = off_support & (rng.random(E) < p.relapse_per_year)
        state[relapse] = FP

        # --- accrue discounted cost for the year ---
        cost += _annual_net_cost(state, ens, p) * active * df[t]

    return cost


def simulate(p: Params, pop: dict, rng: np.random.Generator) -> dict:
    """Run both arms and return per-individual expected savings + ensemble."""
    n = pop["age"].size
    D = p.mc_draws

    # Replicate each individual D times -> Monte-Carlo ensemble.
    ens = {k: np.repeat(v, D, axis=0) for k, v in pop.items()}

    Tmax = int(p.folkepension_age - pop["age"].min())
    df = discount_factors(Tmax, p)

    arm_control = {"q_fp_review": p.q0_per_review,
                   "q_res_work": p.q_res_work0,
                   "q_res_to_fp": p.q_res_to_fp0}
    arm_treated = {"q_fp_review": p.q1_per_review,
                   "q_res_work": p.q_res_work1,
                   "q_res_to_fp": p.q_res_to_fp1}

    cost_control = _simulate_arm(arm_control, ens, df, p, rng)
    cost_treated = _simulate_arm(arm_treated, ens, df, p, rng)

    saving = cost_control - cost_treated - ens["program_cost"]
    saving_per_individual = saving.reshape(n, D).mean(axis=1)

    return {
        "saving_ensemble": saving,                         # length n*D
        "saving_per_individual": saving_per_individual,    # length n
        "track_ensemble": ens["track"],                    # length n*D
        "track_individual": pop["track"],                  # length n
    }


# ---------------------------------------------------------------------------
# 5. REPORTING
# ---------------------------------------------------------------------------
def summarize(p: Params, res: dict) -> dict:
    s_ind = res["saving_per_individual"]
    s_ens = res["saving_ensemble"]
    tr_ind = res["track_individual"]

    by_track = {}
    for code in (FP, RES):
        m = tr_ind == code
        by_track[STATE_NAMES[code]] = (
            float(s_ind[m].mean()) if m.any() else float("nan")
        )

    return {
        "mean_per_participant": float(s_ind.mean()),
        "median_per_participant": float(np.median(s_ind)),
        "p05": float(np.percentile(s_ens, 5)),
        "p95": float(np.percentile(s_ens, 95)),
        "share_net_positive": float((s_ens > 0).mean()),
        "total_cohort": float(s_ind.sum()),
        "n": int(s_ind.size),
        "by_track": by_track,
    }


def one_way_sensitivity(base: Params) -> list[tuple[str, float, float]]:
    """Re-run the model varying one key driver at a time (low/high)."""
    fast = replace(base, n_individuals=700, mc_draws=120)

    def run(p: Params) -> float:
        rng = np.random.default_rng(p.seed)
        pop = generate_population(p, rng)
        return summarize(p, simulate(p, pop, rng))["mean_per_participant"]

    scenarios = {
        "FP exit effect Δq (per review)": [
            replace(fast, q1_per_review=fast.q0_per_review + 0.01),
            replace(fast, q1_per_review=fast.q0_per_review + 0.06),
        ],
        "RES->work effect (annual)": [
            replace(fast, q_res_work1=fast.q_res_work0 + 0.02),
            replace(fast, q_res_work1=fast.q_res_work0 + 0.12),
        ],
        "RES->FP prevention (annual)": [
            replace(fast, q_res_to_fp1=fast.q_res_to_fp0),            # no prevention
            replace(fast, q_res_to_fp1=max(0.0, fast.q_res_to_fp0 - 0.03)),  # strong prevention
        ],
        "Share starting in RES": [
            replace(fast, share_track_res=0.20),
            replace(fast, share_track_res=0.80),
        ],
        "Share permanent FP (never exits)": [
            replace(fast, share_permanent=0.65),
            replace(fast, share_permanent=0.25),
        ],
        "Programme cost per participant": [
            replace(fast, program_cost_per_participant=30_000),
            replace(fast, program_cost_per_participant=3_000),
        ],
        "Folkepension age (horizon)": [
            replace(fast, folkepension_age=67),
            replace(fast, folkepension_age=72),
        ],
        "Flat discount rate": [
            replace(fast, discount_schedule=((10_000, 0.05),)),
            replace(fast, discount_schedule=((10_000, 0.02),)),
        ],
    }

    out = []
    for name, (low, high) in scenarios.items():
        out.append((name, run(low), run(high)))
    return out


def print_report(p: Params, res: dict) -> None:
    s = summarize(p, res)
    MINK_TOTAL_BN = 29.2  # DKK bn, FVM Jan-2025 estimate (for scale comparison)

    print("=" * 72)
    print(" SYNTHETIC FISCAL-SAVINGS MODEL — young FP + ressourceforløb (18-30)")
    print(" Social Sundhed 'Social Brobygger' — illustrative, synthetic data")
    print("=" * 72)
    print(f" Cohort size (synthetic)............ {s['n']:>14,}")
    print(f" Mean NPV saving / participant...... {s['mean_per_participant']:>14,.0f} DKK")
    print(f" Median NPV saving / participant.... {s['median_per_participant']:>14,.0f} DKK")
    print(f" 5–95% range (individual draws)..... {s['p05']:>14,.0f} … {s['p95']:,.0f} DKK")
    print(f" Share of draws net-positive........ {s['share_net_positive']:>13.1%}")
    print(f" Total NPV saving for the cohort.... {s['total_cohort']:>14,.0f} DKK")
    print("-" * 72)
    print(" Mean NPV saving / participant, by starting track:")
    for name, val in s["by_track"].items():
        print(f"   {name:<22} {val:>14,.0f} DKK")
    print("-" * 72)
    mean_pp = s["mean_per_participant"]
    if mean_pp > 0:
        breakeven = MINK_TOTAL_BN * 1e9 / mean_pp
        print(f" For scale: the DKK {MINK_TOTAL_BN} bn mink bill equals the lifetime")
        print(f" saving from roughly {breakeven:,.0f} successful cases at this mean.")
    print("=" * 72)

    print("\n ONE-WAY SENSITIVITY (mean NPV saving / participant, DKK)")
    print(" driver                                    low            high")
    print(" " + "-" * 64)
    for name, lo, hi in one_way_sensitivity(p):
        print(f" {name:<38} {lo:>12,.0f}   {hi:>12,.0f}")
    print()
    print(" NOTE: defaults are LITERATURE/REGISTER-ANCHORED but directional (see the")
    print(" SOURCES block in this file). Replace with exact 18-30 register figures")
    print(" before citing. See docs/methods.md and docs/data_dictionary.md.")


# ---------------------------------------------------------------------------
# 6. ENTRY POINT
# ---------------------------------------------------------------------------
def main() -> None:
    p = Params()
    rng = np.random.default_rng(p.seed)
    pop = generate_population(p, rng)
    res = simulate(p, pop, rng)
    print_report(p, res)


if __name__ == "__main__":
    main()
