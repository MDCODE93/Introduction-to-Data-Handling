# Methods — Synthetic fiscal-savings model for young disability support (18–30)

**Course:** Social Data Science · **Status:** draft for hand-in · **Data:** 100% synthetic

This note documents the model in [`early_retirement_savings_model.py`](../early_retirement_savings_model.py).
It is written so a reader can reproduce and criticise every number.

---

## 1. Research question

How much **future public expenditure** could Social Sundhed's *Social Brobygger*
initiative plausibly avoid among 18–30-year-olds who are on **førtidspension (FP)**
or in a **ressourceforløb (RES)**, if the initiative raises their chance of moving
into work / fleksjob (and, for RES, lowers their chance of progressing into FP)?

We express the answer as a **net present value (NPV)** per participant and for a
synthetic cohort. This is a *decision-support* estimate, not a causal finding.

## 2. The mink analogy (why NPV over a long horizon)

When the state compensated mink farmers (≈ **DKK 29.2 bn**, Ministry of Food,
Agriculture and Fisheries, Jan-2025), it valued the **present value of lost
future income streams**. We use the mirror image: the **present value of avoided
future expenditure streams** when a young person leaves benefits early. Because
the cohort is 18–30, the relevant horizon to folkepension age is ~40–52 years,
so — exactly as in the mink case — the result is dominated by the discount
schedule. We therefore make discounting explicit and test it.

## 3. Data: a synthetic register

We generate a synthetic person-level dataset that imitates the *structure* of a
Danish administrative extract (one person-row; typed variables; a synthetic
pseudo-key). It contains **no real personal data**. Variables and valid ranges
are documented in [`data_dictionary.md`](data_dictionary.md) and the
machine-readable `data/codebook.csv`. The generator draws:

- **age** (18–30, skewed toward 25–30, where grants are more common);
- **civil status** (single / cohabiting → benefit rate);
- **track** (FP or RES) with share `share_track_res`;
- **FP responsiveness** — a flag for whether work capacity can develop at all
  (post-2013, permanent FP for under-40s is only granted when capacity
  "obviously" cannot develop, so a real share has ≈0 exit probability);
- **remaining RES duration** (1–5 years).

## 4. Model: a two-arm Markov microsimulation

Each synthetic individual is simulated year-by-year from their start age to
folkepension age, in **five states**:

```
FP  førtidspension      RES ressourceforløb
EMP employment          FLEX fleksjob          OTH other benefit
```

Annual transitions:

- **RES → work/fleksjob** with prob. `q_res_work` (an exit, split EMP/FLEX/OTH);
- **RES → FP** progression with prob. `q_res_to_fp` (the expensive event);
- on **RES expiry** (course runs out unresolved) → FP with prob. `res_expiry_to_fp`, else an exit;
- **FP → exit** only at the **mandatory 3-yearly re-evaluation**, with prob.
  `q_fp_review`, and only for *responsive* cases;
- **relapse** EMP/FLEX/OTH → FP with annual prob. `relapse_per_year`.

We run two arms with identical draws structure:

| arm | `q_fp_review` | `q_res_work` | `q_res_to_fp` |
|-----|---------------|--------------|---------------|
| **control** (no initiative) | `q0_per_review` | `q_res_work0` | `q_res_to_fp0` |
| **treated** (initiative)    | `q1_per_review` | `q_res_work1` | `q_res_to_fp1` |

## 5. Fiscal accounting

Each state carries a **net annual public cost** (benefit minus tax clawed back;
employment is *negative* because the state receives net tax):

$$
\text{Saving}_i \;=\; \underbrace{\text{PV}^{\text{control}}_i - \text{PV}^{\text{treated}}_i}_{\text{avoided net expenditure}} \;-\; C_{\text{program}}
$$

with present value

$$
\text{PV}_i \;=\; \sum_{t=0}^{T_i} \text{cost}_{i,t}\, \cdot \, \mathrm{DF}_t ,
\qquad
\mathrm{DF}_t = \prod_{s=1}^{t}\frac{1}{1+r_s}.
$$

The discount rate $r_s$ follows **Finansministeriet's declining schedule**
(3.5 % years 1–35, 2.5 % years 36–70, 1.5 % thereafter).

## 6. Uncertainty

Each individual is replicated `mc_draws` times (Monte-Carlo), so every reported
figure is a mean over draws and we can show the **5–95 % spread** and the
**share of draws that are net-positive**.

We report uncertainty at two levels:

1. **One-way sensitivity (tornado)** — re-runs the model varying one assumption
   at a time (in `early_retirement_savings_model.py`).
2. **Probabilistic sensitivity analysis (PSA)** — `probabilistic_sensitivity.py`
   samples **all** uncertain parameters *jointly* from distributions (Beta for
   probabilities, Dirichlet for the destination split, Normal for costs, Uniform
   for the treatment uplifts and discount rate), re-runs the simulation per
   draw, and produces a **full uncertainty fan** plus a **driver ranking**
   (Spearman rank correlation of each input with the output). The PSA reports a
   **95 % credible interval** and **P(saving > 0)**.

This is the honest core of the hand-in: the *level* of the headline number is
far less defensible than its *direction* and its *sensitivity ranking*.

## 6a. Evidence anchoring of the key parameters

The previously placeholder `[NEEDS EVIDENCE]` parameters are now anchored in
named public sources (see the `SOURCES` block in
[`early_retirement_savings_model.py`](../early_retirement_savings_model.py)).
They are **directional anchors**, not exact register extractions — replace each
with the precise figure for the 18–30 cohort before any external claim.

| parameter | default | anchor |
|-----------|---------|--------|
| `share_permanent` | 0.55 | (S1) Post-2013 rule: young FP grants are mostly genuinely permanent; revocations are a small share of the stock |
| `q0_per_review` / `q1_per_review` | 0.015 / 0.030 | (S1, S3) Revocation is rare; the initiative roughly doubles it, in the lower-to-mid IPS range |
| `p_employment` / `p_fleksjob` / `p_other_benefit` | 0.20 / 0.45 / 0.35 | (S2) Danish exit pattern: fleksjob dominates, ordinary jobs are a minority |
| `q_res_work0` / `q_res_work1` | 0.10 / 0.15 | (S2, S3) ~quarter of completed forløb reach fleksjob/work; uplift from IPS evidence |
| `q_res_to_fp0` / `q_res_to_fp1` | 0.10 / 0.075 | (S2) ~third of completed forløb progress to FP; initiative prevents some |

**Sources**

- **(S1)** Reform of førtidspension and fleksjob (Lov nr. 1380 af 23/12/2012,
  in force 1 Jan 2013) + DST/STAR statistics on revocations (frakendelser).
- **(S2)** STAR / jobindsats.dk result statistics for completed ressourceforløb;
  Rigsrevisionen, *Beretning om ressourceforløb* (9/2019).
- **(S3)** IPS (Individual Placement and Support) evidence — international
  meta-analyses and the Danish IPS trials — employment effects ≈ +10–15 pp for
  hard-to-place groups, used as an **upper** anchor for the initiative's effect.

## 7. Key limitations (state these in the report)

1. **Synthetic data** — levels are illustrative; the anchored parameters are
   directional, not exact register extractions for the 18–30 cohort.
2. **No causal identification** — the treatment effect (Δq) is an input anchored
   to IPS evidence (S3), not an estimate for *this* programme. A voluntary
   bridging programme is lighter-touch than full IPS, so the default sits in the
   lower part of that range; a credible own estimate would need an RCT /
   quasi-experiment.
3. **Selection** — participants of a voluntary programme differ from
   non-participants; a naive Δq overstates savings.
4. **Partial fiscal scope** — we count benefits + income tax only, not health-care
   use, VAT, or quality-of-life gains (which would *raise* the social value).
5. **Horizon risk** — folkepension age and the discount schedule are indexed and
   uncertain; both are tested in the tornado and the PSA.

## 8. Reproducing the results

```bash
python early_retirement_savings_model.py     # headline + sensitivity table
python export_synthetic_register.py          # data/synthetic_cohort.csv + codebook.csv
python make_figures.py                        # figures/*.png
python probabilistic_sensitivity.py           # PSA fan + driver ranking + data/psa_draws.csv
```

All randomness is controlled by `Params.seed` (and `MASTER_SEED` in the PSA).
