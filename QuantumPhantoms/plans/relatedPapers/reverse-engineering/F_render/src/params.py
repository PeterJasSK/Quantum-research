"""Every tunable of the F render in one place. `asdict(RenderParams())` is written verbatim into
`hybrid_volume.insertion.params`, so a receipt can replay the exact render.

Defaults: SyntheticTumors [H01] Table 1 where a value transfers from liver to lung; plan §4 otherwise.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RenderParams:
    method: str = "image-domain additive delta v1"
    supersample: int = 4                      # sub-voxels per host axis; box-integrated (partial volume)
    # [H01] texture: N(µ, σ) noise, cubic up-scaling by η ~ U(1.1, 1.5), Gaussian blur σb = 0.6 (voxels)
    texture_eta_range: tuple[float, float] = (1.1, 1.5)
    texture_sigma_b_vox: float = 0.6
    # [H01] elastic outline deformation (σe not tabulated in H01: chosen small for E-grown lattices)
    deform_alpha_mm: float = 0.5
    deform_sigma_mm: float = 3.0
    # margin = lobulated: spherical-harmonic radial perturbation drawn from the library power spectrum
    lobulation_lmax: int = 4
    # margin = spiculated: thin tapered radial spicules ([F01]/analysis §4 item 1)
    spicule_count: int = 10
    spicule_length_mm: float = 6.0
    spicule_width_mm: float = 0.6
    # [H01] eq. 5 mass effect (local scaling warp), γmax = 1.3 r, I = 30; applied to the noise-free anatomy only
    mass_effect: bool = True
    mass_effect_intensity: float = 30.0
    mass_effect_gamma_factor: float = 1.3
    # [H01] eq. 6–8 capsule; off for lungs (no capsule in lung nodules), kept for the liver reproduction
    capsule: bool = False
    capsule_bounds: tuple[float, float] = (0.4, 0.7)
    capsule_sigma_d_vox: float = 0.8
    capsule_d_hu: float = 120.0
    # composition
    ggo_alpha: float = 1.0                    # ground-glass: additive α-blend (vessels keep their contrast)
    part_solid_core_fraction: float = 0.5     # part-solid: cells deeper than this fraction of max depth are solid
    necrotic_offset_std: float = 1.0          # necrotic HU = type interior mean − k · library hu.std (plan Q9)
    background_kernel_mm: float = 12.0        # median-filter size for the local parenchyma background
    anatomy_sigma_vox: float = 1.0            # host smoothing that separates anatomy A from noise N
    residual_noise: bool = True               # top up lesion-interior σ to the σ map with NPS-shaped noise
    psf_sigma_mm_zyx: tuple[float, float, float] | None = None   # None = from the scanner fingerprint
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}
