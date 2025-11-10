from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field

from nomad_cau_plugin.parsers.parser import NewParser


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):

        return NewParser(**self.model_dump())


parser_entry_point = NewParserEntryPoint(
    name='NewParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.*\.newmainfilename',
)
