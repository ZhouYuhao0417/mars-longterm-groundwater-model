# Model methods and parameter definitions

[中文方法](METHODS_ZH.md)

## Spatial model

The completed runs retain the original 400 m, two-dimensional, finite-volume diffusive-wave solver. The model includes DEM-controlled surface gradients, filling of a closed source depression, spill across its lowest natural saddle, downstream propagation, an open boundary and a mass-balance diagnostic. Mars gravity is `3.721 m s⁻²`, Manning's `n` is `0.0545`, and explicit surface-flow steps are `600 s`.

The point at `75.937180°E, 18.136689°N` is a single prescribed equivalent crater-side source applied after source-basin filling at the candidate low-rim outlet. It does not represent surface flow along the northeast–southwest Nili Fossae trough or assume delivery through that trough to Jezero's western-delta headwaters.

## Interface parameters

`Q(t)` is the prescribed raw discharge of the single equivalent crater-side input in `m³ s⁻¹`. It is distributed with source-cell weights whose sum is one and is therefore applied exactly once. The source is a lumped boundary condition, not a resolved trough-flow calculation.

`C` is an effective along-path retention coefficient:

```text
Vraw(t)  = integral[0,t] Q(s) ds
Veff(t)  = C Vraw(t)
Vloss(t) = (1-C) Vraw(t)
```

`C` is not a precipitation-runoff coefficient. Values `0.4`, `0.7` and `1.0` define the loss sensitivity analysis.

`T` is the hydrograph cutoff. The current-time control selects the state and ledger time; it does not change `T` or reinject water.

## Hydrographs

Constant baseflow:

```text
Q(t) = Qb
```

Exponential recession:

```text
Q(t) = Qb + Q0 exp(-t/tau)
```

Staged pulses:

```text
Q(t) = Qb + Q0 mk, for t/T in [ak,bk)
```

The high scenario uses pulse multipliers `1.00`, `0.35`, `0.80` and `0.60` over normalized intervals `[0.00,0.02)`, `[0.02,0.08)`, `[0.25,0.28)` and `[0.55,0.57)`. All source volumes are evaluated by analytical integration, not daily rectangular summation.

## Long-duration execution

The source depression has a modeled capacity of `134.53242 km³` to the lowest saddle at `-1223.6875 m`. Before spill, the analytical hydrograph integral advances the source storage directly. After spill, the 600 s finite-volume equations are retained. A dynamic computational window excludes distant dry cells without changing wet-cell equations. The accepted medium v2 run uses float64 hydrodynamic state/flux, completes 17.339773 years of explicit routing after 2.660227 years of analytical prefill, and skips no downstream time. Older accelerated high outputs are legacy exploratory products, not same-version accepted results.

## Water ledger

At each reported time:

```text
Vraw = Vloss + Vsource + Vsurface + Vboundary + epsilon
```

The open boundary removes exported water from the domain, preventing unlimited inundation growth based solely on cumulative volume.

## Accepted v2 results

| Metric | Low | Medium |
|---|---:|---:|
| Duration | 10 yr | 20 yr |
| Source fill / explicit routing | no spill / 0 yr | 2.660227 yr / 17.339773 yr |
| Raw release | 31.5576 km³ | 473.0025 km³ |
| Effective input | 12.6230 km³ | 331.1018 km³ |
| Along-path loss | 18.9346 km³ | 141.9008 km³ |
| Source storage | 12.6230 km³ | 134.5324 km³ |
| Downstream surface storage | 0 km³ | 19.7960 km³ |
| Open-boundary outflow | 0 km³ | 176.7734 km³ |
| Maximum depth | 115.1065 m | 380.0000 m |
| HW1–HW3 exact reporting-wet cells | 0/3 | 3/3 |

Both records have `complete=true`, `paper_usable=true`, all declared publication gates true, closed ledgers and no downstream time skipping. The old `3.727989 yr` incomplete medium checkpoint remains in `data/excluded/` only as audit history and is not used by the accepted viewer.

## Legacy boundary-condition audit

The former constant boundary condition `160,000 m³ s⁻¹ × 180 d` releases `2488.32 km³`; after `C=0.60`, `1492.992 km³` enters the DEM ledger. This is about 11.1 times the modeled source-depression capacity, so rapid spill, broad downstream inundation and large boundary export are expected consequences of the imposed volume.

## Publication rule

Numerical values must be taken from the accepted summary JSON and corresponding arrays, not measured from either interactive preview. Quantitative use requires `complete=true`, `paper_usable=true`, all v2 gates true, a closed water ledger, no skipped downstream time and passing regression tests. Browser `.f32` files are display copies with hashes recorded in `data/accepted-v2/accepted_v2_manifest.json`.
