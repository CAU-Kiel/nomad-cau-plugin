from nomad.config.models.plugins import SchemaPackageEntryPoint


class MRO005SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_cau_plugin.measurements.MRO005 import m_package

        return m_package


MRO005_schema = MRO005SchemaPackageEntryPoint(
    name='experiment MRO005 schema',
    description='Schema tailored for experimnet MRO005.',
)


class MRO004SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_cau_plugin.measurements.MRO004 import m_package

        return m_package


MRO004_schema = MRO004SchemaPackageEntryPoint(
    name='experiment MRO004 schema', description='Schema tailored to experiment MRO004.'
)
