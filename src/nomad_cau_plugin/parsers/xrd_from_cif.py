from __future__ import annotations

import io
import os
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class XRDPattern:
    two_theta: list[float]
    intensity: list[float]


def _decode_text_bytes(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1')


def _pattern_from_dataframe(df_local: pd.DataFrame) -> XRDPattern:
    return XRDPattern(
        two_theta=[float(x) for x in df_local['two_theta']],
        intensity=[float(y) for y in df_local['intensity']],
    )


def _pattern_from_structure(
    structure,
    *,
    wavelength: str | float | None = None,
    two_theta_range: tuple[float, float] | None = None,
) -> XRDPattern:
    from pymatgen.analysis.diffraction.xrd import XRDCalculator  # noqa: PLC0415, I001

    xrd = XRDCalculator(wavelength=wavelength) if wavelength else XRDCalculator()
    pattern = xrd.get_pattern(structure, two_theta_range=two_theta_range or (0, 90))

    return XRDPattern(
        two_theta=[float(x) for x in pattern.x],
        intensity=[float(y) for y in pattern.y],
    )


def xrd_pattern_from_cif_bytes(
    cif_bytes: bytes,
    *,
    wavelength: str | float | None = None,
    two_theta_range: tuple[float, float] | None = None,
) -> XRDPattern:
    """Compute an XRD powder pattern from a CIF file.

    This uses pymatgen's :class:`~pymatgen.analysis.diffraction.xrd.XRDCalculator`
    and returns a 2θ grid with corresponding relative intensities.

    Args:
        cif_bytes: Raw CIF file content.
        wavelength: Optional pymatgen wavelength (in Angstrom) or identifier.
            If ``None``, pymatgen defaults are used (typically Cu Kα).

    Returns:
        XRDPattern: (two_theta, intensity)

    Raises:
        ImportError: If pymatgen is not installed.
        ValueError: If the CIF content cannot be parsed.
    """

    try:
        from pymatgen.io.cif import CifParser  # noqa: PLC0415, I001
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'Missing dependency for CIF→XRD conversion. Install `pymatgen`.'
        ) from exc

    cif_text = _decode_text_bytes(cif_bytes)

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

    return _pattern_from_structure(
        structure,
        wavelength=wavelength,
        two_theta_range=two_theta_range,
    )


def xrd_pattern_from_xy_bytes(xy_bytes: bytes) -> XRDPattern:
    """Parse a two-column .xy/.xyd file as (two_theta, intensity)."""

    xy_text = _decode_text_bytes(xy_bytes)
    df_local = pd.read_csv(
        io.StringIO(xy_text),
        sep=r'[\s,]+',
        comment='#',
        header=None,
        names=['two_theta', 'intensity'],
        usecols=[0, 1],
        engine='python',
    )
    df_local['two_theta'] = pd.to_numeric(df_local['two_theta'], errors='coerce')
    df_local['intensity'] = pd.to_numeric(df_local['intensity'], errors='coerce')
    df_local = df_local.dropna(subset=['two_theta', 'intensity'])
    return _pattern_from_dataframe(df_local)


def xrd_pattern_from_vasp_bytes(
    vasp_bytes: bytes,
    *,
    wavelength: str | float | None = None,
    two_theta_range: tuple[float, float] | None = None,
) -> XRDPattern:
    """Compute an XRD powder pattern from a VASP structure file."""

    try:
        from pymatgen.io.vasp import Poscar  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'Missing dependency for VASP→XRD conversion. Install `pymatgen`.'
        ) from exc

    vasp_text = _decode_text_bytes(vasp_bytes)
    structure = Poscar.from_str(vasp_text).structure
    return _pattern_from_structure(
        structure,
        wavelength=wavelength,
        two_theta_range=two_theta_range,
    )


def xrd_pattern_from_reference_file_bytes(
    file_path: str,
    file_bytes: bytes,
    *,
    wavelength: str | float | None = None,
    two_theta_range: tuple[float, float] | None = None,
) -> XRDPattern:
    """Dispatch reference file parsing based on file extension."""

    suffix = os.path.splitext(file_path)[1].lower()
    if suffix in {'.xy', '.xyd'}:
        return xrd_pattern_from_xy_bytes(file_bytes)
    if suffix == '.vasp':
        return xrd_pattern_from_vasp_bytes(
            file_bytes,
            wavelength=wavelength,
            two_theta_range=two_theta_range,
        )
    if suffix == '.cif':
        return xrd_pattern_from_cif_bytes(
            file_bytes,
            wavelength=wavelength,
            two_theta_range=two_theta_range,
        )

    raise ValueError(f'Unsupported reference file format: {suffix or file_path}')
