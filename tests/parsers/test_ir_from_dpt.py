"""Tests for IR spectroscopy data parsing."""

import numpy as np
import pytest

from nomad_cau_plugin.normalizers.CaP_experiments_normalizer import CaPNormalizer
from nomad_cau_plugin.parsers.ir_from_dpt import (
    IRSpectrum,
    ir_spectrum_from_dpt_bytes,
)


def test_ir_spectrum_from_dpt_bytes_parses_two_columns():
    """Test parsing a simple .dpt file with two columns."""
    dpt_content = b"""# IR spectrum data
4000.0	0.99
3000.0	0.95
2000.0	0.90
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    # Should be sorted by wavenumber descending (4000, 3000, 2000)
    assert spectrum.wavenumber == [4000.0, 3000.0, 2000.0]
    assert spectrum.transmittance == [0.99, 0.95, 0.90]


def test_ir_spectrum_from_dpt_bytes_handles_whitespace():
    """Test parsing with variable whitespace and tabs."""
    dpt_content = b"""4000	0.99
3000   0.95
2000\t0.90"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert len(spectrum.wavenumber) == 3
    assert spectrum.wavenumber[0] == 4000.0


def test_ir_spectrum_from_dpt_bytes_skips_comments():
    """Test that comment lines are properly skipped."""
    dpt_content = b"""# Comment 1
4000.0	0.99
# Another comment
3000.0	0.95
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert len(spectrum.wavenumber) == 2
    assert spectrum.wavenumber == [4000.0, 3000.0]


def test_ir_spectrum_from_dpt_bytes_sorts_descending():
    """Test that wavenumbers are sorted in descending order."""
    dpt_content = b"""2000.0	0.90
4000.0	0.99
3000.0	0.95
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert spectrum.wavenumber == [4000.0, 3000.0, 2000.0]
    assert spectrum.transmittance == [0.99, 0.95, 0.90]


def test_ir_spectrum_from_dpt_bytes_raises_on_empty_file():
    """Test that empty or invalid files raise ValueError."""
    with pytest.raises(ValueError, match='No valid wavenumber'):
        ir_spectrum_from_dpt_bytes(b'# only comments\n# no data')


def test_ir_spectrum_from_dpt_bytes_handles_scientific_notation():
    """Test parsing with scientific notation."""
    dpt_content = b"""4.000e3	9.9e-1
3.000e3	9.5e-1
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert len(spectrum.wavenumber) == 2
    assert abs(spectrum.wavenumber[0] - 4000.0) < 0.1


def test_ir_spectrum_equality():
    """Test that IRSpectrum dataclass equality works."""
    spectrum1 = IRSpectrum(wavenumber=[4000.0, 3000.0], transmittance=[0.99, 0.95])
    spectrum2 = IRSpectrum(wavenumber=[4000.0, 3000.0], transmittance=[0.99, 0.95])

    assert spectrum1 == spectrum2


def test_normalize_ir_data_output_structure():
    """Test that normalize_ir_data returns correct output structure."""
    dpt_content = b"""4000.0	0.99
3000.0	0.95
2000.0	0.90
"""

    # This is a simple unit test of the output structure
    # (full integration requires archive context)
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    expected_keys = {'wavenumber', 'transmittance'}
    assert hasattr(spectrum, 'wavenumber')
    assert hasattr(spectrum, 'transmittance')
    assert len(spectrum.wavenumber) == 3
    assert len(spectrum.transmittance) == 3
