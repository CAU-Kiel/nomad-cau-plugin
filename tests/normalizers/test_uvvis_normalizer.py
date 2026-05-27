from contextlib import contextmanager
from io import BytesIO

from nomad_cau_plugin.normalizers.uvvis_normalizer import UVVisNormalizer


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)


class DummyContext:
    def __init__(self, file_bytes):
        self.file_bytes = file_bytes

    @contextmanager
    def raw_file(self, path, mode):
        yield BytesIO(self.file_bytes)


class DummyArchive:
    def __init__(self, file_bytes):
        self.m_context = DummyContext(file_bytes)


def test_process_uvvis_data_selects_requested_trace():
    file_bytes = b'''Baseline 100%T;;BaSO4;;BaSO4+MT-MA-009
Wavelength (nm);%R;Wavelength (nm);%R;Wavelength (nm);F(R)
2000;83.91782379;2000;89.5533371;2000;0.00609317
1999;84.0428772;1999;89.20882416;1999;0.006526792
'''

    result = UVVisNormalizer.process_uvvis_data(
        DummyArchive(file_bytes),
        'sample.csv',
        DummyLogger(),
        selected_trace='BaSO4+MT-MA-009',
    )

    assert result['available_traces'] == [
        'Baseline 100%T',
        'BaSO4',
        'BaSO4+MT-MA-009',
    ]
    assert result['selected_trace'] == 'BaSO4+MT-MA-009'
    assert result['x_values'] == [2000.0, 1999.0]
    assert result['y_values'] == [0.00609317, 0.006526792]
    assert (
        result['figure'].figure['layout']['title']['text']
        == 'UV-Vis: BaSO4+MT-MA-009'
    )