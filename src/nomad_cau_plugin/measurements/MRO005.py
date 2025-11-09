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

import re
from typing import (
    TYPE_CHECKING,
)

import numpy as np
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.basesections import (
    ProcessStep,
    PubChemPureSubstanceSection,
)
from nomad.datamodel.metainfo.eln import ElnBaseSection
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import (
    Datetime,
    Package,
    Quantity,
    Section,
    SubSection,
)
from nomad.units import ureg
from nomad_cau_plugin.normalizers.mro005_normalizer import MRO005Normalizer

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

m_package = Package(name='MRO005 archive schema')

class Chemical(ElnBaseSection):
    '''
        Class for chemicals from Excel file (MRO005).
        Now with automatic PubChem/CAS database integration!
    '''
    m_def=Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'chemical_name',
                    'pure_substance',
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
        a_eln={'component':'StringEditQuantity'}
    )
    pure_substance = SubSection(
        section_def=PubChemPureSubstanceSection,
        description="""
        Chemical substance information with automatic PubChem/CAS database lookup.
        Automatically populates molecular formula, SMILES, InChI, CAS number, and more.
        """,
    )
    mol_weight = Quantity(
        type=np.float64,
        description='molecular weight of the chemical',
        a_eln={'component':'NumberEditQuantity', 'defaultDisplayUnit': 'g/mol'},
        unit='g/mol',
    )
    actual_moles = Quantity(
        type=np.float64,
        description='actual moles used (m = n * M)',
        a_eln={'component':'NumberEditQuantity', 'defaultDisplayUnit': 'mol'},
        unit='mol',
    )
    actual_amount = Quantity(
        type=np.float64,
        description='actual amount used in grams (m = n * M)',
        a_eln={'component':'NumberEditQuantity', 'defaultDisplayUnit': 'g'},
        unit='g',
    )
    concentration = Quantity(
        type=str,
        description='concentration (e.g., 100 w/w%)',
        a_eln={'component':'StringEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the 'Chemical' class.
        Implements:
        1. Automatic PubChem/CAS database lookup
        2. Automatic recalculation: m = n * M (mass = moles × molecular weight)

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        
        # Set the name for GUI display if not already set
        if not self.name and self.chemical_name:
            self.name = self.chemical_name
        
        # AUTO-CREATE PubChem reference if chemical_name exists but pure_substance doesn't
        if self.chemical_name and not self.pure_substance:
            try:
                logger.info(f"Creating PubChem reference for chemical: {self.chemical_name}")
                self.pure_substance = PubChemPureSubstanceSection(name=self.chemical_name)
                logger.info(f"Successfully created PubChem reference for {self.chemical_name}")
            except Exception as e:
                logger.warning(f"Could not create PubChem reference for {self.chemical_name}: {e}")
        
        # Auto-recalculate if both mol_weight and one of the other values are set
        if hasattr(self, 'mol_weight') and self.mol_weight is not None:
            mol_weight_value = self.mol_weight.magnitude if hasattr(self.mol_weight, 'magnitude') else self.mol_weight
            
            if hasattr(self, 'actual_moles') and self.actual_moles is not None:
                moles_value = self.actual_moles.magnitude if hasattr(self.actual_moles, 'magnitude') else self.actual_moles
                # Calculate mass: m = n * M
                calculated_mass = moles_value * mol_weight_value
                self.actual_amount = ureg.Quantity(calculated_mass, 'g')
                
            elif hasattr(self, 'actual_amount') and self.actual_amount is not None:
                mass_value = self.actual_amount.magnitude if hasattr(self.actual_amount, 'magnitude') else self.actual_amount
                # Calculate moles: n = m / M
                calculated_moles = mass_value / mol_weight_value
                self.actual_moles = ureg.Quantity(calculated_moles, 'mol')

class Recipe(ProcessStep, ArchiveSection):
    '''
        Class for recipe inside an excel file MRO005.
    '''
    m_def=Section(
        a_eln={
            'properties': {
                'order': [
                    'step_number',
                    'action',
                    'duration',
                    'start_time',
                    'end_time',
                    'temperature',
                ]
            }
        },
    )
    action = Quantity(
        type=str,
        description='an action/annotation from recipe file',
        a_eln={'component':'StringEditQuantity'}
    )
    duration = Quantity(
        # probably needed normalizer to convert this datetime to seconds
        type=np.float64,
        description='the duration of the action performed',
        a_eln={'component':'NumberEditQuantity', 'defaultDisplayUnit': 'second'},
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
    temperature = Quantity(
        type=np.float64,
        description='relative temperature measurement during an action',
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'celsius'},
        unit='celsius',
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

class MRO005(PlotSection, EntryData, ArchiveSection):
    '''
    Class updated to use plotly_graph_object annotation.
    '''
    m_def = Section()
    chemicals = SubSection(
        section_def=Chemical,
        repeats=True,
        description="Chemicals used in the process (with automatic PubChem/CAS lookup)",
    )
    steps = SubSection(
        section_def=Recipe,
        repeats=True
    )
    data_file = Quantity(
        type=str,
        a_browser={"adaptor": "RawFileAdaptor"},
        a_eln={"component": "FileEditQuantity"},
    )
    process_time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='seconds',
    )
    CalciumNitrate_Complex = Quantity(
        type=np.float64,
        shape=['*'],
        unit='milliliter', #display attribute
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
    Stirring_Speed = Quantity(
        type=np.float64,
        shape=['*'],
        unit='rpm',
    )
    Temperature = Quantity(
        type=np.float64,
        shape=['*'],
        unit='celsius',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        '''
        The normalizer for the `MRO005` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)

        if self.data_file:
            # Process Excel data and create plots
            data_result = MRO005Normalizer.process_excel_data(archive, self.data_file, logger)
            
            # Set the processed data
            self.process_time = data_result['process_time']
            self.CalciumNitrate_Complex = data_result['calcium_nitrate_complex']
            self.Conductivity = data_result['conductivity']
            self.pH = data_result['ph']
            self.Stirring_Speed = data_result['stirring_speed']
            self.Temperature = data_result['temperature']
            self.figures.append(data_result['figure'])

            # Process recipe data
            self.steps = MRO005Normalizer.process_recipe_data(archive, self.data_file, logger)

m_package.__init_metainfo__()

