# Case study: four instrument failures caught before a number was published

The Challenge's 2026 open problems argue that *"better diagnostics matter just
as much as better models"*. This is what that costs, and what it buys.

Between rounds 19 and 27 we built a line-rhythm judge, pointed it at real
material, and **published no result about that material** — because each time
the instrument was put through its own controls, the instrument failed first.
Below is every failure, what a false positive would have looked like had the
control been absent, and the control that caught it.

None of these are hypotheticals. Each row is a run that happened, in order.

| # | Failure | How the false positive would have looked | The control that caught it | Generalisable lesson |
|---|---|---|---|---|
| **1** | **Wrong standardiser.** The H0 pool was built on the *substrate* map and used to standardise the *reader's* map — the central assumption of the design. | The reading scored **T₁₀ = 1.1186** against a pre-registered z\* = 2.6765. Had the bias landed the other way, a **+0.9σ systematic** would have carried a null result over the line and it would have read as a clean detection. | A **rot90 negative control**, which must not fire, scored **4.3626** — above threshold, while the real reading was below it. Both nulls outscored the reading (mean u **+0.96** rot90, **+0.88** permz, vs **+0.55** for the reader map; under a correct H0, mean 0). | A null model built on different material than the thing you are testing does not standardise it. **Always run a negative control that is required to stay silent** — it is the only thing that detects a shift affecting your primary and your null equally. |
| **2** | **Unvalidated repair.** The fix (standardise against surrogates of the reader's *own* map) worked — and revealed something worse: **real text scored *negative*.** | With the repair in place but unvalidated, a low score would have been reported as "no text detected". It would have been an artifact of a judge that *penalises* text. | Validation **on labelled truth before use**: without text, mosaic surrogates gave u = **−0.01 / +0.19** (pass) where the old pool gave **+2.04 / +2.41** (fail). *With* text, displacement went **negative in all three arms** (−0.20 / −1.94 / **−2.76**); raw z_mos was **+0.12** without text and **−1.97** with it. | Fixing the calibration is not the same as validating it. **Validate where truth exists before applying where it does not** — and check the sign on positives, not just the calibration on negatives. |
| **3** | **Look-elsewhere (Davies' problem).** The statistic maximises over 99 orientations; the null did not account for the same search. | Any window could be mined for its best angle. The failure was *inverted* here — the surrogate maximum beat the observed one on text — but the same defect produces inflated significance whenever the search favours the observation. | Measuring the mechanism directly: observed peak ÷ surrogate peak = **0.99 on blank papyrus** but **0.73–0.78 on real high-contrast text**, the null winning in 75–100 % of windows. **3 640 evaluations across 8 candidate null families; none passed the admissibility gate, so the figure was never computed.** Fixing the direction recovered **70–95 %** of the deficit (−1.78 → −0.44). | **A maximum over a nuisance parameter must be compared against a null that maximises over the same parameter.** And a pre-registered gate has to be able to return *"no admissible instrument"* — and stop. |
| **4** | **Substrate structure mistaken for writing.** A 2.68 mm periodicity in the photograph, sharp and coherent over 59 mm, read as line spacing. | A judge pre-registered at P₀ = 2.68 mm would have been a **fibre-weave detector** scoring confidently on blank papyrus. One at P₀ = 7.45 mm would have sat on top of the blank substrate's own in-band periodicity. Either would have produced a publishable "detection". | A **light/dark channel test**. The comb is present *entire* in ink-free papyrus (enhancement 4.97 vs 5.14) and is **stronger in the light channel than the dark** (7.37 vs 5.14). **Ink can only darken; a symmetric light/dark comb is relief.** An independent point-process periodogram over glyph centroids (maxT permutation null, M = 199) gave **p ≥ 0.165** in every condition and **≥ 0.51** in the most favourable. | **Ink can only darken — so a periodicity that is symmetric in polarity is geometry, not writing.** A one-line control, and it is decisive. Also: 7.45 mm turned out to be the same 2.68 mm comb read at the wrong angle. |

## Two further defects, found by auditing our own record

**A phantom prior.** The line-spacing prior P₀ = 4.03 mm turned out to rest on a
broken citation chain: it came from a median of eight first-ACF-peaks measured
with a **free angle** — the very estimator failure #4 had just falsified — with
angles jumping ±45° within one manuscript and **two text-free segments included
in the average**. Re-measured against the label, only one segment has countable
lines (4 centres at 5.28 / 12.12 / 17.87 / 22.61 mm) giving **P₀ = 6.3 mm
(5.75–6.47)**, independently corroborated at 6.17, 6.46, 6.32 and 6.33. The
proposed 46.7 mm window then gives **7.39 periods < 8** and does not qualify.

**A band-clipping artifact in our own diagnostic.** The claim that blank
substrate shows a 15.4× in-band enhancement peaking at 7.945 mm in 6 of 8
segments was an artifact: enhancement grows monotonically with period over
papyrus because the spectrum is **red**, and the band had been clipped. Whitened,
blank segments are **flat (S ≈ 1.00 across the band)**. The verdicts resting on
the channel test and the direct count do not change; what falls is our own
earlier argument that one of those kills had been *necessary*. Corrected
retroactively rather than quietly.

## What this cost, and what it bought

Nine rounds of judgement (19–27) produced **zero claims about the material**.
Every candidate signal was killed by a control, and in two cases the control
killed a conclusion we had already written down.

> **Zero false claims in nine rounds of judgements. The cost was claiming
> nothing — and that is the trade the field should be able to choose.**

The tooling in this repository is the part of that programme that generalises:
the judges (`validation/`) with their false-positive rates bounded on real
substrate, the null-model comparison showing the standard permutation null is
unsafe above 100 keV, and the power curves that say when a negative result is
*inconclusive by construction* rather than informative.

## Record

The runs above are lab records, not shipped artifacts; integrity hashes are
quoted so the record remains checkable if released.

| item | hash / count |
|---|---|
| frozen reader used throughout | `e0b9ec7e…` (unchanged across all nine rounds) |
| judge source | `101_vara_v2.py` `bbd7a579…` |
| sealed reader maps | 40/40 byte-identical at open and close; aggregate `0d0dd390a935073a08ca307cbc6e7566fa5b68e32f457de6289ae3ac803b0cba` |
| pre-registered protocols | round 24 `a085c610…`, round 25 `c4a88d30…`, sealed prior declaration `b73518ac…` |
| audit scale | 3 640 evaluations, 8 null families (failure #3) |

What *is* shipped here: `validation/data/*.json` (the rounds 19–22 calibration
and power campaigns) and `validation/data/substrate/*.npz`, which reproduce the
null-model finding offline — see [`../validation/README.md`](../validation/README.md).
