from io import BytesIO

import pandas as pd
import pytest

from nomad_cau_plugin.parsers.luminescence_csv import luminescence_from_csv_bytes


def test_luminescence_from_csv_bytes_parses_csv_matrix():
    file_bytes = b'''time;2024-01-01 10:00:00;2024-01-01 10:01:00
meta;;
meta;;
meta;;
meta;;
500;1.0;2.0
510;3.0;4.0
'''

    parsed = luminescence_from_csv_bytes('sample.csv', file_bytes)

    assert parsed.time_seconds == [0.0, 60.0]
    assert parsed.wavelength_nm == [500.0, 510.0]
    assert parsed.intensity_matrix == [[1.0, 2.0], [3.0, 4.0]]


def test_luminescence_from_csv_bytes_uses_requested_sheet_name():
    sheet1 = pd.DataFrame(
        [
            ['time', '2024-01-01 08:00:00', '2024-01-01 08:01:00'],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            [500, 10.0, 20.0],
        ]
    )
    sheet2 = pd.DataFrame(
        [
            ['time', '2024-01-01 09:00:00', '2024-01-01 09:02:00'],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            [600, 1.5, 2.5],
        ]
    )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        sheet1.to_excel(writer, sheet_name='SheetA', index=False, header=False)
        sheet2.to_excel(writer, sheet_name='MyLum', index=False, header=False)

    parsed = luminescence_from_csv_bytes(
        'sample.xlsx',
        buffer.getvalue(),
        sheet_names=['MyLum'],
    )

    assert parsed.time_seconds == [0.0, 120.0]
    assert parsed.wavelength_nm == [600.0]
    assert parsed.intensity_matrix == [[1.5, 2.5]]


def test_luminescence_from_csv_bytes_defaults_to_first_sheet_for_excel():
    first = pd.DataFrame(
        [
            ['time', '2024-01-01 07:00:00', '2024-01-01 07:00:30'],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            [700, 5.0, 6.0],
        ]
    )
    second = pd.DataFrame(
        [
            ['time', '2024-01-01 11:00:00', '2024-01-01 11:05:00'],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            [800, 9.0, 10.0],
        ]
    )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        first.to_excel(writer, sheet_name='FirstSheet', index=False, header=False)
        second.to_excel(writer, sheet_name='SecondSheet', index=False, header=False)

    parsed = luminescence_from_csv_bytes('sample.xlsx', buffer.getvalue())

    assert parsed.time_seconds == [0.0, 30.0]
    assert parsed.wavelength_nm == [700.0]
    assert parsed.intensity_matrix == [[5.0, 6.0]]


def test_luminescence_from_csv_bytes_raises_for_unknown_sheet_name():
    frame = pd.DataFrame(
        [
            ['time', '2024-01-01 08:00:00', '2024-01-01 08:01:00'],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            ['meta', '', ''],
            [500, 10.0, 20.0],
        ]
    )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        frame.to_excel(writer, sheet_name='Data', index=False, header=False)

    with pytest.raises(
        ValueError,
        match='None of the requested sheet names were found',
    ):
        luminescence_from_csv_bytes(
            'sample.xlsx',
            buffer.getvalue(),
            sheet_names=['MissingSheet'],
        )
