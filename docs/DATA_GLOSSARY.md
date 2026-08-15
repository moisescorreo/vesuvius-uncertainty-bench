# Reading the shipped campaign JSONs

The result files under `validation/data/`, `benchmark/data/` and
`audit/data/` are **verbatim run records** from the instrument that produced
them — not re-typed summaries. Nothing has been edited except stripping local
filesystem paths.

That has one consequence for readers: the original instrument was written in
Spanish, so **the keys inside those JSONs are Spanish**. We deliberately did not
rewrite them, because a hand-translated result file is a result file somebody
could have altered. The tables in `RESULTS.md` and the reports in each package
are the English surface; these files are the receipts underneath.

Every script in `scripts/` reads and prints them in English. You should not
need this glossary unless you open the raw JSON.

## Key glossary

| Spanish key | English |
|---|---|
| `vara` | `ruler` — the coherent line-spacing judge |
| `inco` / `inco_v2` | `incoherence` — the tiled, phase-invariant judge |
| `juez` / `jueces` | judge / judges |
| `sustrato` | substrate (blank papyrus, no text) |
| `lienzo` | canvas (synthetic mosaicked substrate — an INVALID null) |
| `nulo` | null model |
| `z_mos` | z against the block-mosaic null (**decides**) |
| `z_perm` | z against the permutation null (**diagnostic only**) |
| `p_mos`, `p_perm` | empirical p against each null |
| `z_estrella` | `z*` — the calibrated claim threshold |
| `piso_p` | arithmetic floor of the empirical p, `1/(n+1)` |
| `banda_mm` | search band for line spacing, in mm |
| `banda_completa` | whether the window can resolve the whole band |
| `alcance_mm` | reach — the largest period the window can resolve |
| `min_periodos` | periods that must fit inside the window |
| `n_perm`, `n_mos` | null draws of each kind |
| `celda` / `celdas` | cell / cells (16 px aggregation grid) |
| `mm_por_celda` | mm per cell |
| `ventana` | window |
| `corrida` / `corridas` | run / runs |
| `semilla` | seed |
| `potencia` | statistical power |
| `inyeccion` / `inyecciones` | injection(s) of real text at controlled contrast |
| `c_realizado` | realised contrast (measured, not nominal) |
| `c_lector` | contrast the reader actually delivers |
| `contraste(s)` | contrast level(s) |
| `donante` | donor (the real-text source for injection) |
| `interlinea_mm` | line spacing, mm |
| `periodo_mm` | detected period, mm |
| `mascara` | mask |
| `frac_valida` | valid fraction |
| `cobertura` | coverage |
| `techo` | ceiling |
| `veredicto` | verdict |
| `prueba_esfuerzo_lienzo` | canvas stress test (the null that FALSIFIES) |
| `falsea` | "falsifies" — this null manufactures the signal |
| `curacion` | curation |
| `escala` | scale |
| `agregado` | aggregate |
| `por_segmento` | per segment |
| `campeon` | champion (an out-of-domain 54 keV reference model) |
| `media_z`, `sd_z` | mean and sd over the z-stack — substrate baselines |
| `amplitud` | amplitude — a substrate baseline |
| `constancia` | attestation — a note recording what was NOT done |
| `holdout` | holdout (same word) |

## Verdict vocabulary

| term | meaning |
|---|---|
| `LINES` / `RENGLONES` | claim: periodic line rhythm detected |
| `negativo` | negative — no detection, and the test had power |
| `marginal` | above 0.7·z\* but below z\* |
| `inconclusive_extent` / `inconcluso_extensión` | the window is too small to resolve the band — a null result carries **no information** |
| `INCONCLUSO POR CONSTRUCCIÓN` | inconclusive by construction: measured power is too low for a negative to mean anything |
| `NO-GO` | a pre-registered power gate refused to let the judgement run |

`inconclusive_extent` and `inconclusive by construction` are first-class
outcomes in this instrument, not failures. Most of what it reports is one of
them, and reporting them as "no text found" would be the error the whole
package exists to prevent.
