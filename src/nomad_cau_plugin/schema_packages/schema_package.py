from typing import (
    TYPE_CHECKING,
)

import numpy as np

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config
from nomad.datamodel.data import ArchiveSection, EntryData, Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import Process, ProcessStep
from nomad.datamodel.metainfo.eln import ElnBaseSection
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Datetime, MEnum, Quantity, SchemaPackage, Section, SubSection

from nomad_cau_plugin.measurements.CaP_experiments import Chemical, XRDMeasurement
from nomad_cau_plugin.normalizers.CaP_experiments_normalizer import CaPNormalizer

configuration = config.get_plugin_entry_point(
    'nomad_cau_plugin.schema_packages:schema_package_entry_point'
)

m_package = SchemaPackage()


class NewSchemaPackage(Schema):
    name = Quantity(
        type=str, a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )
    message = Quantity(type=str)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        logger.info('NewSchema.normalize', parameter=configuration.parameter)
        self.message = f'Hello {self.name}!'


class SynthesisChemical(Chemical):
    m_def = Section(
        label='Synthesis Chemical',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'role',
                    'addition_time',
                    'chemical_name',
                    'mol_weight',
                    'actual_moles',
                    'actual_amount',
                    'concentration',
                ]
            }
        },
    )

    role = Quantity(
        type=MEnum('Solvent', 'Solid Reactant', 'Liquid Reactant', 'Additive'),
        description='Role of the chemical in the synthesis.',
        a_eln={'component': 'EnumEditQuantity'},
    )
    addition_time = Quantity(
        type=Datetime,
        description='Absolute timestamp when this chemical was added.',
        a_eln={'component': 'TimeEditQuantity'},
    )


class SynthesisStep(ProcessStep, ArchiveSection):
    m_def = Section(
        label='Synthesis Step',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'start_time',
                    'duration',
                    'reaction_temperature_start',
                    'reaction_temperature_end',
                    'procedure',
                    'chemicals',
                ]
            }
        },
    )

    reaction_temperature_start = Quantity(
        type=np.float64,
        unit='celsius',
        description='Temperature at the start of this synthesis step.',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'celsius'},
    )
    reaction_temperature_end = Quantity(
        type=np.float64,
        unit='celsius',
        description='Temperature at the end of this synthesis step.',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'celsius'},
    )
    procedure = Quantity(
        type=str,
        description='Free-text procedure details for this synthesis step.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    chemicals = SubSection(section_def=SynthesisChemical, repeats=True)


class Synthesis(Process, ArchiveSection):
    m_def = Section(
        label='Synthesis',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'steps',
                ]
            }
        },
    )

    steps = SubSection(section_def=SynthesisStep, repeats=True)


class RefinementStep(ElnBaseSection, ArchiveSection):
    m_def = Section(
        label='Refinement Step',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'step_type',
                    'duration',
                    'solvent',
                    'rpm_speed',
                    'oven_type',
                    'temperature',
                ]
            }
        },
    )

    step_type = Quantity(
        type=MEnum('washing', 'centrifuge', 'drying'),
        description='Select the refinement step type.',
        a_eln={'component': 'EnumEditQuantity'},
    )
    duration = Quantity(
        type=np.float64,
        unit='seconds',
        description='Duration of the refinement step.',
        a_eln={'component': 'NumberEditQuantity'},
    )
    solvent = SubSection(
        section_def=Chemical,
        description='Solvent used for washing.',
    )
    rpm_speed = Quantity(
        type=np.float64,
        description='Centrifuge rotational speed in revolutions per minute.',
        a_eln={'component': 'NumberEditQuantity'},
    )
    oven_type = Quantity(
        type=str,
        description='Description of the oven type.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    temperature = Quantity(
        type=np.float64,
        unit='kelvin',
        description='Temperature in Kelvin.',
        a_eln={'component': 'NumberEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Auto-generate step name based on type and sequence."""
        super().normalize(archive, logger)

        if self.step_type:
            if not self.name or self.name.startswith(
                ('washing', 'centrifuge', 'drying')
            ):
                try:
                    parent = self.m_parent
                    if parent and hasattr(parent, 'steps'):
                        count = 1
                        for step in parent.steps:
                            if step is self:
                                break
                            if step.step_type == self.step_type:
                                count += 1
                        self.name = f"{self.step_type} {count}"
                except Exception as e:
                    logger.warning(f'Could not auto-generate step name: {e}')
                    if not self.name:
                        self.name = f"{self.step_type} step"


class Refinement(ArchiveSection):
    m_def = Section(
        label='Refinement',
        a_eln={
            'properties': {
                'order': [
                    'steps',
                ]
            }
        },
    )

    steps = SubSection(section_def=RefinementStep, repeats=True)


class Characterization(ArchiveSection):
    m_def = Section(
        label='Characterization',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'description',
                    'xrd_measurements',
                    'uv_vis_measurements',
                    'dls_measurements',
                    'ir_measurements',
                    'raman_measurements',
                ]
            }
        },
    )

    name = Quantity(
        type=str,
        description='Name of characterization campaign.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    description = Quantity(
        type=str,
        description='Description of characterization measurements.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    xrd_measurements = SubSection(
        section_def=XRDMeasurement,
        repeats=True,
        description='X-ray diffraction measurements.',
    )
    uv_vis_measurements = SubSection(
        section_def=XRDMeasurement,
        repeats=True,
        description='UV-VIS spectroscopy measurements (placeholder).',
    )
    dls_measurements = SubSection(
        section_def=XRDMeasurement,
        repeats=True,
        description='Dynamic Light Scattering measurements (placeholder).',
    )
    ir_measurements = SubSection(
        section_def=XRDMeasurement,
        repeats=True,
        description='Infrared spectroscopy measurements (placeholder).',
    )
    raman_measurements = SubSection(
        section_def=XRDMeasurement,
        repeats=True,
        description='Raman spectroscopy measurements (placeholder).',
    )


class Michaela(PlotSection, EntryData, ArchiveSection):
    m_def = Section(
        label='Michaela',
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'description',
                    'external_id',
                    'synthesis',
                    'refinement',
                    'characterization',
                ]
            }
        },
    )

    name = Quantity(
        type=str,
        description='Name of this Michaela entry.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    description = Quantity(
        type=str,
        description='Free-text description that can be adjusted later.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    external_id = Quantity(
        type=str,
        description='Optional external identifier.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    synthesis = SubSection(section_def=Synthesis)
    refinement = SubSection(section_def=Refinement)
    characterization = SubSection(section_def=Characterization)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.characterization and self.characterization.xrd_measurements:
            for xrd in self.characterization.xrd_measurements:
                if xrd and xrd.xrd_file:
                    xrd_result = CaPNormalizer.process_xrd_file(
                        archive, xrd.xrd_file, logger
                    )
                    xrd.two_theta = xrd_result['two_theta']
                    xrd.intensity = xrd_result['intensity']
                    self.figures.append(xrd_result['figure'])


m_package.__init_metainfo__()
