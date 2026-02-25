from .xrd_from_cif import XRDPattern, xrd_pattern_from_cif_bytes

__all__ = [
    'XRDPattern',
    'xrd_pattern_from_cif_bytes',
]

from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_cau_plugin.parsers.parser import NewParser

        return NewParser(**self.model_dump())


parser_entry_point = NewParserEntryPoint(
    name='NewParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.*\.newmainfilename',
)
