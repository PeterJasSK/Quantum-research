# #18 — SYN-LUNGS anatomy-informed placement (+ lungmask, TotalSegmentator on LIDC)

**Letter:** A ([`A_placement`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** A01, A02, A03, A04, F01 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Where a synthetic lung nodule sits matters as much as what it looks like. Real nodules fall into three border classes:
- **well-circumscribed (free):** surrounded by parenchyma;
- **vascularized (juxtavascular):** attached to a vessel;
- **juxtapleural:** merged with the chest wall or mediastinal pleura.

The class drives B's phenotype rules (e.g. no ground-glass at the pleura; juxtavascular → lobulated more likely), E's growth constraints and F's insertion (clip juxtapleural lesions with the lung mask).

**Source gap (important).** The target was listed as "SYN-LUNGS placement logic" [A01]. Dissection found that the A01 PDF (arXiv:2502.21187v4, *Virtual Patients, Real Gains*) contains **no placement rules, class definitions, thresholds or class proportions**. What it does say:
- X-Lesions inserts 512 nodules (4–30 mm, sizes from NLST) into 174 XCAT digital twins, at 0.1 mm voxels with CLB texture.
- Its only LIDC link is LUNA16 (601 scans / 1,186 nodules).

The operational rule therefore comes from **Ambrosini et al. [F01]**, which defines the three classes for nodule simulation and cites **Kostis et al.** (200 nodules) for their proportions. A01 contributes only the size range and the "anatomy-aware insertion" framing.

**Pipeline.** Everything is re-implemented here, and every step is 3-D on the native host grid:
1. LIDC host CT.
2. lungmask [A03]: lungs (R231) + lobes (LTRCLobes fused with R231).
3. TotalSegmentator [A04] task `lung_vessels`: vessels + airway.
4. Euclidean distance maps.
5. Large-vessel bifurcation points.
6. Placement class of a nodule-sized sphere at each voxel.
7. Seeded candidate sites per class, each with its context vector.

## Equations

The contact ring of a nodule mask *N* (6-connected dilation δ₆, one step):

```text
R(N) = δ₆(N) \ N
```

The class of an annotated nodule (reproduction, `classes.classify_mask`). Precedence is pleura > vessel > free, so the classes are mutually exclusive:

```text
out        = ¬(Lungs ∪ N ∪ Airway)
f_pleura   = |R ∩ out| / |R|          juxtapleural   if f_pleura ≥ 0.10
n_vessel   = |R ∩ V|  (V without N)   juxtavascular  elif n_vessel ≥ 5
                                      free           otherwise
```

The class of a planned sphere of radius *r* centred at voxel *x* (placement, `classes.classify_site_arrays`). All distances are Euclidean in mm: `d_P` = EDT inside Lungs to the lung boundary, `d_V` = EDT to vessels, `d_B` = EDT to large-vessel bifurcations, `m` = margin.

```text
juxtapleural   0 < d_P(x) ≤ r
juxtavascular  d_P(x) > r + m  ∧  0 < d_V(x) ≤ r  ∧  d_B(x) ≤ r
free           d_P(x) > r + m  ∧  d_V(x) > r + m
(otherwise ambiguous → never emitted)
```

Bifurcations: skeleton voxels *s* of the vessel mask with ≥ 3 skeleton neighbours (26-connectivity) and a local vessel radius of at least 1.5 mm (EDT inside the vessel at *s*).

Wilson 95 % interval for a class proportion k/n, with z = 1.96:

```text
centre = (p + z²/2n) / (1 + z²/n),   half = z·√(p(1−p)/n + z²/4n²) / (1 + z²/n)
```

## Parameters

The class thresholds were fixed **before** the reproduction run (plan Q5) and are never fitted to Kostis. The code source is `src/classes.py`.

| Parameter | Value | Source / reason |
|---|---|---|
| Contact ring | 1 voxel, 6-connected | F01 "no voxel overlap" / "share voxels": contact is voxel adjacency |
| `pleura_contact_frac` | 0.10 | F01 "merged with lung contour"; a tangent touch is not enough (pre-registered) |
| `vessel_contact_vox` | 5 | F01 "share voxels with vessel"; guards single-voxel segmentation noise (pre-registered) |
| `min_vessel_radius_mm` | 1.5 | F01 "large vessel" (pre-registered) |
| Site margin *m* | 3 mm | clearance band between contact and free (pre-registered) |
| Consensus | pylidc `consensus(clevel=0.5)`, ≥ 3 of 4 readers, mean diameter ≥ 3 mm | LIDC [A02] outlines nodules ≥ 3 mm |
| Nominal radius *r* | median consensus radius of the reproduction set | plan Q8; stored per site in `context.extra.nominal_radius_mm` |
| Vessel density | vessel-voxel fraction in a 10 mm sphere | `context.extra.vessel_density` (B's "vessel density" context) |
| Local HU | mean/std over a sphere of radius *r*, vessel voxels excluded | contract `local_hu_mean/std` |
| Sites per class | 10 (equal counts) | plan Q7; the class prior belongs to B's rulebook |
| Kostis reference | vascularized 0.45 · free 0.33 · juxtapleural 0.22 | F01 citing Kostis: "almost half … around one-third … approaching one-quarter" |
| Pass criterion | each class within ±10 pp **and** the ordering vasc > free > juxtapleural | plan Q3 |

**Tools (versions pinned in each cache `meta.json`):**
- lungmask 0.2.22 (Apache-2.0);
- TotalSegmentator 2.18.0 (Apache-2.0; task `lung_vessels` needs no licence key);
- pylidc 0.2.3 (MIT);
- tcia_utils 3.3.5 (Apache-2.0).

LIDC-IDRI comes from TCIA (CC BY 3.0).

## Paper's claimed result

The reproduction target is Ambrosini et al. [F01], citing Kostis et al. (200 pulmonary nodules): "almost half of all nodules were vascularized, around one-third had well-circumscribed boundaries, and approaching one-quarter of all nodules were juxtapleural". A fourth class, pleural tails, is about 1 %. We merge it into juxtapleural and do not model it separately.

The figures are qualitative fractions, so the numeric reference 0.45 / 0.33 / 0.22 is our reading of them (plan Q3).

## Our reproduction (number + figure)

**The result is not matched, and it is inconclusive at n = 9 nodules.**
- **Run:** `A_placement/runs/20261029-122412-repro-proportions/` (gitignored), command `python -m A_placement.repro.class_proportions --limit 6 --workers 1`.
- **Figure:** [`../figures/18-class-proportions.png`](../figures/18-class-proportions.png).

| Class | Ours (n=9) | 95 % Wilson CI | Kostis via F01 | Within ±10 pp |
|---|---|---|---|---|
| free (well-circumscribed) | 5 · 0.56 | 0.27–0.81 | 0.33 | no |
| juxtavascular (vascularized) | 4 · 0.44 | 0.19–0.73 | 0.45 | yes |
| juxtapleural | 0 · 0.00 | 0.00–0.30 | 0.22 | no |

The ordering vasc > free > juxtapleural fails. The median consensus radius is **4.72 mm**, which becomes `nominal_radius_mm` for placement.

**Sample.** The plan called for 40 scans, later amended to 20. CPU segmentation took about 25 min per scan alone, and up to 75 min while other sessions loaded the machine. The developer stopped the run after 6 scans (LIDC-IDRI-0001, 0003–0007), with the goal of validating the working pipeline rather than the statistics. The full 20-scan list holds 44 eligible nodules, whose CI half-width would be about ±13–14 pp.

**Diagnostic (not used to tune anything).** Distance from each nodule to the nearest non-lung, non-airway voxel:

| Nodule | Diameter mm | Class | Gap to wall mm | Ring fraction outside lung |
|---|---|---|---|---|
| 0001-1 | 32.8 | juxtavascular | 1.41 | 0.000 |
| 0003-1 | 31.0 | juxtavascular | 15.87 | 0.000 |
| 0003-2 | 13.3 | free | 2.32 | 0.000 |
| 0003-3 | 15.0 | free | **0.82** | 0.035 |
| 0004-1 | 6.8 | free | 8.74 | 0.000 |
| 0005-1 | 5.7 | free | 5.19 | 0.000 |
| 0005-2 | 7.9 | free | 6.84 | 0.000 |
| 0006-1 | 8.8 | juxtavascular | 11.49 | 0.000 |
| 0007-1 | 34.4 | juxtavascular | 2.50 | 0.002 |

Four of nine nodules lie within 2.5 mm of the lung wall, yet none passes the pre-registered rule (one-voxel contact, at least 10 % of the ring outside the lung). Two causes:
- **Mask boundary:** R231's lung mask includes a thin rim of wall-side tissue, so a nodule that touches the pleura radiologically still sees "lung" in its ring.
- **Consensus shrinkage:** the 50 % consensus outline shrinks the nodule border slightly.

**Consequence for downstream:** the rule as fixed **undercounts juxtapleural** nodules on real annotations. Placement of *planned* spheres uses distances, not this ring: juxtapleural sites satisfy `d_P ≤ r` and do sit against the wall (see the site figure). So A's candidate sites are usable, but the measured class prior is biased.

**Candidate fix (needs a new, pre-registered run, not done here):** contact = "gap to the lung boundary ≤ 1 in-plane voxel *or* ring fraction ≥ 0.10", evaluated on the full 20-scan set.

## Adaptation

- **Lungs, 3-D, native grid:**
  - every mask and distance map is computed on the host's own DICOM grid (LPS, no resampling);
  - 2-D images exist only as the exported figures.
- **TotalSegmentator 2.18 class split:** task `lung_vessels` no longer emits `lung_vessels` / `lung_trachea_bronchia`. It emits `lung_arteries`, `lung_veins`, `lung_airways` and `lung_airways_wall`. We use vessels = arteries ∪ veins and airway = airway lumen ∪ airway wall. The wall counts as airway, so it never counts as "outside the lung" or as an eligible site.
- **lungmask excludes juxtapleural nodules from `lungs`.** R231 often carves a large wall-adjacent nodule out of the lung mask (seen on LIDC-IDRI-0001). The nodule rule therefore uses `Lungs ∪ N`, so the nodule's own carve-out is not mistaken for chest wall.
- **Nodule hygiene (AC-5):**
  - consensus nodules, dilated by 2 voxels, are removed from the delivered `vessels` mask, because TotalSegmentator labels nodule borders as vessel;
  - no candidate site lies within 2r of a known nodule;
  - the reproduction uses the raw vessel mask minus the nodule's own voxels, because a contact ring needs the vessel voxels right next to the nodule.
- **From real nodules to planned sites:** a sphere of radius *r* inherits the same three contact definitions through distance maps. Juxtavascular additionally requires a large-vessel bifurcation within *r* (F01: inserted "at a large vessel bifurcation").
- **Determinism:** sites are drawn with `shared.seedhash.rng(seed_hex, "A.place.<class>")`, keeping at least 2r between sites. The same seed gives the same `sites.json`.
- **Speed:** CPU only, about 25 min per scan (TotalSegmentator dominates). The reproduction set is therefore the first 20 patients of a deterministic LIDC list, segmented 3 at a time (plan Q2 amendment).

## Verdict

**State: `dissected` (the pipeline is built and validated; the published number is not matched).**

- **Pipeline: works, verified by hand.** On LIDC-IDRI-0001 and 0004 the whole chain runs and checks out:
  - DICOM → LPS host CT on the native grid → contract-valid `anatomy_masks`, with the 5 lobes, sides and orientation checked;
  - LIDC consensus outlines land exactly on the nodules;
  - nodules are removed from vessels (61 → 0 voxels);
  - placement emits 10/10/10 contract-valid sites;
  - recomputed distances match by brute force (S001 15.88, S013 11.22, S026 2.89 mm);
  - every site re-checks to its class;
  - the same seed gives identical `sites.json` and a different seed gives different sites;
  - bifurcation points sit on visible branchings.
- **Reproduction: not matched (n = 9, inconclusive).** Juxtavascular agrees (0.44 vs 0.45), but juxtapleural is 0 vs 0.22 because of the contact-rule undercount above.

The epic defines `reproduced` as "published number matched", so the target stays at `dissected` with the attempt recorded. It moves to `reproduced`/`adapted` after a pre-registered rerun on the 20-scan set with the candidate fix, or when INT accepts the miss.

**Claim level:** classical stage, no quantum claim.

## What to reuse next

- **B:** read `sites[].context`. The placement class plus `extra.vessel_density` and `extra.dist_bifurcation_mm` are the conditioning variables. The LIDC class proportions in `proportions.json` are a candidate prior for B's rulebook, cited as Kostis/F01, with our measured value alongside.
- **E:** constrain growth with `lungs`/`lobes` (pleura and fissures) and `vessels`/`airway` from the same `anatomy_masks.json`.
- **F:** juxtapleural sites must be clipped by the lung mask at insertion. `local_hu_mean/std` is the host background for additive-delta insertion.
- **INT:** use the final `place` run directory, which is self-contained: masks, `anatomy_masks.json`, `sites.json` and `run.json`. If B draws a size very different from `nominal_radius_mm`, re-check the class with `classes.classify_site`.
