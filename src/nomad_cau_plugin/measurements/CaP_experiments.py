#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import (
    TYPE_CHECKING,
)

import numpy as np
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.basesections import ProcessStep
from nomad.datamodel.metainfo.eln import ElnBaseSection
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import (
    Datetime,
    Package,
    Quantity,
    Section,
    SubSection,
)
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )
from nomad_cau_plugin.normalizers.CaP_experiments_normalizer import CaPNormalizer

m_package = Package(name='Calcium Phosphate experiments archive schema')


class Chemical(ElnBaseSection):
    """
    Class for chemicals from the PDF report.
    """

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'chemical_name',
                    'mol_weight',
                    'actual_moles',
                    'actual_amount',
                    'concentration',
                ]
            }
        },
    )
    chemical_name = Quantity(
        type=str,
        description='name of the chemical',
        a_eln={'component': 'StringEditQuantity'},
    )
    mol_weight = Quantity(
        type=np.float64,
        description='molecular weight of the chemical',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'g/mol'},
        unit='g/mol',
    )
    actual_moles = Quantity(
        type=np.float64,
        description='actual moles used (m = n * M)',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mol'},
        unit='mol',
    )
    actual_amount = Quantity(
        type=np.float64,
        description='actual amount used in grams (m = n * M)',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'g'},
        unit='g',
    )
    concentration = Quantity(
        type=str,
        description='concentration (e.g., 100 w/w%)',
        a_eln={'component': 'StringEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the 'Chemical' class.
        Implements automatic recalculation: m = n * M (mass = moles × molecular weight)

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        # Set the name for GUI display if not already set
        if not self.name and self.chemical_name:
            self.name = self.chemical_name

        # Auto-recalculate if both mol_weight and one of the other values are set
        if hasattr(self, 'mol_weight') and self.mol_weight is not None:
            mol_weight_value = (
                self.mol_weight.magnitude
                if hasattr(self.mol_weight, 'magnitude')
                else self.mol_weight
            )

            if hasattr(self, 'actual_moles') and self.actual_moles is not None:
                moles_value = (
                    self.actual_moles.magnitude
                    if hasattr(self.actual_moles, 'magnitude')
                    else self.actual_moles
                )
                # Calculate mass: m = n * M
                calculated_mass = moles_value * mol_weight_value
                self.actual_amount = ureg.Quantity(calculated_mass, 'g')

            elif hasattr(self, 'actual_amount') and self.actual_amount is not None:
                mass_value = (
                    self.actual_amount.magnitude
                    if hasattr(self.actual_amount, 'magnitude')
                    else self.actual_amount
                )
                # Calculate moles: n = m / M
                calculated_moles = mass_value / mol_weight_value
                self.actual_moles = ureg.Quantity(calculated_moles, 'mol')


class Recipe(ProcessStep, ArchiveSection):
    """
    Class for recipe inside an excel file MRO005.
    """

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'step_number',
                    'action',
                    'duration',
                    'start_time',
                    'end_time',
                ]
            }
        },
    )
    action = Quantity(
        type=str,
        description='an action/annotation from recipe file',
        a_eln={'component': 'StringEditQuantity'},
    )
    duration = Quantity(
        # probably needed normalizer to convert this datetime to seconds
        type=np.float64,
        description='the duration of the action performed',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'second'},
        unit='seconds',
    )
    start_time = Quantity(
        type=Datetime,
        description='absolute start time of an action',
        a_eln={'component': 'TimeEditQuantity'},
    )
    end_time = Quantity(
        type=Datetime,
        description='absolute end time of an action',
        a_eln={'component': 'TimeEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the 'Recipe' class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class SetupImage(ElnBaseSection, ArchiveSection):
    """Metadata for documenting experimental setup photos uploaded elsewhere."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'caption',
                ]
            }
        },
    )
    caption = Quantity(
        type=str,
        description=(
            'Caption/notes for the setup photo '
            '(upload/view the image via the entry description)'
        ),
        a_eln={'component': 'StringEditQuantity'},
    )


class ReactorMeasurement(ElnBaseSection, ArchiveSection):
    """Reactor/process monitoring data upload and derived quantities."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'data_file',
                    'report_file',
                    'process_time',
                    'CalciumNitrate_Complex',
                    'Conductivity',
                    'pH',
                    'Temperature',
                ]
            }
        }
    )

    data_file = Quantity(
        type=str,
        description='Reactor/process data file (CSV)',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    report_file = Quantity(
        type=str,
        description='PDF report file containing recipe and chemistry information',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    process_time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='seconds',
    )
    CalciumNitrate_Complex = Quantity(
        type=np.float64,
        shape=['*'],
        unit='milliliter',
    )
    Conductivity = Quantity(
        type=np.float64,
        shape=['*'],
        unit='millisiemens/centimeter',
    )
    pH = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
    )
    Temperature = Quantity(
        type=np.float64,
        shape=['*'],
        unit='celsius',
    )


class XRDMeasurement(ElnBaseSection, ArchiveSection):
    """XRD upload section with optional reference files."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'xrd_file',
                    'xrd_alpha',
                    'xrd_reference_cif_files',
                    'two_theta',
                    'intensity',
                ]
            }
        }
    )

    xrd_file = Quantity(
        type=str,
        description='XRD data file in .xyd format',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    xrd_alpha = Quantity(
        type=np.float64,
        unit='angstrom',
        description=(
            'Optional wavelength (Angstrom) used for q conversion and reference '
            'pattern recomputation. Leave empty to use the default 1.5406 '
            'Angstrom (Cu Kα).'
        ),
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'angstrom',
            'props': {'placeholder': '1.5406'},
        },
    )
    xrd_reference_cif_files = Quantity(
        type=str,
        shape=['*'],
        label='Reference files',
        description='Optional reference files in .cif, .xy, .xyd, or .vasp format',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    two_theta = Quantity(
        type=np.float64,
        shape=['*'],
        unit='degree',
    )
    intensity = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
    )


class LuminescenceMeasurement(ElnBaseSection, ArchiveSection):
    """Luminescence section with matrix CSV upload and 3D plot outputs."""

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'data_file',
                    'measurement_start_time',
                    'measurement_start_label',
                    'time_seconds',
                    'wavelength_nm',
                    'intensity_matrix',
                ]
            }
        }
    )

    data_file = Quantity(
        type=str,
        description=(
            'Luminescence matrix CSV. Row 1 contains timestamps in columns 2..N, '
            'rows 2..5 are ignored, data starts at row 6.'
        ),
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    measurement_start_time = Quantity(
        type=Datetime,
        description=(
            'Absolute start timestamp parsed from the first measurement column.'
        ),
        a_eln={'component': 'TimeEditQuantity'},
    )
    measurement_start_label = Quantity(
        type=str,
        description='Display label for measurement start (date and time).',
        a_eln={'component': 'StringEditQuantity'},
    )
    time_seconds = Quantity(
        type=np.float64,
        shape=['*'],
        unit='seconds',
        description='Measurement time axis normalized to seconds from start.',
    )
    wavelength_nm = Quantity(
        type=np.float64,
        shape=['*'],
        unit='nanometer',
        description='Wavelength vector from first column starting at row 6.',
    )
    intensity_matrix = Quantity(
        type=np.float64,
        shape=['*', '*'],
        description='Intensity matrix with axes [wavelength, time].',
    )


class DLSMeasurement(ElnBaseSection, ArchiveSection):
    """Dynamic Light Scattering measurement with three distribution types."""

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
        unit='percent',
        description='Differential intensity distribution (%)',
    )
    intensity_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='percent',
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
        unit='percent',
        description='Differential volume distribution (%)',
    )
    volume_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='percent',
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
        unit='percent',
        description='Differential number distribution (%)',
    )
    number_cumulative = Quantity(
        type=np.float64,
        shape=['*'],
        unit='percent',
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



class CaP_experiments(PlotSection, EntryData, ArchiveSection):
    """
    Class for MRO004 Calcium Phosphate experiments.
    """

    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'reactor',
                    'xrd',
                    'luminescence',
                    'chemicals',
                    'steps',
                    'setup_images',
                ]
            }
        }
    )

    reactor = SubSection(section_def=ReactorMeasurement)
    xrd = SubSection(section_def=XRDMeasurement)
    luminescence = SubSection(section_def=LuminescenceMeasurement)
    chemicals = SubSection(section_def=Chemical, repeats=True)
    steps = SubSection(section_def=Recipe, repeats=True)
    setup_images = SubSection(section_def=SetupImage, repeats=True)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `MRO004` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        # Process reactor CSV data file
        if self.reactor and self.reactor.data_file:
            data_result = CaPNormalizer.process_csv_data(
                archive, self.reactor.data_file, logger
            )

            # Set the processed data
            self.reactor.process_time = data_result['process_time']
            self.reactor.CalciumNitrate_Complex = data_result['calcium_nitrate_complex']
            self.reactor.Conductivity = data_result['conductivity']
            self.reactor.pH = data_result['ph']
            self.reactor.Temperature = data_result['temperature']
            self.figures.append(data_result['figure'])

        # Process PDF report file
        if self.reactor and self.reactor.report_file and not self.chemicals:
            chemicals, steps = CaPNormalizer.process_pdf_report(
                archive, self.reactor.report_file, logger
            )
            self.chemicals = chemicals
            self.steps = steps

        # Process XRD file
        if self.xrd and self.xrd.xrd_file:
            xrd_result = CaPNormalizer.process_xrd_file(
                archive,
                self.xrd.xrd_file,
                logger,
                reference_files=(self.xrd.xrd_reference_cif_files or None),
                xrd_alpha=self.xrd.xrd_alpha,
            )
            self.xrd.two_theta = xrd_result['two_theta']
            self.xrd.intensity = xrd_result['intensity']
            self.figures = [
                figure
                for figure in (self.figures or [])
                if getattr(figure, 'label', None) != 'XRD Pattern'
            ]
            self.figures.append(xrd_result['figure'])

        # Process luminescence CSV file
        if self.luminescence and self.luminescence.data_file:
            lum_result = CaPNormalizer.process_luminescence_data(
                archive,
                self.luminescence.data_file,
                logger,
            )
            self.luminescence.measurement_start_time = lum_result[
                'measurement_start_time'
            ]
            self.luminescence.measurement_start_label = lum_result[
                'measurement_start_label'
            ]
            self.luminescence.time_seconds = lum_result['time_seconds']
            self.luminescence.wavelength_nm = lum_result['wavelength_nm']
            self.luminescence.intensity_matrix = lum_result['intensity_matrix']
            self.figures.append(lum_result['figure'])




m_package.__init_metainfo__()
