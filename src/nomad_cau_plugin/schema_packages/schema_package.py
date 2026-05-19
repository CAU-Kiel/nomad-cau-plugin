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

from nomad_cau_plugin.measurements.CaP_experiments import (
    Chemical,
    XRDMeasurement,
)
from nomad_cau_plugin.normalizers.Michaela_experiments_normalizer import (
    MichaelaNormalizer,
)

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


class IRMeasurement(ElnBaseSection, ArchiveSection):
    """IR spectroscopy measurement section with .dpt file upload."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'ir_file',
                    'wavenumber',
                    'transmittance',
                ]
            }
        }
    )

    ir_file = Quantity(
        type=str,
        description='IR spectroscopy data file in .dpt format',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    wavenumber = Quantity(
        type=np.float64,
        shape=['*'],
        unit='1/cm',
        description='Wavenumber axis in cm⁻¹',
    )
    transmittance = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Transmittance values (typically 0-1 range)',
    )


class DLSMeasurement(ElnBaseSection, ArchiveSection):
    """DLS measurement with intensity, volume, and number distributions."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'intensity_distribution_file',
                    'volume_distribution_file',
                    'number_distribution_file',
                    'intensity_diameter',
                    'intensity_differential',
                    'intensity_cumulative',
                    'volume_diameter',
                    'volume_differential',
                    'volume_cumulative',
                    'number_diameter',
                    'number_differential',
                    'number_cumulative',
                    'intensity_cumulant_diameter',
                    'intensity_polydispersity_index',
                    'intensity_d10',
                    'intensity_d50',
                    'intensity_d90',
                    'volume_cumulant_diameter',
                    'volume_d50',
                    'number_cumulant_diameter',
                    'number_d50',
                ]
            }
        }
    )

    intensity_distribution_file = Quantity(
        type=str,
        description='Intensity distribution .xls file',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    volume_distribution_file = Quantity(
        type=str,
        description='Volume distribution .xls file',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    number_distribution_file = Quantity(
        type=str,
        description='Number distribution .xls file',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )

    # Intensity distribution data
    intensity_diameter = Quantity(
        type=np.float64,
        shape=['*'],
        unit='nanometer',
        description='Diameter axis for intensity distribution',
    )
    intensity_differential = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Differential intensity distribution (%)',
    )
    intensity_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Cumulative intensity distribution (%)',
    )

    # Volume distribution data
    volume_diameter = Quantity(
        type=np.float64,
        shape=['*'],
        unit='nanometer',
        description='Diameter axis for volume distribution',
    )
    volume_differential = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Differential volume distribution (%)',
    )
    volume_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Cumulative volume distribution (%)',
    )

    # Number distribution data
    number_diameter = Quantity(
        type=np.float64,
        shape=['*'],
        unit='nanometer',
        description='Diameter axis for number distribution',
    )
    number_differential = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Differential number distribution (%)',
    )
    number_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='Cumulative number distribution (%)',
    )

    # Cumulant diameter and percentile data
    intensity_cumulant_diameter = Quantity(
        type=np.float64,
        unit='nanometer',
        description='Cumulant diameter (mean) from intensity distribution',
    )
    intensity_polydispersity_index = Quantity(
        type=np.float64,
        unit='dimensionless',
        description='Polydispersity index from intensity distribution',
    )
    intensity_d10 = Quantity(
        type=np.float64,
        unit='nanometer',
        description='D10 percentile (10%) from intensity distribution',
    )
    intensity_d50 = Quantity(
        type=np.float64,
        unit='nanometer',
        description='D50 percentile (50%, median) from intensity distribution',
    )
    intensity_d90 = Quantity(
        type=np.float64,
        unit='nanometer',
        description='D90 percentile (90%) from intensity distribution',
    )

    volume_cumulant_diameter = Quantity(
        type=np.float64,
        unit='nanometer',
        description='Cumulant diameter (mean) from volume distribution',
    )
    volume_d50 = Quantity(
        type=np.float64,
        unit='nanometer',
        description='D50 percentile (50%, median) from volume distribution',
    )

    number_cumulant_diameter = Quantity(
        type=np.float64,
        unit='nanometer',
        description='Cumulant diameter (mean) from number distribution',
    )
    number_d50 = Quantity(
        type=np.float64,
        unit='nanometer',
        description='D50 percentile (50%, median) from number distribution',
    )


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
        section_def=DLSMeasurement,
        repeats=True,
        description='Dynamic Light Scattering measurements.',
    )
    ir_measurements = SubSection(
        section_def=IRMeasurement,
        repeats=True,
        description='Infrared spectroscopy measurements.',
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
                    xrd_result = MichaelaNormalizer.process_xrd_file(
                        archive,
                        xrd.xrd_file,
                        logger,
                        reference_files=xrd.xrd_reference_cif_files,
                        xrd_alpha=getattr(xrd, 'xrd_alpha', None),
                    )
                    xrd.two_theta = xrd_result['two_theta']
                    xrd.intensity = xrd_result['intensity']
                    self.figures = [
                        figure
                        for figure in (self.figures or [])
                        if getattr(figure, 'label', None) != 'XRD Pattern'
                    ]
                    self.figures.append(xrd_result['figure'])

        if self.characterization and self.characterization.ir_measurements:
            for ir in self.characterization.ir_measurements:
                if ir and ir.ir_file:
                    ir_result = MichaelaNormalizer.process_ir_file(
                        archive, ir.ir_file, logger
                    )
                    ir.wavenumber = ir_result['wavenumber']
                    ir.transmittance = ir_result['transmittance']
                    self.figures = [
                        figure
                        for figure in (self.figures or [])
                        if getattr(figure, 'label', None) != 'IR Spectrum'
                    ]
                    self.figures.append(ir_result['figure'])

        if self.characterization and self.characterization.dls_measurements:
            for dls in self.characterization.dls_measurements:
                if dls:
                    dls_result = MichaelaNormalizer.process_dls_files(
                        archive, dls, logger
                    )
                    if dls_result:
                        # Set intensity distribution data
                        dls.intensity_diameter = dls_result['intensity_diameter']
                        dls.intensity_differential = dls_result[
                            'intensity_differential'
                        ]
                        dls.intensity_cumulative = dls_result['intensity_cumulative']
                        dls.intensity_cumulant_diameter = dls_result[
                            'intensity_cumulant_diameter'
                        ]
                        dls.intensity_polydispersity_index = dls_result[
                            'intensity_polydispersity_index'
                        ]
                        dls.intensity_d10 = dls_result['intensity_d10']
                        dls.intensity_d50 = dls_result['intensity_d50']
                        dls.intensity_d90 = dls_result['intensity_d90']

                        # Set volume distribution data
                        dls.volume_diameter = dls_result['volume_diameter']
                        dls.volume_differential = dls_result['volume_differential']
                        dls.volume_cumulative = dls_result['volume_cumulative']
                        dls.volume_cumulant_diameter = dls_result[
                            'volume_cumulant_diameter'
                        ]
                        dls.volume_d50 = dls_result['volume_d50']

                        # Set number distribution data
                        dls.number_diameter = dls_result['number_diameter']
                        dls.number_differential = dls_result['number_differential']
                        dls.number_cumulative = dls_result['number_cumulative']
                        dls.number_cumulant_diameter = dls_result[
                            'number_cumulant_diameter'
                        ]
                        dls.number_d50 = dls_result['number_d50']

                        # Add figures, removing old DLS figures first
                        self.figures = [
                            figure
                            for figure in (self.figures or [])
                            if getattr(figure, 'label', None)
                            not in [
                                'DLS Intensity Distribution',
                                'DLS Volume Distribution',
                                'DLS Number Distribution',
                            ]
                        ]
                        self.figures.extend(dls_result.get('figures', []))


m_package.__init_metainfo__()
