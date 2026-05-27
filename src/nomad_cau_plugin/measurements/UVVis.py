from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.eln import ElnBaseSection
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Package, Quantity, Section

from nomad_cau_plugin.normalizers.uvvis_normalizer import UVVisNormalizer

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='UV-Vis archive schema')


class UVVisMeasurement(PlotSection, ElnBaseSection, EntryData, ArchiveSection):
    m_def = Section(
        a_eln={
            'properties': {
                'order': [
                    'name',
                    'data_file',
                    'selected_trace',
                    'available_traces',
                    'x_axis_label',
                    'y_axis_label',
                    'x_values',
                    'y_values',
                ]
            }
        },
    )

    data_file = Quantity(
        type=str,
        description='UV-Vis spreadsheet containing paired x/y columns.',
        a_browser={'adaptor': 'RawFileAdaptor'},
        a_eln={'component': 'FileEditQuantity'},
    )
    selected_trace = Quantity(
        type=str,
        description='First-row header to plot. Leave empty to use the first trace.',
        a_eln={'component': 'StringEditQuantity'},
    )
    available_traces = Quantity(
        type=str,
        shape=['*'],
        description='Trace headers detected from the first row of the spreadsheet.',
    )
    x_axis_label = Quantity(
        type=str,
        description='Label parsed from the second row for the x-axis.',
    )
    y_axis_label = Quantity(
        type=str,
        description='Label parsed from the second row for the y-axis.',
    )
    x_values = Quantity(
        type=np.float64,
        shape=['*'],
        description='Selected trace x values.',
    )
    y_values = Quantity(
        type=np.float64,
        shape=['*'],
        description='Selected trace y values.',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if not self.data_file:
            return

        result = UVVisNormalizer.process_uvvis_data(
            archive,
            self.data_file,
            logger,
            selected_trace=self.selected_trace,
        )
        self.available_traces = result['available_traces']
        self.selected_trace = result['selected_trace']
        self.x_axis_label = result['x_axis_label']
        self.y_axis_label = result['y_axis_label']
        self.x_values = result['x_values']
        self.y_values = result['y_values']
        self.figures.append(result['figure'])


m_package.__init_metainfo__()