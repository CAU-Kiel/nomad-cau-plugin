import numpy as np

import nomad_cau_plugin.parsers.xrd_from_cif as xrd_module
from nomad_cau_plugin.normalizers.CaP_experiments_normalizer import CaPNormalizer
from nomad_cau_plugin.parsers.xrd_from_cif import (
    XRDPattern,
    xrd_pattern_from_reference_file_bytes,
    xrd_pattern_from_vasp_bytes,
    xrd_pattern_from_xy_bytes,
)

# Test constants
Q_AXIS_THRESHOLD_8_8 = 8.8


def test_xrd_pattern_from_xy_bytes_parses_two_columns():
    pattern = xrd_pattern_from_xy_bytes(b'# comment\n10.0 100\n20.0 200\n')

    assert pattern == XRDPattern(two_theta=[10.0, 20.0], intensity=[100.0, 200.0])


def test_xrd_pattern_from_reference_file_bytes_dispatches_by_extension():
    xy_pattern = xrd_pattern_from_reference_file_bytes(
        'pattern.xy',
        b'10 5\n20 10\n',
    )
    assert xy_pattern.two_theta == [10.0, 20.0]


def test_xrd_pattern_from_vasp_bytes_returns_pattern():
    vasp_text = """Fe
1.0
1 0 0
0 1 0
0 0 1
Fe
1
Direct
0 0 0
"""

    original_pattern_from_structure = xrd_module._pattern_from_structure
    xrd_module._pattern_from_structure = lambda *args, **kwargs: XRDPattern(
        two_theta=[12.0, 24.0],
        intensity=[1.0, 0.5],
    )
    try:
        pattern = xrd_pattern_from_vasp_bytes(vasp_text.encode('utf-8'))
    finally:
        xrd_module._pattern_from_structure = original_pattern_from_structure

    assert pattern == XRDPattern(two_theta=[12.0, 24.0], intensity=[1.0, 0.5])


def test_q_axis_conversion_uses_wavelength():
    q_values = CaPNormalizer._two_theta_to_q(np.array([0.0, 90.0]), 1.0)

    assert q_values[0] == 0.0
    assert q_values[1] > Q_AXIS_THRESHOLD_8_8