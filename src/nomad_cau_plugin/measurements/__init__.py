from nomad.config.models.plugins import SchemaPackageEntryPoint

from nomad_cau_plugin.measurements.MRO004 import m_package as m_package_mro004
from nomad_cau_plugin.measurements.MRO005 import m_package as m_package_mro005


class MRO005SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self): 
        return m_package_mro005


MRO005_schema = MRO005SchemaPackageEntryPoint(
    name='experiment MRO005 schema',
    description='Schema tailored for experimnet MRO005.',
)


class MRO004SchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        return m_package_mro004


MRO004_schema = MRO004SchemaPackageEntryPoint(
    name='experiment MRO004 schema', description='Schema tailored to experiment MRO004.'
)
