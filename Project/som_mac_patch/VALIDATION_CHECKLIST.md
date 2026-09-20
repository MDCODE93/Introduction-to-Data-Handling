# SØM Mac patch — numerical validation checklist

Goal: prove the **patched Mac copy** (`som-v3-4_mac.xlsb`) produces results
**identical** to the unmodified model run on **Windows Excel**. The patch only
touches UI plumbing (regex helpers, two UserforForms, Word export), so every
result cell must match to full precision. This checklist tells you exactly which
cells to compare.

> Reference run = the original, signed `som-v3-4.xlsb` opened in Excel for
> Windows (or Excel on a Windows VM). Test run = the patched copy in Excel for
> Mac. Use the **same input case** in both.

---

## 0. Before you start
- [ ] Work on a **copy**; keep the original signed file untouched.
- [ ] Confirm the patch compiled on Mac: VBE ▸ **Debug ▸ Compile VBAProject** = no errors.
- [ ] Decide on **one fixed test case** (see §1) and write its inputs down so they
      are byte-identical in both runs.

## 1. Define a deterministic test case
Pick a single, fully-specified intervention so nothing is ambiguous:
- [ ] One **indsats** (Indsats 1) only — delete/ignore Indsats 2–5.
- [ ] A named **målgruppe** from the Vidensdatabase (record the exact name).
- [ ] A fixed **effektstørrelse**, **effektmål**, and **sammenligningsgrundlag**.
- [ ] Fixed **omkostninger** (record every cost input).
- [ ] Fixed **tidshorisont**, **varighed**, **antal konsekvensår**, and
      **succesrate/population**.
- [ ] Note the **discount rate / slutår** settings (`resultat_start`,
      `resultat_slut`, `resultat_slut_automatisk`).

Record these inputs in the table at the end so the run is reproducible.

## 2. Primary result cells — MUST match exactly
Compare these named ranges (VBE ▸ Insert name box, or Formulas ▸ Name Manager).
Expect identical values to **all decimals**.

| # | Named range | What it is | Win value | Mac value | Match? |
|---|-------------|------------|-----------|-----------|--------|
| 1 | `nettogevinst_samlet` | Total net gain (headline) | | | |
| 2 | `nettogevinst_deltager` | Net gain per participant | | | |
| 3 | `nettogevinst_område` | Net gain by actor/area | | | |
| 4 | `NNV_resprdelt` | Net present value, split by result | | | |
| 5 | `NNV_resprdelt_detaljeret` | NPV, detailed split | | | |
| 6 | `brugersparedeomk` | User-entered saved costs | | | |
| 7 | `brugeromk` | User-entered costs | | | |
| 8 | `endeligomkaktør` | Final cost by actor | | | |
| 9 | `Samlet_omkostning_skøn` / `samlet_omkostning_skøn` | Total estimated cost (SKØN) | | | |
| 10 | `succes_population_output_start` | Success population basis | | | |

## 3. Sensitivity-tool outputs — MUST match exactly
The følsomhed (sensitivity) routines use `CleanString`/`CleanNumbers`, so they are
the **most important** thing to verify after the patch.

| # | Named range | What it is | Win | Mac | Match? |
|---|-------------|------------|-----|-----|--------|
| 11 | `føl_output` | Sensitivity output (main) | | | |
| 12 | `føl_output_succesrate` | Sensitivity vs success rate | | | |
| 13 | `føl_omkostninger` | Sensitivity vs costs | | | |
| 14 | `brugerfoelsomhedoutput` | User sensitivity output | | | |

## 4. Result tables / pivots — spot-check
These are driven by pivots that the macros refresh. Compare the **top-left,
a middle, and the total row** of each.

| # | Named range | Cells to check | Match? |
|---|-------------|----------------|--------|
| 15 | `tab_ressamlet1` | first row, total row | |
| 16 | `tab_resprdelt1`..`tab_resprdelt4` | first + total of each | |
| 17 | `resultat_start`, `resultat_slut`, `resultat_slut_automatisk` | the year values | |

## 5. The helper functions directly (unit check)
Confirm the rewritten regex-free helpers behave identically. In the VBE
**Immediate window** (Ctrl/Cmd+G), run:

```vba
? CleanString("Indsats 12 (a)")     '  -> "12"   (keep digits only)
? CleanString("trin7b")             '  -> "7"
? CleanString("abc")                '  -> ""      (no digits)
? CleanNumbers("Indsats 12 (a)")    '  -> "Indsats  (a)"  (digits removed)
? CleanNumbers("trin7b")            '  -> "trinb"
? CleanNumbers("2024-kr")           '  -> "-kr"
```
- [ ] All six outputs match the comments above (same as the Windows regex result).

## 6. Behavioural (non-numeric) checks
- [ ] Clicking an **"i" info icon** shows the correct help text (MsgBox on Mac).
- [ ] Navigating to **Resultater** the first time does **not** error where the
      `Vælg_visning_res` box used to appear (it is skipped on Mac).
- [ ] Running **Word export** on Mac shows the "not supported on macOS" message
      and does **not** crash.
- [ ] `KopierIndsats`, `TilføjIndsats`, `SletIndsats`, and the målgruppe filters
      run without error.

## 7. Whole-sheet diff (strongest proof)
Belt-and-braces numeric proof that nothing drifted:
- [ ] In **both** runs, after entering the test case, save each result sheet as
      CSV (File ▸ Save As ▸ CSV for the active sheet), e.g. `win_results.csv` and
      `mac_results.csv`.
- [ ] Diff them. From a terminal:
      ```bash
      diff <(tr ';' ',' < win_results.csv) <(tr ';' ',' < mac_results.csv)
      ```
      Expect **no differences** (ignore trailing locale/format-only lines).
      For a tolerance-aware compare, load both in pandas and assert
      `numpy.allclose` on the numeric columns.

## 8. Sign-off
- [ ] All §2–§3 cells match to full precision.
- [ ] §5 helper unit checks pass.
- [ ] §7 CSV diff is empty (numeric).
- [ ] Conclusion: the patched Mac copy is numerically identical to the signed
      Windows reference for this case.

> If ANY result cell differs: re-confirm the inputs are byte-identical first
> (most "differences" are input mismatches). If inputs match but a result
> differs, the culprit is almost certainly a missed `CleanString`/`CleanNumbers`
> copy — search the project again for `vbscript.regexp` and patch the remaining
> one.

---

### Test-case input record (fill in once, reuse for both runs)

| Input | Value |
|-------|-------|
| Indsats name | |
| Målgruppe | |
| Effektstørrelse | |
| Effektmål | |
| Sammenligningsgrundlag | |
| Omkostninger (each) | |
| Tidshorisont | |
| Varighed | |
| Antal konsekvensår | |
| Succesrate / population | |
| Diskonteringsrente | |
| resultat_start / resultat_slut | |
