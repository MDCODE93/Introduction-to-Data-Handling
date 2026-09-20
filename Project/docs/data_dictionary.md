# Data dictionary — `data/synthetic_cohort.csv`

Register-style documentation of the **synthetic** micro-dataset produced by
[`export_synthetic_register.py`](../export_synthetic_register.py). The file
imitates the layout of a Danish administrative extract (one person-row, typed
variables, a synthetic pseudo-key) but contains **no real personal data**.

A machine-readable version of this table is written to `data/codebook.csv`.

| variable | type | label | valid range / values |
|----------|------|-------|----------------------|
| `pnr_synth` | string | Synthetic pseudo-identifier. **Not** a real CPR number; format only resembles one. | `SYN<seed><6-digit row>` |
| `age` | int | Age in completed years at simulation start. | 18–30 |
| `civilstatus` | category | Cohabitation status driving the benefit rate. | `enlig`, `samlevende` |
| `track` | category | Support track the person starts in. | `foertidspension`, `ressourceforloeb` |
| `benefit_gross_dkk` | int | Annual **gross** public transfer in the start state (DKK). | ≥ 0 |
| `net_annual_cost_dkk` | int | Annual **net** public cost = gross × (1 − tax_back) (DKK). | ≥ 0 |
| `fp_responsive` | int | 1 if FP work capacity can develop (eligible to exit at review), else 0. | 0, 1 |
| `res_years_left` | int | Remaining ressourceforløb duration in years (0 if FP track). | 0–5 |
| `years_to_folkepension` | int | Years from start age to folkepension age (model horizon $T_i$). | ≥ 0 |
| `npv_saving_dkk` | int | Monte-Carlo mean NPV of public expenditure avoided, net of programme cost (DKK). | real (can be negative) |

## Provenance of each variable

All variables are **generated**, not observed. They derive from the parameters
in `Params` (see [`methods.md`](methods.md) §3–§5):

- `age` — categorical draw, weights linearly skewed 0.6→1.4 across 18–30.
- `civilstatus` — Bernoulli(`share_single`).
- `track` — Bernoulli(`share_track_res`) → RES else FP.
- `benefit_gross_dkk` — looked up from `benefit_{fp,res}_{single,cohab}`.
- `net_annual_cost_dkk` — `benefit_gross_dkk × (1 − tax_back_{fp,res})`.
- `fp_responsive` — Bernoulli(`1 − share_permanent`).
- `res_years_left` — uniform integer 1…`res_max_years` (RES rows only).
- `npv_saving_dkk` — output of the two-arm microsimulation (see methods §4–§5).

## Parameters and their evidence status

The transition and destination parameters in `Params` are now
**literature/register-anchored** (directional, not exact register extractions).
See the `SOURCES` block in
[`early_retirement_savings_model.py`](../early_retirement_savings_model.py) and
[`methods.md`](methods.md) §6a:

- `share_permanent`, `q0_per_review`, `q1_per_review` — anchored to (S1) the
  2013 reform + DST/STAR revocation statistics and (S3) IPS evidence.
- `p_employment`, `p_fleksjob`, `p_other_benefit`, `q_res_work*`, `q_res_to_fp*`
  — anchored to (S2) STAR/jobindsats ressourceforløb result statistics and
  Rigsrevisionen 9/2019.

**Still `[ASSUMPTION]` (replace with the organisation's / register figures):**
`program_cost_per_participant`, the per-state net costs
(`net_cost_employment/fleksjob/other`), `res_expiry_to_fp`, and the benefit
levels.

Suggested live sources to pull exact 18–30 figures: Danmarks Statistik /
jobindsats.dk register flows for FP and ressourceforløb; STAR evaluations of
ressourceforløb; published IPS evaluations for the treatment effect (Δq).
