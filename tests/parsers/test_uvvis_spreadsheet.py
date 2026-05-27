from nomad_cau_plugin.parsers.uvvis_spreadsheet import (
    UVVisTrace,
    uvvis_traces_from_spreadsheet_bytes,
)


def test_uvvis_traces_from_spreadsheet_bytes_parses_pairwise_columns():
    file_bytes = b'''Baseline 100%T;;BaSO4;;BaSO4+MT-MA-009
Wavelength (nm);%R;Wavelength (nm);%R;Wavelength (nm);F(R)
2000;83.91782379;2000;89.5533371;2000;0.00609317
1999;84.0428772;1999;89.20882416;1999;0.006526792
'''

    traces = uvvis_traces_from_spreadsheet_bytes('sample.csv', file_bytes)

    assert traces == [
        UVVisTrace(
            name='Baseline 100%T',
            x_label='Wavelength (nm)',
            y_label='%R',
            x_values=[2000.0, 1999.0],
            y_values=[83.91782379, 84.0428772],
        ),
        UVVisTrace(
            name='BaSO4',
            x_label='Wavelength (nm)',
            y_label='%R',
            x_values=[2000.0, 1999.0],
            y_values=[89.5533371, 89.20882416],
        ),
        UVVisTrace(
            name='BaSO4+MT-MA-009',
            x_label='Wavelength (nm)',
            y_label='F(R)',
            x_values=[2000.0, 1999.0],
            y_values=[0.00609317, 0.006526792],
        ),
    ]