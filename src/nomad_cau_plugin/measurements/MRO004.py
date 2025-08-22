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
import pandas as pd
import plotly.graph_objs as go
import pdfplumber
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.basesections import ProcessStep
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import (
    Datetime,
    Package,
    Quantity,
    Section,
    SubSection,
)
from nomad.units import ureg
from plotly.subplots import make_subplots

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

m_package = Package(name='MRO005 archive schema')

# Import the recipe extraction function from pdf_extract.py
from nomad_cau_plugin.parsers.pdf_extract import extract_recipe_from_pdf

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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the 'Recipe' class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

class MRO004(PlotSection, EntryData, ArchiveSection):
    '''
    Class updated to use plotly_graph_object annotation.
    '''
    m_def = Section()
    steps = SubSection(
        section_def=Recipe,
        repeats=True
    )
    data_file = Quantity(
        type=str,
        a_browser={"adaptor": "RawFileAdaptor"},
        a_eln={"component": "FileEditQuantity"},
    )
    recipe_file = Quantity(
        type=str,
        description='PDF file containing recipe information',
        a_browser={"adaptor": "RawFileAdaptor"},
        a_eln={"component": "FileEditQuantity"},
    )
    process_time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='seconds',
    )
    CalciumPhosphate_CeriumNitrate = Quantity(
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
        The normalizer for the `MRO004` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)

        if self.data_file:
            with archive.m_context.raw_file(self.data_file, 'rb') as file:
                df = pd.read_csv(file, skiprows=[1], decimal=',',sep=r'\t|;',)
            df = df.drop(df.columns[0], axis=1)
            df['Experiment Time'] = pd.to_timedelta(df['Experiment Time'])
            dt_duration = df['Experiment Time'].dt.total_seconds().to_numpy()
            self.process_time = ureg.Quantity(dt_duration, 'seconds')
            #self.process_time = df['Experiment Time']
            self.CalciumPhosphate_CeriumNitrate = df['Ca(NO3)2 Ce(NO3)3.TotalVolume']
            self.Conductivity = df['Leitfähigkeit']
            self.pH = df['pH-Druck']
            #self.Stirring_Speed = df['R']
            self.Temperature = df['Tr']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(x=self.process_time,
                            y=self.CalciumPhosphate_CeriumNitrate ,
                            name = 'CalciumPhosphate_CeriumNitrate',
                            yaxis='y')
            )
            fig.add_trace(
                go.Scatter(x=self.process_time, y=self.Conductivity,
                        name='Conductivity', yaxis='y2'),
                        secondary_y=True,
            )
            fig.add_trace(
                go.Scatter(x=self.process_time, y=self.pH,
                        name='pH', yaxis='y3'),
            )
            #fig.add_trace(go.Scatter(x=self.process_time, y=self.Stirring_Speed, name='Stirring_Speed', yaxis='y4'),)
            fig.add_trace(
                go.Scatter(x=self.process_time, y=self.Temperature,
                        name='Temperature', yaxis='y4'),
            )
            fig.update_layout(
                title='Process Parameters Over Time',
                xaxis=dict(title='Process Time (s)'),
                yaxis=dict(title='CalciumPhosphate_CeriumNitrate (ml)',
                           titlefont=dict(color='blue'),
                           tickfont=dict(color='blue')),
                yaxis2=dict(title='Conductivity (mS/cm)', titlefont=dict(color='red'),
                            tickfont=dict(color='red'),
                            overlaying='y', side='right'),
                yaxis3=dict(title='pH', titlefont=dict(color='green'),
                            tickfont=dict(color='green'),
                            overlaying='y', side='left', position=0.05),
                #yaxis4=dict(title='Stirring Speed (rpm)', titlefont=dict(color='orange'),
                            #tickfont=dict(color='orange'),
                            #overlaying='y', side='right', position=0.95),
                yaxis4=dict(title='Temperature (°C)', titlefont=dict(color='purple'),
                            tickfont=dict(color='purple'),
                            overlaying='y', side='left', position=0.15),
            )
            figure_json = fig.to_plotly_json()
            figure_json['config'] = {'staticPlot': True}
            self.figures.append(PlotlyFigure(label='Process Parameters Over Time',
                                             index=0,
                                             figure=figure_json,
                                             open=True))

        # Extract recipe from PDF file
        if self.recipe_file:
            try:
                with archive.m_context.raw_file(self.recipe_file, 'rb') as file:
                    # Create a temporary file path for pdfplumber
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(file.read())
                        tmp_file_path = tmp_file.name
                    
                    try:
                        recipe_df = extract_recipe_from_pdf(tmp_file_path)
                        
                        steps = []
                        for i, row in recipe_df.iterrows():
                            step = Recipe()
                            step.name = 'step ' + str(row['#'])
                            step.action = row['Action/Annotation']
                            
                            # Calculate duration from start and end times
                            if row['Start Time'] and row['End Time']:
                                try:
                                    # Parse time strings (HH:MM:SS format)
                                    start_parts = row['Start Time'].split(':')
                                    end_parts = row['End Time'].split(':')
                                    
                                    if len(start_parts) == 3 and len(end_parts) == 3:
                                        start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + int(start_parts[2])
                                        end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + int(end_parts[2])
                                        duration_seconds = end_seconds - start_seconds
                                        step.duration = ureg.Quantity(duration_seconds, 'seconds')
                                    else:
                                        step.duration = ureg.Quantity(0, 'seconds')
                                except:
                                    step.duration = ureg.Quantity(0, 'seconds')
                            else:
                                step.duration = ureg.Quantity(0, 'seconds')
                            
                            # Set start and end times (these are the process times from the PDF)
                            step.start_time = row['Start Time'] if row['Start Time'] else None
                            step.end_time = row['End Time'] if row['End Time'] else None
                            
                            steps.append(step)
                        
                        self.steps = steps
                        
                    finally:
                        # Clean up temporary file
                        os.unlink(tmp_file_path)
                        
            except Exception as e:
                logger.warning(f"Failed to extract recipe from PDF: {e}")

m_package.__init_metainfo__()

