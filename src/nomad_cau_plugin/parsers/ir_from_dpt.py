"""Parser for infrared spectroscopy .dpt files."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class IRSpectrum:
    """Container for IR spectrum data."""

    wavenumber: list[float]
    transmittance: list[float]


def _decode_text_bytes(file_bytes: bytes) -> str:
    """Decode bytes to text, trying UTF-8 first, then latin-1."""
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1')


def _spectrum_from_dataframe(df_local: pd.DataFrame) -> IRSpectrum:
    """Create IRSpectrum from a DataFrame with wavenumber and transmittance columns."""
    return IRSpectrum(
        wavenumber=[float(x) for x in df_local['wavenumber']],
        transmittance=[float(y) for y in df_local['transmittance']],
    )


def ir_spectrum_from_dpt_bytes(dpt_bytes: bytes) -> IRSpectrum:
    """
    Parse a .dpt infrared spectroscopy file as (wavenumber, transmittance).

    The .dpt format is a two-column text file where:
    - Column 1: wavenumber in cm⁻¹
    - Column 2: transmittance (typically 0-1 or 0-100%)

    Args:
        dpt_bytes: Raw .dpt file content as bytes.

    Returns:
        IRSpectrum: (wavenumber, transmittance) data.

    Raises:
        ValueError: If the file cannot be parsed as valid IR data.
    """
    dpt_text = _decode_text_bytes(dpt_bytes)
    try:
        df_local = pd.read_csv(
            io.StringIO(dpt_text),
            sep=r'[\s\t]+',
            comment='#',
            header=None,
            names=['wavenumber', 'transmittance'],
            usecols=[0, 1],
            engine='python',
        )
    except Exception as exc:
        raise ValueError(f'Failed to parse .dpt file: {exc}') from exc

    df_local['wavenumber'] = pd.to_numeric(df_local['wavenumber'], errors='coerce')
    df_local['transmittance'] = pd.to_numeric(
        df_local['transmittance'], errors='coerce'
    )
    df_local = df_local.dropna(subset=['wavenumber', 'transmittance'])

    if df_local.empty:
        raise ValueError('No valid wavenumber/transmittance data found in .dpt file')

    # Sort by wavenumber in descending order (typical IR format)
    df_local = df_local.sort_values('wavenumber', ascending=False).reset_index(
        drop=True
    )

    return _spectrum_from_dataframe(df_local)
