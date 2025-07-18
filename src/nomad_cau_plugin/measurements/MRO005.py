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
        The normalizer for the `MRO005` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)

        if self.data_file:
            with archive.m_context.raw_file(self.data_file, 'rb') as file:
                df = pd.read_excel(file, sheet_name='Measured values')
            #for i, row in df.inerrows():
            self.process_time = df['process_time']
            self.CalciumPhosphate_CeriumNitrate = df['Ca(NO3)2 Ce(NO3)3']
            self.Conductivity = df['Leitfähigkeit']
            self.pH = df['pH-Druck']
            self.Stirring_Speed = df['R']
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
            fig.add_trace(
                go.Scatter(x=self.process_time, y=self.Stirring_Speed,
                        name='Stirring_Speed', yaxis='y4'),
            )
            fig.add_trace(
                go.Scatter(x=self.process_time, y=self.Temperature,
                        name='Temperature', yaxis='y5'),
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
                yaxis4=dict(title='Stirring Speed (rpm)', titlefont=dict(color='orange'),
                            tickfont=dict(color='orange'),
                            overlaying='y', side='right', position=0.95),
                yaxis5=dict(title='Temperature (°C)', titlefont=dict(color='purple'),
                            tickfont=dict(color='purple'),
                            overlaying='y', side='left', position=0.15),
            )
            figure_json = fig.to_plotly_json()
            figure_json['config'] = {'staticPlot': True}
            self.figures.append(PlotlyFigure(label='Process Parameters Over Time',
                                             index=0,
                                             figure=figure_json,
                                             open=True))

            with archive.m_context.raw_file(self.data_file, 'rb') as file:
                df = pd.read_excel(file, sheet_name='Recipe')
            dt_duration = ''
            steps = []
            for i, row in df.iterrows():
                step = Recipe()
                step.name = 'step ' + str(row['#'])
                step.action = row['Action / Annotation']
                dt_duration = pd.to_timedelta(row['Duration']).total_seconds()
                step.duration = ureg.Quantity(dt_duration, 'seconds')
                step.start_time = row['Start Time']
                step.end_time = row['End Time']
                match = re.search(r'[\d.]+', str(row['Tr']))
                temperature_numeric = float(match.group()) if match else None
                step.temperature = ureg.Quantity(
                    temperature_numeric, 'celsius'
                )
                steps.append(step)
            self.steps = steps

m_package.__init_metainfo__()

