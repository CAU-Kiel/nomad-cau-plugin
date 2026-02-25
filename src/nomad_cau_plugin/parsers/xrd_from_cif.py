from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class XRDPattern:
    two_theta: list[float]
    intensity: list[float]


def xrd_pattern_from_cif_bytes(
    cif_bytes: bytes,
    *,
    wavelength: str | None = None,
    two_theta_range: tuple[float, float] | None = None,
) -> XRDPattern:
    """Compute an XRD powder pattern from a CIF file.

    This uses pymatgen's :class:`~pymatgen.analysis.diffraction.xrd.XRDCalculator`
    and returns a 2θ grid with corresponding relative intensities.

    Args:
        cif_bytes: Raw CIF file content.
        wavelength: Optional pymatgen wavelength identifier. If ``None``,
            pymatgen defaults are used (typically Cu Kα).

    Returns:
        XRDPattern: (two_theta, intensity)

    Raises:
        ImportError: If pymatgen is not installed.
        ValueError: If the CIF content cannot be parsed.
    """

    try:
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        from pymatgen.io.cif import CifParser
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'Missing dependency for CIF→XRD conversion. Install `pymatgen`.'
        ) from exc

    # CIF files are text; try UTF-8 first, then latin-1.
    try:
        cif_text = cif_bytes.decode('utf-8')
    except UnicodeDecodeError:
        cif_text = cif_bytes.decode('latin-1')

    # Many CIFs (incl. CCDC exports) may contain duplicated sites / occupancies
    # that exceed 1.0; using CifParser with a relaxed tolerance is more robust.
    parser = CifParser.from_str(
        cif_text,
        occupancy_tolerance=10.0,
        check_cif=False,
    )
    structures = parser.parse_structures(primitive=False)
    if not structures:
        raise ValueError('Invalid CIF file with no structures.')
    structure = structures[0]

    xrd = XRDCalculator(wavelength=wavelength) if wavelength else XRDCalculator()
    pattern = xrd.get_pattern(structure, two_theta_range=two_theta_range or (0, 90))

    return XRDPattern(
        two_theta=[float(x) for x in pattern.x],
        intensity=[float(y) for y in pattern.y],
    )
