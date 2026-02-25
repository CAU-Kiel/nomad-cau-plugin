import os
import tempfile

import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.units import ureg
from plotly.subplots import make_subplots

from nomad_cau_plugin.parsers.pdf_extract import extract_tables_from_report
from nomad_cau_plugin.parsers.xrd_from_cif import xrd_pattern_from_cif_bytes

from .column_utils import (
    find_calcium_nitrate_column,
    find_conductivity_column,
    find_ph_column,
    find_temperature_column,
)


class CaPNormalizer:
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
        from nomad_cau_plugin.measurements.CaP_experiments import Chemical

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
        from nomad_cau_plugin.measurements.CaP_experiments import Recipe

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

                    if (
                        len(start_parts) == TIME_PARTS_COUNT
                        and len(end_parts) == TIME_PARTS_COUNT
                    ):  # noqa: E501
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
                    chemicals = CaPNormalizer._process_chemistry_data(chemistry_df)
                    steps = CaPNormalizer._process_recipe_data(recipe_df)

                    return chemicals, steps

                finally:
                    # Clean up temporary file
                    os.unlink(tmp_file_path)

        except Exception as e:
            logger.warning(f'Failed to extract data from PDF report: {e}')
            return [], []

    @staticmethod
    def _as_list(value):
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    @staticmethod
    def _read_xyd_df(archive, path: str) -> pd.DataFrame:
        with archive.m_context.raw_file(path, 'rb') as file:
            df_local = pd.read_csv(
                file,
                delim_whitespace=True,
                header=None,
                comment='#',
                names=['two_theta', 'intensity'],
                usecols=[0, 1],
                engine='python',
            )
        df_local['two_theta'] = pd.to_numeric(
            df_local['two_theta'], errors='coerce'
        )
        df_local['intensity'] = pd.to_numeric(
            df_local['intensity'], errors='coerce'
        )
        return df_local.dropna(subset=['two_theta', 'intensity'])

    @staticmethod
    def _read_cif_as_pattern_df(
        archive, path: str, *, two_theta_range: tuple[float, float] | None = None
    ) -> pd.DataFrame:
        with archive.m_context.raw_file(path, 'rb') as file:
            cif_bytes = file.read()
        pattern = xrd_pattern_from_cif_bytes(cif_bytes, two_theta_range=two_theta_range)
        return pd.DataFrame(
            {'two_theta': pattern.two_theta, 'intensity': pattern.intensity}
        )

    @staticmethod
    def _collect_reference_dfs(
        archive,
        logger,
        reference_files: list[str],
        reference_cif_files: list[str],
        *,
        two_theta_range: tuple[float, float] | None = None,
    ) -> list[tuple[str, pd.DataFrame]]:
        reference_dfs: list[tuple[str, pd.DataFrame]] = []

        for ref_file in reference_files:
            try:
                reference_dfs.append(
                    (ref_file, CaPNormalizer._read_xyd_df(archive, ref_file))
                )
            except Exception as exc:
                logger.warning(f'Failed to read reference XRD file {ref_file}: {exc}')

        for cif_file in reference_cif_files:
            try:
                reference_dfs.append(
                    (
                        cif_file,
                        CaPNormalizer._read_cif_as_pattern_df(
                            archive, cif_file, two_theta_range=two_theta_range
                        ),
                    )
                )
            except Exception as exc:
                logger.warning(
                    f'Failed to generate XRD pattern from CIF {cif_file}: {exc}'
                )

        return reference_dfs

    @staticmethod
    def normalize_xrd_data(
        archive,
        xrd_file,
        logger,
        reference_files=None,
        reference_cif_files=None,
    ):
        """
                Parse an XRD ``.xyd`` text file with two columns (2θ, intensity)
                and create a stacked line plot with 2θ on the x-axis.

                If reference files are provided, they will be plotted above the
                measurement using vertical offsets (no overlap), to ease comparison.

                - ``reference_files``: reference patterns as ``.xyd`` (2θ, intensity)
                - ``reference_cif_files``: reference structures as ``.cif``; a powder
                    pattern is generated via pymatgen and plotted.

        Args:
            archive: The archive containing the data.
            xrd_file: Path to the XRD data file.
            logger: Logger instance.
        """

        reference_files = CaPNormalizer._as_list(reference_files)
        reference_cif_files = CaPNormalizer._as_list(reference_cif_files)

        try:
            measurement_df = CaPNormalizer._read_xyd_df(archive, xrd_file)
        except Exception as exc:  # pragma: no cover - guarded read
            logger.error(f'Failed to read XRD data file {xrd_file}: {exc}')
            raise

        # Generate references in the same 2θ range as the measurement so the
        # stacked comparison always overlaps in x.
        measurement_two_theta_min = float(measurement_df['two_theta'].min())
        measurement_two_theta_max = float(measurement_df['two_theta'].max())
        reference_two_theta_range = (
            measurement_two_theta_min,
            measurement_two_theta_max,
        )

        reference_dfs = CaPNormalizer._collect_reference_dfs(
            archive,
            logger,
            reference_files,
            reference_cif_files,
            two_theta_range=reference_two_theta_range,
        )

        # Build stacked plot: measurement at the bottom, references above.
        datasets = [(xrd_file, measurement_df)] + reference_dfs

        # Filter out empty datasets to avoid blank subplots.
        non_empty_datasets: list[tuple[str, pd.DataFrame]] = []
        for path, df_local in datasets:
            if not df_local.empty:
                non_empty_datasets.append((path, df_local))
        if not non_empty_datasets:
            non_empty_datasets = [(xrd_file, measurement_df)]

        subplot_titles = [
            os.path.splitext(os.path.basename(path))[0]
            for path, _ in non_empty_datasets
        ]

        fig = make_subplots(
            rows=len(non_empty_datasets),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=subplot_titles,
        )

        # Plot normalized intensities so measurement and reference are comparable.
        global_min, global_max = 0.0, 1.05

        x_min = None
        x_max = None
        for _, df_local in non_empty_datasets:
            if df_local.empty:
                continue
            min_val = float(df_local['two_theta'].min())
            max_val = float(df_local['two_theta'].max())
            x_min = min_val if x_min is None else min(x_min, min_val)
            x_max = max_val if x_max is None else max(x_max, max_val)

        for row_idx, (path, df_local) in enumerate(non_empty_datasets, start=1):
            two_theta = df_local['two_theta'].to_numpy()
            intensity = df_local['intensity'].to_numpy()
            intensity_max = float(pd.Series(intensity).max()) if intensity.size else 0.0
            intensity_plot = (
                intensity / intensity_max
                if intensity_max and intensity_max > 0
                else intensity
            )
            trace_name = os.path.splitext(os.path.basename(path))[0]

            fig.add_trace(
                go.Scatter(
                    x=two_theta,
                    y=intensity_plot,
                    mode='lines',
                    name=trace_name,
                ),
                row=row_idx,
                col=1,
            )
            fig.update_yaxes(
                title_text='Intensity (a.u.)',
                range=[global_min, global_max],
                row=row_idx,
                col=1,
            )

        fig.update_xaxes(title_text='2θ (degrees)', row=len(non_empty_datasets), col=1)
        if x_min is not None and x_max is not None:
            fig.update_xaxes(range=[x_min, x_max])
        fig.update_layout(title='XRD Pattern', showlegend=False)

        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}

        # Return measurement arrays for downstream use, plus optional reference info.
        two_theta_out = measurement_df['two_theta'].to_numpy()
        intensity_out = measurement_df['intensity'].to_numpy()

        return {
            'two_theta': two_theta_out,
            'intensity': intensity_out,
            'reference_files': [p for p, _ in reference_dfs],
            'reference_xyd_files': reference_files,
            'reference_cif_files': reference_cif_files,
            'figure': PlotlyFigure(
                label='XRD Pattern',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }

    # Alias for the measurement class naming
    process_xrd_file = normalize_xrd_data