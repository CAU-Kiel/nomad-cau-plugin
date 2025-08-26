from nomad.config.models.plugins import NormalizerEntryPoint
from pydantic import Field


class NewNormalizerEntryPoint(NormalizerEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_cau_plugin.normalizers.normalizer import NewNormalizer

        return NewNormalizer(**self.model_dump())


normalizer_entry_point = NewNormalizerEntryPoint(
    name='NewNormalizer',
    description='New normalizer entry point configuration.',
)

# Import the new normalizers
from .mro004_normalizer import MRO004Normalizer
from .mro005_normalizer import MRO005Normalizer
