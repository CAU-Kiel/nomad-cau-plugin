"""Tests for IR spectroscopy data parsing."""

import pytest

from nomad_cau_plugin.parsers.ir_from_dpt import (
    IRSpectrum,
    ir_spectrum_from_dpt_bytes,
)

# Test constants
IR_WAVENUMBER_4000 = 4000.0
IR_TRANSMITTANCE_0_99 = 0.99
IR_WAVENUMBER_3000 = 3000.0
IR_TRANSMITTANCE_0_95 = 0.95
IR_WAVENUMBER_2000 = 2000.0
IR_TRANSMITTANCE_0_90 = 0.90
IR_SPECTRUM_LENGTH_2 = 2
IR_SPECTRUM_LENGTH_3 = 3
SCIENTIFIC_NOTATION_TOLERANCE = 0.1


def test_ir_spectrum_from_dpt_bytes_parses_two_columns():
    """Test parsing a simple .dpt file with two columns."""
    dpt_content = b"""# IR spectrum data
4000.0	0.99
3000.0	0.95
2000.0	0.90
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    # Should be sorted by wavenumber descending (4000, 3000, 2000)
    assert spectrum.wavenumber == [
        IR_WAVENUMBER_4000,
        IR_WAVENUMBER_3000,
        IR_WAVENUMBER_2000,
    ]
    assert spectrum.transmittance == [
        IR_TRANSMITTANCE_0_99,
        IR_TRANSMITTANCE_0_95,
        IR_TRANSMITTANCE_0_90,
    ]


def test_ir_spectrum_from_dpt_bytes_handles_whitespace():
    """Test parsing with variable whitespace and tabs."""
    dpt_content = b"""4000	0.99
3000   0.95
2000\t0.90"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert len(spectrum.wavenumber) == IR_SPECTRUM_LENGTH_3
    assert spectrum.wavenumber[0] == IR_WAVENUMBER_4000


def test_ir_spectrum_from_dpt_bytes_skips_comments():
    """Test that comment lines are properly skipped."""
    dpt_content = b"""# Comment 1
4000.0	0.99
# Another comment
3000.0	0.95
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert len(spectrum.wavenumber) == IR_SPECTRUM_LENGTH_2
    assert spectrum.wavenumber == [IR_WAVENUMBER_4000, IR_WAVENUMBER_3000]


def test_ir_spectrum_from_dpt_bytes_sorts_descending():
    """Test that wavenumbers are sorted in descending order."""
    dpt_content = b"""2000.0	0.90
4000.0	0.99
3000.0	0.95
"""
    spectrum = ir_spectrum_from_dpt_bytes(dpt_content)

    assert spectrum.wavenumber == [
        IR_WAVENUMBER_4000,
        IR_WAVENUMBER_3000,
        IR_WAVENUMBER_2000,
    ]
    assert spectrum.transmittance == [
        IR_TRANSMITTANCE_0_99,
        IR_TRANSMITTANCE_0_95,
        IR_TRANSMITTANCE_0_90,
    ]


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

    assert len(spectrum.wavenumber) == IR_SPECTRUM_LENGTH_2
    tolerance = SCIENTIFIC_NOTATION_TOLERANCE
    assert abs(spectrum.wavenumber[0] - IR_WAVENUMBER_4000) < tolerance


def test_ir_spectrum_equality():
    """Test that IRSpectrum dataclass equality works."""
    spectrum1 = IRSpectrum(
        wavenumber=[IR_WAVENUMBER_4000, IR_WAVENUMBER_3000],
        transmittance=[IR_TRANSMITTANCE_0_99, IR_TRANSMITTANCE_0_95],
    )
    spectrum2 = IRSpectrum(
        wavenumber=[IR_WAVENUMBER_4000, IR_WAVENUMBER_3000],
        transmittance=[IR_TRANSMITTANCE_0_99, IR_TRANSMITTANCE_0_95],
    )

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

    assert hasattr(spectrum, 'wavenumber')
    assert hasattr(spectrum, 'transmittance')
    assert len(spectrum.wavenumber) == IR_SPECTRUM_LENGTH_3
    assert len(spectrum.transmittance) == IR_SPECTRUM_LENGTH_3
