from __future__ import annotations

import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure

from nomad_cau_plugin.parsers.uvvis_spreadsheet import (
    uvvis_traces_from_spreadsheet_bytes,
)


class UVVisNormalizer:
    @staticmethod
    def process_uvvis_data(
        archive,
        data_file,
        logger,
        selected_trace: str | None = None,
    ):
        with archive.m_context.raw_file(data_file, 'rb') as file:
            file_bytes = file.read()

        traces = uvvis_traces_from_spreadsheet_bytes(data_file, file_bytes)
        trace_names = [trace.name for trace in traces]
        chosen_name = selected_trace.strip() if isinstance(selected_trace, str) else ''
        trace = next((item for item in traces if item.name == chosen_name), traces[0])

        if chosen_name and trace.name != chosen_name:
            logger.warning(
                f'UV-Vis trace {chosen_name!r} not found in {data_file}; '
                f'using {trace.name!r} instead.'
            )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=trace.x_values,
                y=trace.y_values,
                mode='lines',
                name=trace.name,
            )
        )
        fig.update_layout(
            title=f'UV-Vis: {trace.name}',
            xaxis_title=trace.x_label or 'Wavelength',
            yaxis_title=trace.y_label or 'Signal',
            showlegend=False,
        )

        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}

        return {
            'available_traces': trace_names,
            'selected_trace': trace.name,
            'x_values': trace.x_values,
            'y_values': trace.y_values,
            'x_axis_label': trace.x_label,
            'y_axis_label': trace.y_label,
            'figure': PlotlyFigure(
                label='UV-Vis Spectrum',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }