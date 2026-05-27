from nomad.config.models.plugins import SchemaPackageEntryPoint


class MRO005SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_cau_plugin.measurements.MRO005 import (  # noqa: PLC0415
            m_package as m_package_mro005,
        )

        return m_package_mro005


MRO005_schema = MRO005SchemaPackageEntryPoint(
    name='experiment MRO005 schema',
    description='Schema tailored for experimnet MRO005.',
)


class MRO004SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_cau_plugin.measurements.CaP_experiments import (  # noqa: PLC0415
            m_package as m_package_mro004,
        )

        return m_package_mro004


MRO004_schema = MRO004SchemaPackageEntryPoint(
    name='experiment MRO004 schema',
    description='Schema tailored to experiment MRO004 and other Calcium Phosphate experiments.'  # noqa: E501
)


class UVVisSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_cau_plugin.measurements.UVVis import (  # noqa: PLC0415
            m_package as m_package_uvvis,
        )

        return m_package_uvvis


UVVis_schema = UVVisSchemaPackageEntryPoint(
    name='UV-Vis schema',
    description='Schema tailored to UV-Vis measurements.',
)
