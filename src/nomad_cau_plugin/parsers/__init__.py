from .dls_from_xls import DLSDistribution, dls_distribution_from_xls_bytes
from .ir_from_dpt import IRSpectrum, ir_spectrum_from_dpt_bytes
from .luminescence_csv import LuminescenceData, luminescence_from_csv_bytes
from .xrd_from_cif import (
    XRDPattern,
    xrd_pattern_from_cif_bytes,
    xrd_pattern_from_reference_file_bytes,
    xrd_pattern_from_vasp_bytes,
    xrd_pattern_from_xy_bytes,
)

__all__ = [
    'XRDPattern',
    'xrd_pattern_from_cif_bytes',
    'xrd_pattern_from_xy_bytes',
    'xrd_pattern_from_vasp_bytes',
    'xrd_pattern_from_reference_file_bytes',
    'IRSpectrum',
    'ir_spectrum_from_dpt_bytes',
    'LuminescenceData',
    'luminescence_from_csv_bytes',
    'DLSDistribution',
    'dls_distribution_from_xls_bytes',
]

from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):  # noqa: PLC0415
        from nomad_cau_plugin.parsers.parser import NewParser  # noqa: PLC0415, I001

        return NewParser(**self.model_dump())


parser_entry_point = NewParserEntryPoint(
    name='NewParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.*\.newmainfilename',
)
