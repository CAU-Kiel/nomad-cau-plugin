import os
import tempfile

import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.units import ureg
from plotly.subplots import make_subplots

from nomad_cau_plugin.parsers.pdf_extract import extract_tables_from_report

from .column_utils import (
    find_calcium_nitrate_column,
    find_conductivity_column,
    find_ph_column,
    find_temperature_column,
)


class MRO004Normalizer:
    """
    Normalizer for MRO004 measurement data.
    Handles CSV data processing and PDF report extraction.
    """

    @staticmethod
    def process_csv_data(archive, data_file, logger):
        """
        Process CSV data file and create plots.

        Args:
            archive: The archive containing the data
            data_file: Path to the CSV data file
            logger: Logger instance
        """
        with archive.m_context.raw_file(data_file, 'rb') as file:
            # Try different encodings to handle German characters
            try:
                df = pd.read_csv(
                    file, skiprows=[1], decimal=',', sep=r'\t|;', encoding='utf-8'
                )
                logger.info('Successfully read CSV file with UTF-8 encoding')
            except UnicodeDecodeError:
                # If UTF-8 fails, try with latin-1 encoding (common for German files)
                file.seek(0)  # Reset file pointer
                try:
                    df = pd.read_csv(
                        file, skiprows=[1], decimal=',', sep=r'\t|;', encoding='latin-1'
                    )
                    logger.info('Successfully read CSV file with latin-1 encoding')
                except Exception as e:
                    logger.error(
                        f'Failed to read CSV file with both UTF-8 and latin-1 encodings: {e}'  # noqa: E501
                    )
                    raise

        df = df.drop(df.columns[0], axis=1)
        df['Experiment Time'] = pd.to_timedelta(df['Experiment Time'])
        dt_duration = df['Experiment Time'].dt.total_seconds().to_numpy()

        # Create quantities
        process_time = ureg.Quantity(dt_duration, 'seconds')

        # Find calcium nitrate column dynamically
        calcium_nitrate_col = find_calcium_nitrate_column(df)
        if calcium_nitrate_col is None:
            logger.error(f'Available columns: {list(df.columns)}')
            raise ValueError("No column starting with 'Ca(NO3)2' found in the data")
        calcium_nitrate_complex = df[calcium_nitrate_col]
        # Store the actual column name for display purposes
        calcium_nitrate_display_name = calcium_nitrate_col
        logger.info(f'Found calcium nitrate column: {calcium_nitrate_col}')

        # Find other columns dynamically
        conductivity_col = find_conductivity_column(df)
        if conductivity_col is None:
            logger.error(f'Available columns: {list(df.columns)}')
            raise ValueError('No conductivity column found in the data')
        conductivity = df[conductivity_col]
        logger.info(f'Found conductivity column: {conductivity_col}')

        ph_col = find_ph_column(df)
        if ph_col is None:
            logger.error(f'Available columns: {list(df.columns)}')
            raise ValueError('No pH column found in the data')
        ph = df[ph_col]
        logger.info(f'Found pH column: {ph_col}')

        temp_col = find_temperature_column(df)
        if temp_col is None:
            logger.error(f'Available columns: {list(df.columns)}')
            raise ValueError('No temperature column found in the data')
        temperature = df[temp_col]
        logger.info(f'Found temperature column: {temp_col}')

        # Create plot
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(
            go.Scatter(
                x=process_time,
                y=calcium_nitrate_complex,
                name=calcium_nitrate_display_name,
                yaxis='y',
            )
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=conductivity, name='Conductivity', yaxis='y2'),
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=ph, name='pH', yaxis='y3'),
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=temperature, name='Temperature', yaxis='y4'),
        )
        fig.update_layout(
            title='Process Parameters Over Time',
            xaxis=dict(title='Process Time (s)'),
            yaxis=dict(
                title=f'{calcium_nitrate_display_name} (ml)',
                titlefont=dict(color='blue'),
                tickfont=dict(color='blue'),
            ),
            yaxis2=dict(
                title='Conductivity (mS/cm)',
                titlefont=dict(color='red'),
                tickfont=dict(color='red'),
                overlaying='y',
                side='right',
            ),
            yaxis3=dict(
                title='pH',
                titlefont=dict(color='green'),
                tickfont=dict(color='green'),
                overlaying='y',
                side='left',
                position=0.05,
            ),
            yaxis4=dict(
                title='Temperature (°C)',
                titlefont=dict(color='purple'),
                tickfont=dict(color='purple'),
                overlaying='y',
                side='left',
                position=0.15,
            ),
        )
        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}

        return {
            'process_time': process_time,
            'calcium_nitrate_complex': calcium_nitrate_complex,
            'calcium_nitrate_display_name': calcium_nitrate_display_name,
            'conductivity': conductivity,
            'ph': ph,
            'temperature': temperature,
            'figure': PlotlyFigure(
                label='Process Parameters Over Time',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }

    @staticmethod
    def _process_chemistry_data(chemistry_df):
        """Extract chemical data from chemistry dataframe."""
        from nomad_cau_plugin.measurements.MRO004 import Chemical

        chemicals = []
        if chemistry_df.empty:
            return chemicals

        for i, row in chemistry_df.iterrows():
            chemical = Chemical()
            chemical.name = row['Chemical']
            chemical.chemical_name = row['Chemical']

            # Parse molecular weight
            try:
                mol_weight_value = float(row['Mol Weight'].split()[0])
                chemical.mol_weight = ureg.Quantity(mol_weight_value, 'g/mol')
            except Exception:
                chemical.mol_weight = ureg.Quantity(0, 'g/mol')

            # Parse actual moles
            try:
                actual_moles_value = float(row['Actual Moles'].split()[0])
                chemical.actual_moles = ureg.Quantity(actual_moles_value, 'mol')
            except Exception:
                chemical.actual_moles = ureg.Quantity(0, 'mol')

            # Parse actual amount
            try:
                actual_amount_value = float(row['Actual Amount'].split()[0])
                chemical.actual_amount = ureg.Quantity(actual_amount_value, 'g')
            except Exception:
                chemical.actual_amount = ureg.Quantity(0, 'g')

            # Parse concentration
            try:
                chemical.concentration = row['Concentration'].split()[0]
            except Exception:
                chemical.concentration = ''

            chemicals.append(chemical)

        return chemicals

    @staticmethod
    def _process_recipe_data(recipe_df):
        """Extract recipe steps from recipe dataframe."""
        from nomad_cau_plugin.measurements.MRO004 import Recipe

        TIME_PARTS_COUNT = 3
        steps = []

        for i, row in recipe_df.iterrows():
            step = Recipe()
            step.name = 'step ' + str(row['#'])
            step.action = row['Action/Annotation']

            # Calculate duration from start and end times
            if row['Start Time'] and row['End Time']:
                try:
                    start_parts = row['Start Time'].split(':')
                    end_parts = row['End Time'].split(':')

                    if len(start_parts) == TIME_PARTS_COUNT and len(end_parts) == TIME_PARTS_COUNT:  # noqa: E501
                        start_seconds = (
                            int(start_parts[0]) * 3600
                            + int(start_parts[1]) * 60
                            + int(start_parts[2])
                        )
                        end_seconds = (
                            int(end_parts[0]) * 3600
                            + int(end_parts[1]) * 60
                            + int(end_parts[2])
                        )
                        duration_seconds = end_seconds - start_seconds
                        step.duration = ureg.Quantity(duration_seconds, 'seconds')
                    else:
                        step.duration = ureg.Quantity(0, 'seconds')
                except Exception:
                    step.duration = ureg.Quantity(0, 'seconds')
            else:
                step.duration = ureg.Quantity(0, 'seconds')

            # Set start and end times
            step.start_time = row['Start Time'] if row['Start Time'] else None
            step.end_time = row['End Time'] if row['End Time'] else None

            steps.append(step)

        return steps

    @staticmethod
    def process_pdf_report(archive, report_file, logger):
        """
        Process PDF report file and extract chemistry and recipe data.

        Args:
            archive: The archive containing the data
            report_file: Path to the PDF report file
            logger: Logger instance

        Returns:
            tuple: (chemicals, steps) - lists of Chemical and Recipe objects
        """
        try:
            with archive.m_context.raw_file(report_file, 'rb') as file:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix='.pdf'
                ) as tmp_file:
                    tmp_file.write(file.read())
                    tmp_file_path = tmp_file.name

                try:
                    # Extract both chemistry and recipe data
                    chemistry_df, setup_df, recipe_df = extract_tables_from_report(
                        tmp_file_path
                    )

                    # Process chemistry and recipe data
                    chemicals = MRO004Normalizer._process_chemistry_data(chemistry_df)
                    steps = MRO004Normalizer._process_recipe_data(recipe_df)

                    return chemicals, steps

                finally:
                    # Clean up temporary file
                    os.unlink(tmp_file_path)

        except Exception as e:
            logger.warning(f'Failed to extract data from PDF report: {e}')
            return [], []
