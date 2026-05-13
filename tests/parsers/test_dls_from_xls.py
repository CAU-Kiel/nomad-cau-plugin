"""Tests for DLS distribution data parsing."""

import numpy as np
import pytest

from nomad_cau_plugin.parsers.dls_from_xls import (
    DLSDistribution,
    dls_distribution_from_xls_bytes,
)


def test_dls_distribution_parses_intensity_type():
    """Test parsing DLS intensity distribution data."""
    dls_content = b"""File Name : MT-MA-005_20240927_153410
Group :
Sample Info :
-------------------------------------------------------------------------------------------
Cumulant Diameter (nm)  PI      D10     D50     D90
206,6   -0,053  191,6   199,6   207,5
-------------------------------------------------------------------------------------------
Diameter (nm)   Differential Intensity (%)      Cumulative Intensity(%)
100.0	5.0	5.0
150.0	20.0	25.0
200.0	50.0	75.0
250.0	25.0	100.0
"""
    dist = dls_distribution_from_xls_bytes(dls_content, distribution_type='Intensity')

    assert dist.distribution_type == 'Intensity'
    assert len(dist.diameter) == 4
    assert dist.diameter == [100.0, 150.0, 200.0, 250.0]
    assert dist.differential == [5.0, 20.0, 50.0, 25.0]
    assert dist.cumulative == [5.0, 25.0, 75.0, 100.0]
    assert dist.cumulant_diameter == 206.6
    assert dist.polydispersity_index == -0.053
    assert dist.d10 == 191.6
    assert dist.d50 == 199.6
    assert dist.d90 == 207.5


def test_dls_distribution_parses_volume_type():
    """Test parsing DLS volume distribution data."""
    dls_content = b"""File Name : MT-MA-005_20240927_153410
Group :
Sample Info :
-------------------------------------------------------------------------------------------
Cumulant Diameter (nm)  PI      D10     D50     D90
206,6   -0,053  191,3   199,0   207,0
-------------------------------------------------------------------------------------------
Diameter (nm)   Differential Volume (%) Cumulative Volume (%)
100.0\t3.0\t3.0
150.0\t18.0\t21.0
200.0\t60.0\t81.0
250.0\t19.0\t100.0
"""
    dist = dls_distribution_from_xls_bytes(dls_content, distribution_type='Volume')

    assert dist.distribution_type == 'Volume'
    assert dist.cumulant_diameter == 206.6
    assert dist.d50 == 199.0
    assert len(dist.diameter) == 4


def test_dls_distribution_parses_number_type():
    """Test parsing DLS number distribution data."""
    dls_content = b"""File Name : MT-MA-005_20240927_153410
Group :
Sample Info :
-------------------------------------------------------------------------------------------
Cumulant Diameter (nm)  PI      D10     D50     D90
206,6   -0,053  191,0   198,5   206,6
-------------------------------------------------------------------------------------------
Diameter (nm)   Differential Number (%) Cumulative Number (%)
100.0\t8.0\t8.0
150.0\t25.0\t33.0
200.0\t40.0\t73.0
250.0\t27.0\t100.0
"""
    dist = dls_distribution_from_xls_bytes(dls_content, distribution_type='Number')

    assert dist.distribution_type == 'Number'
    assert dist.cumulant_diameter == 206.6
    assert dist.d50 == 198.5
    assert dist.d90 == 206.6


def test_dls_distribution_equality():
    """Test that DLSDistribution dataclass equality works."""
    dist1 = DLSDistribution(
        diameter=[100.0, 150.0],
        differential=[5.0, 20.0],
        cumulative=[5.0, 25.0],
        cumulant_diameter=125.0,
        polydispersity_index=0.1,
        d10=100.0,
        d50=125.0,
        d90=150.0,
        distribution_type='Intensity',
    )
    dist2 = DLSDistribution(
        diameter=[100.0, 150.0],
        differential=[5.0, 20.0],
        cumulative=[5.0, 25.0],
        cumulant_diameter=125.0,
        polydispersity_index=0.1,
        d10=100.0,
        d50=125.0,
        d90=150.0,
        distribution_type='Intensity',
    )

    assert dist1 == dist2
