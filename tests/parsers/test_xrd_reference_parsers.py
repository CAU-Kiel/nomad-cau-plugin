import numpy as np
import pandas as pd

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


def test_xrd_pattern_from_reference_file_bytes_filters_xy_range():
    xy_pattern = xrd_pattern_from_reference_file_bytes(
        'pattern.xyd',
        b'10 5\n20 10\n30 15\n',
        two_theta_range=(15.0, 25.0),
    )

    assert xy_pattern.two_theta == [20.0]


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


def test_xrd_plot_uses_angstrom_symbol_for_q_axis(monkeypatch):
    monkeypatch.setattr(
        CaPNormalizer,
        '_read_xyd_df',
        staticmethod(
            lambda *args, **kwargs: pd.DataFrame(
                {
                    'two_theta': [10.0, 20.0],
                    'intensity': [1.0, 2.0],
                }
            )
        ),
    )
    monkeypatch.setattr(
        CaPNormalizer,
        '_collect_reference_dfs',
        staticmethod(lambda *args, **kwargs: []),
    )

    result = CaPNormalizer.normalize_xrd_data(
        archive=None,
        xrd_file='test.xyd',
        logger=type('Logger', (), {'error': lambda *args, **kwargs: None})(),
    )

    assert result['figure'].figure['layout']['xaxis']['title']['text'] == 'q (Å⁻¹)'