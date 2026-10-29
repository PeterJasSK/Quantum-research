# #11 — Pixel2Cancer + Kansal–Torquato layers

**Letter:** E ([`E_classical_growth`](../README.md)) · **Priority:** ★★★ · **Kind:** classical · **Papers:** E01, E02 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Two published cellular automata, rebuilt from the papers and combined:

- **Kansal–Torquato 2000 [E02]** (idealised glioblastoma). This gives the tumor its **internal structure**. The tumor has three layers:
  - a proliferating rim;
  - a non-proliferative (G0, "dormant") shell;
  - a necrotic core.

  The layer thicknesses scale with the tumor radius as Rt^(2/3), a surface-to-volume (nutrient-diffusion) law. Four microscopic parameters (p0, a, b, Rmax) reproduce Gompertzian growth over three orders of magnitude in radius. The lattice is a variable-density Voronoi/Delaunay lattice, dense at the centre and coarse at the edge, chosen to avoid cubic-lattice artefacts.
- **Pixel2Cancer 2024 [E01]** (liver, pancreas, kidney tumors in real CT). This gives the tumor its **interaction with the organ**:
  - the organ's HU is quantified into tissue levels;
  - vessels and the organ boundary are level-0 barriers;
  - three generic rules apply: R1 growth, R2 invasion, R3 death.

  Crowded cells exert *pressure* on barriers, and a barrier gives way only after a threshold number of pushes. That is how tumors are compressed by, and wrap around, vessels and boundaries.

Our lung engine keeps the Kansal–Torquato layer dynamics, uses Pixel2Cancer's barrier pressure and tissue levels for the anatomy, and adds lung-specific barriers:
- the pleura and fissures are hard barriers that are never crossed;
- vessels and airways are soft, pressure-threshold barriers.

## Equations

Kansal–Torquato [E02] §3 (eqs. 2–6). One time step = one day:

```text
z(r)  = r^(2/3) / 6            mean site spacing at radius r (mm)                         (2)
Rt    = Σ r_i / N_P            mean radius of the tumor-edge cells                         (3)
dn    = a · Rt^(2/3)           dormant cells deeper than dn below the edge → necrotic       (4)
pd    = p0 · (1 − r / Rmax)    probability that a proliferating cell attempts to divide     (5)
dp    = b · Rt^(2/3)           a dividing cell takes the nearest free site within dp;       (6)
                               none found → the cell becomes non-proliferative
growth fraction   = proliferating / tumor (volume-weighted, weight = z(r)³)
necrotic fraction = necrotic / tumor
doubling time     = ln2 · Δt / ln(V(t+Δt/2) / V(t−Δt/2)),  V = 4/3·π·Rt³,  Δt = 10 d
```

Pixel2Cancer [E01] §2.1–2.2 and reference code (`utils.py`, `cellular.cu`):

```text
quantify:  interval = (hi − lo)/3;  level 1: HU < lo+interval;  2: < lo+2·interval;  3: < hi;
           level 0 (barrier): HU ≥ hi or outside the organ mask
state s ∈ {−1 dead, 0, 1…10};  kernel 3×3×3
R1  1 ≤ s < 10                → s + 1
R2  s ≥ 5: up to 3 random kernel targets, one success
      barrier & s = 10:  pressure ≥ 3 → barrier becomes level-1 tissue;  else pressure + 1
      tissue level L:    accepted with probability (1, 0.3, 0.1)[L]; target s < 10 → target + 1
R3  after the growth loop, if steps > tumor-size steps (liver 50) and a fair coin:
      start points + random s = 10 cells nearby → −1; −1 spreads into s = 10 neighbours, steps/7 + 1 times
```

Lung engine (ours, `src/engine.py`), per day on the cubic lattice:

```text
Rt from the edge voxels about the seed centroid;  dn = a·Rt^(2/3);  dp = max(b·Rt^(2/3), √3·Δ)
depth(v) = Euclidean distance to the tumor surface;  dormant & depth > dn → necrotic
every dormant cell pushes one random 26-neighbour; soft barrier with pressure ≥ vessel_threshold → entered
proliferating cell: with pd = p0(1 − r/Rmax) take the nearest free parenchyma voxel within dp
   (distances on a jittered lattice: each voxel site offset by U(−0.4, 0.4)·Δ per axis),
   accepted with rate[level];  none → dormant
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| p0 (KT) | 0.192 d⁻¹ | [E02] §4 |
| a (KT) | 0.42 mm^(1/3) | [E02] §4 |
| b (KT) | 0.11 mm^(1/3) | [E02] §4 |
| Rmax (KT) | 37.5 mm | [E02] §4 |
| initial radius (KT) | 0.1 mm | [E02] Table 2 footnote |
| lattice sites (KT) | 1.5 × 10⁶ | [E02] §2 |
| Organ_HU liver / pancreas / kidney | [100, 160] / [100, 160] / [140, 200] | Pixel2Cancer `tumor_synthesis.py` |
| max steps liver / pancreas / kidney | 150 / 80 / 80 | Pixel2Cancer `tumor_synthesis.py` |
| death size steps liver / pancreas / kidney | 50 / 30 / 30 | Pixel2Cancer `utils.py` `Tumor_size` |
| threshold (full population) | 10 | Pixel2Cancer `tumor_synthesis.py` |
| barrier pressure | 3 pushes, invaded at the 4th | Pixel2Cancer `cellular.cu` (`> outrange + 2`) |
| tissue rates per level | 1, 0.3, 0.1 | Pixel2Cancer `cellular.cu` `check_tissue` |
| grow_per_cell / max_try | 1 / 3 | Pixel2Cancer `cellular.py` |
| lung p0 solid / part-solid / ground-glass | 0.00947 / 0.00292 / 0.00150 d⁻¹ | calibrated (`repro/calibrate_lung.py`) |
| lung VDT targets | 149 / 457 / 813 d | Hasegawa et al., Br J Radiol 2000 *(verify; PDF not in `papers/`)* |
| lung a, b, Rmax | 2.2 mm^(1/3), 0.11 mm^(1/3), 50 mm | a: necrosis only above 20 mm (assumption); b: [E02]; Rmax: assumption |
| lung vessel_threshold | 30 pushes | assumption |
| lung parenchyma rates (levels 1–4) | 1, 0.3, 0.1, 0.05 | [E01] levels 1–3; level 4 assumption |
| lung HU bounds | [−950, −600] | assumption (plan Q5) |
| lattice | 0.5 mm isotropic, jitter 0.8 Δ | plan Q4; jitter: ours |

All lung values live in [`../src/params_lung.json`](../src/params_lung.json).

## Paper's claimed result

- **[E02] Table 2.** Simulated vs literature values of growth fraction, necrotic fraction, volumetric doubling time and time-to-radius, at the four clinical stages Rt = 0.5 mm (spheroid), 5 mm (detectable lesion), 18.5 mm (diagnosis) and 25 mm (death). Simulated growth fraction 40 / 30 / 19 / 13 %, necrotic fraction 38 / 45 / 57 / 60 %, doubling time 5 / 38 / 72 / 112 d, days 87 / 198 / 405 / 492. **This is the number we reproduce.**
- **[E01].** No growth number is published. The quantitative results are segmentation scores (liver DSC 59.8 %, pancreas 60.9 %, kidney 73.2 %; Table 2) and a 150-image Visual Turing Test (Table 1). Both need trained U-Nets and radiologists, so they cannot be rerun here. The *behaviours* the paper describes in §2.2 and Fig. 2 are reproduced instead (plan Q1):
  - compression by and wrapping of vessels;
  - flattening at the organ boundary;
  - death only above the size rule;
  - size controlled by the step count.

## Our reproduction (number + figure)

**Kansal–Torquato Table 2** (`python -m E_classical_growth.repro.kt_table2`; run `20261028-191231-kt-table2`). The lattice has 1,851,791 sites (spacing law scaled by k = 0.29 to the paper's reported ~1.5 × 10⁶ sites), 15.2 mean neighbours, out to 30 mm.

| Rt (mm) | day: Sim / ours | growth fraction: Data / Sim / ours | necrotic fraction: Data / Sim / ours | doubling time (d): Data / Sim / ours | within tolerance |
|---|---|---|---|---|---|
| 0.5 | 87 / 61 | 0.36 / 0.40 / **0.50** | 0.46 / 0.38 / **0.08** | 6 / 5 / **10.5** | no |
| 5 | 198 / 227 | 0.30 / 0.30 / **0.29** | 0.49 / 0.45 / **0.36** | 45 / 38 / **25.7** | yes |
| 18.5 | 405 / 449 | 0.20 / 0.19 / **0.20** | 0.55 / 0.57 / **0.54** | 70 / 72 / **64.8** | yes |
| 25 | 492 / 555 | 0.09 / 0.13 / **0.19** | 0.60 / 0.60 / **0.58** | 105 / 112 / **105.1** | yes |

Tolerance (plan Q3): fractions ±10 percentage points, doubling time ±35 %, day ±25 %.
- **Three of four stages agree.** The Gompertz-like slow-down of the doubling time from tens to about 100 days and the 55–60 % necrotic fraction of a large tumor are reproduced.
- **0.5 mm does not agree.** There our tumor is still only ~10³ lattice sites around a 0.1 mm start. The dn = a·Rt^(2/3) rule gives a thin necrotic core by construction, so necrosis is not yet established. The paper's early phase also depends on details of its initial lattice that it does not publish.

Figures: [`kt_table2.png`](../figures/kt_table2.png), [`kt_growth_curve.png`](../figures/kt_growth_curve.png) (Fig. 4 analogue), [`kt_cross_sections.png`](../figures/kt_cross_sections.png) (Fig. 3 analogue).

**Lattice resolution matters.** With the literal eq. 2 spacing (k = 1, 47,037 sites to 50 mm; run `20261029-052947-kt-table2-k1`), every stage fails: day 178 vs 492 at 25 mm, growth fraction 0.45 vs 0.13. Each automaton cell is then too large, so divisions add too much volume and the proliferating rim is many cells thick. The figures are kept as [`kt_table2_k1.png`](../figures/kt_table2_k1.png), [`kt_growth_curve_k1.png`](../figures/kt_growth_curve_k1.png) and [`kt_cross_sections_k1.png`](../figures/kt_cross_sections_k1.png). The paper's statement of 1.5 × 10⁶ sites is therefore the operative parameter, and eq. 2 is only the radial shape of the density.

**Pixel2Cancer behaviours** (`python -m E_classical_growth.repro.p2c_behaviour`; synthetic liver phantom, 96³ mm at 1 mm, liver hyper-parameters; run id in the [README](../README.md)):

| Check | Result |
|---|---|
| B1 vessel | PASS: first contact at step 19; vessel voxels are invaded only at ≥ 3 pushes (minimum observed 3 = threshold); 764 of 2180 vessel voxels entered by step 90; tumor present in 12/12 angular sectors around the vessel |
| B2 boundary | PASS: extent toward the boundary 6 mm vs 16 mm away (ratio 0.375); 2400 voxels pushed past the boundary are removed by the organ mask (reference behaviour), 0 remain |
| B3 death | PASS: 0 dead cells in all runs with steps ≤ 50; 2 of 6 runs with steps > 50 have a dead core (the coin flip fired in exactly those 2), dead cells nearer the start than the tumor mean |
| B4 sizes | PASS: equivalent diameter 4.8–57.3 mm over steps 14–149, Spearman ρ = 1.0 (size is a monotone function of steps) |

Figure: [`p2c_behaviour.png`](../figures/p2c_behaviour.png).

Differences from the reference code, found while reading it:
1. `curand_init(clock64(), …)` makes every reference run non-reproducible. We use a seeded `numpy.random.Generator`.
2. `check_tissue()` takes its uniform draw as an `int` parameter, so the float in [0, 1) is truncated to 0. The reference therefore accepts every tissue level with probability 1, despite the coded 0.3 / 0.1. We apply the coded rates; `P2C(faithful_int_cast=True)` reproduces the reference behaviour.
3. The CUDA kernel updates in place with atomics, so the result depends on thread order. Our step is synchronous: the tries of one round are drawn together and increments go through `np.add.at`.
4. The original cannot be run here (CUDA + torch, no GPU), so there is no differential comparison against it.

## Adaptation

Lung engine `src/` (`python -m E_classical_growth.src.grow`):
- **3-D, contract-only I/O.** Reads `anatomy_masks`, `site_candidates`, `tumor_draw`, `certificate` and `seed_shape`, each validated first. Writes `growth_trajectory` (0.5 mm lattice, states 0–3, a baseline when the tumor reaches `tumor_draw.size_mm` and a follow-up 90 days later).
- **Certificate gate.** If the certificate's status is not `pass`, the draw is rejected and logged, the run exits with code 2, and no trajectory is written.
- **Seed chain.** Every random choice comes from `shared.seedhash.rng(certificate seed, "E/engine/<draw>/<site>")`. Identical inputs give byte-identical lattices.
- **Lung barriers.** The site's lung and lobe are free. Another lobe or outside the lung is a hard barrier, so juxtapleural tumors flatten against the pleura and the fissure. Vessels and airways are soft barriers: a tumor in contact with a vessel wraps around it and enters it only after `vessel_threshold` pushes from crowded (dormant) cells. Parenchyma HU gives Pixel2Cancer tissue levels.
- **Lung parameters per type.** `p0` is calibrated so the simulated VDT at 8 mm matches 149 / 457 / 813 d for solid / part-solid / ground-glass. Achieved: 147.6 / 465.8 / 825.4 d (run `20261029-052808-calibrate-lung`, [`lung_calibration.png`](../figures/lung_calibration.png)). `a` keeps necrosis out below 20 mm.
- **Isotropy.** On a cubic lattice, nearest-first division favours face neighbours and grows an octahedron, while random order grows a rough Eden cluster. A fixed sub-voxel jitter per voxel (a jittered lattice, the cubic analogue of KT's Voronoi lattice) gives a compact, isotropic tumor: S001 inertia ratio 0.87. Raw sphericity stays ~0.72 because of 0.5 mm surface roughness. After a 0.5 mm Gaussian smooth, which is below CT resolution, it is 0.89.

Placement classes on the stub phantom (runs `20261029-052830-grow-S001`, `-052837-grow-S002`, `-052843-grow-S003`; [`lung_S001.png`](../figures/lung_S001.png), [`lung_S002.png`](../figures/lung_S002.png), [`lung_S003.png`](../figures/lung_S003.png), [`lung_growth_curves.png`](../figures/lung_growth_curves.png)):

| Site | Class | Baseline / follow-up | Shape checks |
|---|---|---|---|
| S001 | free | day 428, 8.01 mm → day 518, 9.14 mm | sphericity 0.89 (smoothed), inertia ratio 0.87 |
| S002 | juxtavascular | day 448 → 538, 9.08 mm | contact from day 253; within 90 d no vessel entry. A 600-day follow-up run (`20261029-052850-grow-S002`) enters the vessel on day 629, only after the 30-push threshold |
| S003 | juxtapleural | day 540 → 630, 8.80 mm | 0 voxels outside the lung; flattened against the pleura and the LUL/LLL fissure (inertia ratio 0.43) |

## Verdict

**adapted.** Kansal–Torquato is reproduced (Table 2, three of four stages within tolerance at the paper's site count). Pixel2Cancer is reproduced as behaviour (B1–B4 pass). Both are combined into a working, contract-valid, deterministic 3-D lung engine running on stubs. `integrated` follows in INT with real A / C / D inputs.

Claim level: classical stage (n/a). The certified seed gives provenance only and does not make growth more realistic.

## What to reuse next

- **F (render):**
  - read `growth_trajectory` (states 0–3 on a 0.5 mm lattice placed by `origin_mm_lps`);
  - `growth_summary.json` next to it has per-snapshot diameter, volume and layer fractions;
  - `environment.npz` holds the barrier and tissue-level maps.

  Pixel2Cancer's mapping step ([E01] §2.3: population → HU blend, 3-D Gaussian texture) belongs to F (#13/#14). The partial-population field is filed as contract change request 2.
- **H (analysis):** use `growth_summary.json` `per_day` for VDT, layer fractions and barrier contacts against LIDC follow-up pairs.
- **INT:** swap the stubs for real A masks (lungs, lobes, vessels, airway on LIDC), C's seed and D's seed shape. Revisit `lung_hu_bounds` and `vessel_threshold` on real scans, and add the Hasegawa 2000 PDF to confirm the VDT targets.
- Code: `src/kt.py` (KT on any graph, plus the layer laws), `src/p2c.py` (Pixel2Cancer CPU port, deterministic), `src/engine.py` (combined lung rule), `src/lattice.py` (host → lattice resampling and barriers).
