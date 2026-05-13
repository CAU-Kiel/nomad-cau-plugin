"""Parser for Dynamic Light Scattering (DLS) distribution data."""

from dataclasses import dataclass

import numpy as np


@dataclass
class DLSDistribution:
    """Container for DLS distribution data."""

    diameter: list[float]
    differential: list[float]
    cumulative: list[float]
    cumulant_diameter: float
    polydispersity_index: float
    d10: float
    d50: float
    d90: float
    distribution_type: str  # 'Intensity', 'Volume', or 'Number'


def _decode_text_bytes(file_bytes: bytes) -> str:
    """Decode file bytes handling UTF-16 LE with fallback to UTF-8."""
    try:
        # Try UTF-16 LE first (standard for DLS .xls files)
        return file_bytes.decode('utf-16-le')
    except (UnicodeDecodeError, UnicodeError):
        try:
            # Try UTF-8 as fallback
            return file_bytes.decode('utf-8')
        except (UnicodeDecodeError, UnicodeError):
            # Last resort: latin-1 (always succeeds)
            return file_bytes.decode('latin-1')


# Minimum number of fields expected in cumulant data line
MIN_CUMULANT_FIELDS = 5


def _parse_cumulant_section(lines: list[str]) -> dict:
    """
    Extract cumulant diameter data from the file.

    Returns dict with keys: cumulant_diameter, pi, d10, d50, d90
    """
    # Search for lines mentioning cumulant and diameter, case-insensitive.
    for i, line in enumerate(lines):
        low = line.lower()
        if 'cumulant' in low and 'diameter' in low:
            # Next non-empty line should have the data
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                data_line = lines[j].strip()
                # Split on any whitespace (tabs or spaces) and normalize decimals
                values = [v.strip().replace(',', '.') for v in data_line.split()]
                if len(values) >= MIN_CUMULANT_FIELDS:
                    try:
                        return {
                            'cumulant_diameter': float(values[0]),
                            'pi': float(values[1]),
                            'd10': float(values[2]),
                            'd50': float(values[3]),
                            'd90': float(values[4]),
                        }
                    except (ValueError, IndexError):
                        pass
    return {
        'cumulant_diameter': np.nan,
        'pi': np.nan,
        'd10': np.nan,
        'd50': np.nan,
        'd90': np.nan,
    }


# Minimum number of fields expected in distribution data line
MIN_DISTRIBUTION_FIELDS = 3


def _parse_distribution_section(
    lines: list[str], distribution_type: str
) -> tuple[list[float], list[float], list[float]]:
    """
    Extract distribution data from the file.

    Args:
        lines: List of file lines
        distribution_type: 'Intensity', 'Volume', or 'Number'

    Returns:
        Tuple of (diameter, differential, cumulative) lists
    """
    diameter = []
    differential = []
    cumulative = []

    # Find the section header.
    # Accept either an explicit "Differential {Type}" header or a table header
    # line that contains 'Diameter' and 'Differential' and optionally the type.
    start_idx = None
    dtype_lower = distribution_type.lower()
    for i, line in enumerate(lines):
        low = line.lower()
        # Explicit header like 'Differential Intensity' or 'Differential Intensity (%)'
        if 'differential' in low and dtype_lower in low:
            start_idx = i + 1
            break
        # Table header line that contains 'diameter' and 'differential'
        if 'diameter' in low and 'differential' in low:
            start_idx = i + 1
            break

    if start_idx is None:
        return [], [], []

    # Parse data rows
    for line_str in lines[start_idx:]:
        line = line_str.strip()
        if not line or line.startswith('-'):
            continue
        if 'Diameter' in line or 'Cumulant' in line or 'File' in line:
            continue

        # Split on any whitespace
        parts = line.split()
        if len(parts) >= MIN_DISTRIBUTION_FIELDS:
            try:
                # Replace comma with dot for decimal separator (European format)
                d = float(parts[0].replace(',', '.'))
                diff = float(parts[1].replace(',', '.'))
                cum = float(parts[2].replace(',', '.'))

                diameter.append(d)
                differential.append(diff)
                cumulative.append(cum)
            except (ValueError, IndexError):
                continue

    return diameter, differential, cumulative


def dls_distribution_from_xls_bytes(
    xls_bytes: bytes, distribution_type: str = 'Intensity'
) -> DLSDistribution:
    """
    Parse a DLS .xls file into a DLSDistribution object.

    The .xls file should contain:
    - Cumulant diameter section with: Cumulant Diameter, PI, D10, D50, D90
    - Distribution section with: Diameter, Differential <Type>, Cumulative <Type>

    Args:
        xls_bytes: File content as bytes
        distribution_type: Type of distribution ('Intensity', 'Volume', or 'Number')

    Returns:
        DLSDistribution object containing parsed data

    Raises:
        ValueError: If file contains no valid distribution data
    """
    if not isinstance(distribution_type, str) or distribution_type not in [
        'Intensity',
        'Volume',
        'Number',
    ]:
        raise ValueError(
            "distribution_type must be 'Intensity', 'Volume', or 'Number'"
        )

    xls_text = _decode_text_bytes(xls_bytes)

    # Split by lines
    lines = xls_text.split('\n')

    # Parse cumulant section
    cumulant_data = _parse_cumulant_section(lines)

    # Parse distribution section
    diameter, differential, cumulative = _parse_distribution_section(
        lines, distribution_type
    )

    if not diameter:
        raise ValueError(
            f'No valid {distribution_type.lower()} distribution data found in file'
        )

    return DLSDistribution(
        diameter=diameter,
        differential=differential,
        cumulative=cumulative,
        cumulant_diameter=cumulant_data['cumulant_diameter'],
        polydispersity_index=cumulant_data['pi'],
        d10=cumulant_data['d10'],
        d50=cumulant_data['d50'],
        d90=cumulant_data['d90'],
        distribution_type=distribution_type,
    )
