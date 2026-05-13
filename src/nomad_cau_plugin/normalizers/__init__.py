from nomad.config.models.plugins import NormalizerEntryPoint
from pydantic import Field


class NewNormalizerEntryPoint(NormalizerEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):  # noqa: PLC0415
        from nomad_cau_plugin.normalizers.normalizer import NewNormalizer  # noqa: PLC0415, I001

        return NewNormalizer(**self.model_dump())


normalizer_entry_point = NewNormalizerEntryPoint(
    name='NewNormalizer',
    description='New normalizer entry point configuration.',
)

