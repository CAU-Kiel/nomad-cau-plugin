import os
import tempfile

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.units import ureg
from plotly.subplots import make_subplots

from nomad_cau_plugin.parsers.luminescence_csv import luminescence_from_csv_bytes
from nomad_cau_plugin.parsers.pdf_extract import extract_tables_from_report
from nomad_cau_plugin.parsers.ir_from_dpt import ir_spectrum_from_dpt_bytes
from nomad_cau_plugin.parsers.xrd_from_cif import (
    xrd_pattern_from_reference_file_bytes,
)

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

    DEFAULT_XRD_ALPHA_ANGSTROM = 1.5406

    @staticmethod
    def process_luminescence_data(archive, data_file, logger):
        """Parse luminescence CSV and build a 3D time/wavelength/intensity plot."""
        try:
            with archive.m_context.raw_file(data_file, 'rb') as file:
                parsed = luminescence_from_csv_bytes(file.read())
        except Exception as exc:  # pragma: no cover - guarded parsing
            logger.error(f'Failed to parse luminescence data file {data_file}: {exc}')
            raise

        time_seconds = parsed.time_seconds
        wavelength_nm = parsed.wavelength_nm
        intensity_matrix = parsed.intensity_matrix

        z_raw = np.asarray(intensity_matrix, dtype=float)
        x_raw = np.asarray(time_seconds, dtype=float)
        y_raw = np.asarray(wavelength_nm, dtype=float)

        # One line per timestamp: y=wavelength, z=intensity, x=fixed timestamp.
        fig = go.Figure()
        for col_idx, t_val in enumerate(x_raw):
            fig.add_trace(
                go.Scatter3d(
                    x=np.full(y_raw.shape, t_val),
                    y=y_raw,
                    z=z_raw[:, col_idx],
                    mode='lines',
                    showlegend=False,
                    line=dict(color='rgba(31, 119, 180, 0.30)', width=2),
                    hovertemplate=(
                        'time=%{x:.1f} s<br>'
                        'wavelength=%{y:.2f} nm<br>'
                        'intensity=%{z:.2f}<extra></extra>'
                    ),
                )
            )

        fig.update_layout(
            title='Luminescence 3D Map',
            scene=dict(
                xaxis_title='Measurement time (s)',
                yaxis_title='Wavelength (nm)',
                zaxis_title='Intensity',
                aspectmode='manual',
                aspectratio=dict(x=1.4, y=1.0, z=0.7),
                camera=dict(eye=dict(x=1.6, y=1.4, z=0.9)),
                xaxis=dict(nticks=10),
                yaxis=dict(nticks=10),
                zaxis=dict(nticks=8),
            ),
            margin=dict(l=20, r=20, t=50, b=20),
        )

        figure_json = fig.to_plotly_json()
        # 3D traces require WebGL; keep interaction enabled for reliable display.
        figure_json['config'] = {'staticPlot': False}

        return {
            'measurement_start_time': parsed.measurement_start,
            'measurement_start_label': parsed.measurement_start.isoformat(
                sep=' ', timespec='seconds'
            ),
            'time_seconds': time_seconds,
            'wavelength_nm': wavelength_nm,
            'intensity_matrix': intensity_matrix,
            'figure': PlotlyFigure(
                label='Luminescence 3D Map',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }

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
        archive,
        path: str,
        *,
        two_theta_range: tuple[float, float] | None = None,
        wavelength: float | None = None,
    ) -> pd.DataFrame:
        with archive.m_context.raw_file(path, 'rb') as file:
            file_bytes = file.read()
        pattern = xrd_pattern_from_reference_file_bytes(
            path,
            file_bytes,
            two_theta_range=two_theta_range,
            wavelength=wavelength,
        )
        return pd.DataFrame(
            {'two_theta': pattern.two_theta, 'intensity': pattern.intensity}
        )

    @staticmethod
    def _read_reference_pattern_df(
        archive,
        logger,
        reference_file: str,
        *,
        two_theta_range: tuple[float, float] | None = None,
        wavelength: float | None = None,
    ) -> pd.DataFrame | None:
        try:
            return CaPNormalizer._read_cif_as_pattern_df(
                archive,
                reference_file,
                two_theta_range=two_theta_range,
                wavelength=wavelength,
            )
        except Exception as exc:
            logger.warning(
                f'Failed to generate XRD pattern from reference file '
                f'{reference_file}: {exc}'
            )
            return None

    @staticmethod
    def _collect_reference_dfs(
        archive,
        logger,
        reference_files: list[str],
        *,
        two_theta_range: tuple[float, float] | None = None,
        wavelength: float | None = None,
    ) -> list[tuple[str, pd.DataFrame]]:
        reference_dfs: list[tuple[str, pd.DataFrame]] = []

        for reference_file in reference_files:
            pattern_df = CaPNormalizer._read_reference_pattern_df(
                archive,
                logger,
                reference_file,
                two_theta_range=two_theta_range,
                wavelength=wavelength,
            )
            if pattern_df is not None:
                reference_dfs.append((reference_file, pattern_df))

        return reference_dfs

    @staticmethod
    def _two_theta_to_q(two_theta: np.ndarray, wavelength: float) -> np.ndarray:
        theta_radians = np.deg2rad(np.asarray(two_theta, dtype=float) / 2.0)
        return 4.0 * np.pi * np.sin(theta_radians) / float(wavelength)

    @staticmethod
    def _to_local_maxima(df_local: pd.DataFrame) -> pd.DataFrame:
        """Return local maxima points for stick plotting."""
        if df_local.empty:
            return df_local

        ordered = df_local.sort_values('two_theta').reset_index(drop=True)
        min_points_for_interior_peaks = 2
        if len(ordered) <= min_points_for_interior_peaks:
            return ordered[ordered['intensity'] > 0]

        intensity = ordered['intensity']
        prev_vals = intensity.shift(1)
        next_vals = intensity.shift(-1)

        is_peak = (intensity >= prev_vals) & (intensity > next_vals)
        first_peak = (intensity.index == 0) & (intensity > next_vals)
        last_peak = (intensity.index == len(ordered) - 1) & (intensity > prev_vals)
        mask = (is_peak | first_peak | last_peak) & (intensity > 0)

        return ordered.loc[mask, ['two_theta', 'intensity']]

    @staticmethod
    def _sticks_from_points(df_local: pd.DataFrame) -> tuple[list[float], list[float]]:
        """Convert points to vertical-stick scatter coordinates."""
        x_sticks: list[float] = []
        y_sticks: list[float] = []
        for _, row in df_local.iterrows():
            x_val = float(row['two_theta'])
            y_val = float(row['intensity'])
            x_sticks.extend([x_val, x_val, None])
            y_sticks.extend([0.0, y_val, None])
        return x_sticks, y_sticks

    @staticmethod
    def normalize_xrd_data(
        archive,
        xrd_file,
        logger,
        reference_files=None,
        reference_cif_files=None,
        xrd_alpha=None,
    ):
        """
                Parse an XRD ``.xyd`` text file with two columns (2θ, intensity)
                and create a single overlaid comparison plot with q on x-axis.

                - Measurement is drawn as a line.
                - CIF references are drawn as local-maxima sticks (mass-spectrum
                    style) to emphasize peak positions.

                - ``reference_files``: reference structures or reference patterns as
                    ``.cif``, ``.xy``, ``.xyd``, or ``.vasp``; a powder pattern is
                    generated or read and plotted.
                - ``xrd_alpha``: optional wavelength (Angstrom) used for q conversion
                    and structure-based reference pattern computation; falls back to
                    default Cu Kα.

        Args:
            archive: The archive containing the data.
            xrd_file: Path to the XRD data file.
            logger: Logger instance.
        """

        reference_files = CaPNormalizer._as_list(
            reference_files or reference_cif_files
        )
        xrd_alpha_value = (
            float(xrd_alpha)
            if xrd_alpha is not None
            else CaPNormalizer.DEFAULT_XRD_ALPHA_ANGSTROM
        )

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

        reference_cif_dfs = CaPNormalizer._collect_reference_dfs(
            archive,
            logger,
            reference_files,
            two_theta_range=reference_two_theta_range,
            wavelength=xrd_alpha_value,
        )

        fig = go.Figure()

        # Normalize measurement for direct visual peak-position comparison.
        meas_intensity = measurement_df['intensity'].to_numpy()
        meas_max = (
            float(pd.Series(meas_intensity).max()) if meas_intensity.size else 0.0
        )
        meas_plot = (
            meas_intensity / meas_max if meas_max and meas_max > 0 else meas_intensity
        )
        measurement_name = os.path.splitext(os.path.basename(xrd_file))[0]
        measurement_q = CaPNormalizer._two_theta_to_q(
            measurement_df['two_theta'].to_numpy(),
            xrd_alpha_value,
        )
        fig.add_trace(
            go.Scatter(
                x=measurement_q,
                y=meas_plot,
                mode='lines',
                name=measurement_name,
                line=dict(color='#1f77b4', width=1.8),
            )
        )

        # CIF references are rendered as local-maximum sticks.
        cif_colors = [
            '#d62728',
            '#2ca02c',
            '#ff7f0e',
            '#9467bd',
            '#8c564b',
            '#e377c2',
            '#17becf',
            '#bcbd22',
        ]
        for idx, (cif_file, df_local) in enumerate(reference_cif_dfs):
            if df_local.empty:
                continue

            maxima_df = CaPNormalizer._to_local_maxima(df_local)
            if maxima_df.empty:
                continue

            max_intensity = float(maxima_df['intensity'].max())
            if max_intensity > 0:
                maxima_df = maxima_df.assign(
                    intensity=maxima_df['intensity'] / max_intensity
                )

            q_values = CaPNormalizer._two_theta_to_q(
                maxima_df['two_theta'].to_numpy(),
                xrd_alpha_value,
            )
            x_sticks = []
            y_sticks = []
            for x_val, y_val in zip(q_values, maxima_df['intensity'].to_numpy()):
                x_sticks.extend([float(x_val), float(x_val), None])
                y_sticks.extend([0.0, float(y_val), None])
            trace_name = os.path.splitext(os.path.basename(cif_file))[0]
            color = cif_colors[idx % len(cif_colors)]
            fig.add_trace(
                go.Scatter(
                    x=x_sticks,
                    y=y_sticks,
                    mode='lines',
                    name=trace_name,
                    line=dict(color=color, width=1.8),
                )
            )

        fig.update_layout(
            title='XRD Pattern',
            xaxis_title='q (angstrom^-1)',
            yaxis_title='Normalized intensity (a.u.)',
            yaxis=dict(range=[0.0, 1.05]),
            showlegend=True,
            legend=dict(
                x=0.99,
                y=0.99,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.75)',
                bordercolor='rgba(0,0,0,0.15)',
                borderwidth=1,
            ),
        )

        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}

        # Return measurement arrays for downstream use, plus optional reference info.
        two_theta_out = measurement_df['two_theta'].to_numpy()
        intensity_out = measurement_df['intensity'].to_numpy()

        return {
            'two_theta': two_theta_out,
            'intensity': intensity_out,
            'reference_files': [p for p, _ in reference_cif_dfs],
            'reference_xyd_files': [
                p
                for p, _ in reference_cif_dfs
                if os.path.splitext(p)[1].lower() in {'.xy', '.xyd'}
            ],
            'reference_cif_files': [
                p
                for p, _ in reference_cif_dfs
                if os.path.splitext(p)[1].lower() == '.cif'
            ],
            'reference_vasp_files': [
                p
                for p, _ in reference_cif_dfs
                if os.path.splitext(p)[1].lower() == '.vasp'
            ],
            'xrd_alpha': xrd_alpha_value,
            'figure': PlotlyFigure(
                label='XRD Pattern',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }

    @staticmethod
    def normalize_ir_data(archive, ir_file, logger):
        """
        Parse an IR .dpt file and create an IR spectrum plot.

        The .dpt format is a two-column text file with:
        - Column 1: wavenumber in cm⁻¹
        - Column 2: transmittance (typically 0-1 range)

        Creates a line plot with wavenumber on x-axis and transmittance on y-axis.

        Args:
            archive: The archive containing the data.
            ir_file: Path to the IR .dpt file.
            logger: Logger instance.

        Returns:
            dict: Contains 'wavenumber', 'transmittance', and 'figure' (PlotlyFigure).
        """
        try:
            with archive.m_context.raw_file(ir_file, 'rb') as file:
                ir_bytes = file.read()
            spectrum = ir_spectrum_from_dpt_bytes(ir_bytes)
        except Exception as exc:
            logger.error(f'Failed to read IR data file {ir_file}: {exc}')
            raise

        wavenumber_array = np.array(spectrum.wavenumber, dtype=float)
        transmittance_array = np.array(spectrum.transmittance, dtype=float)

        fig = go.Figure()

        measurement_name = os.path.splitext(os.path.basename(ir_file))[0]
        fig.add_trace(
            go.Scatter(
                x=wavenumber_array,
                y=transmittance_array,
                mode='lines',
                name=measurement_name,
                line=dict(color='#1f77b4', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 184, 0.2)',
            )
        )

        fig.update_layout(
            title='IR Spectrum',
            xaxis_title='Wavenumber (cm⁻¹)',
            yaxis_title='Transmittance (a.u.)',
            xaxis=dict(autorange='reversed'),
            showlegend=True,
            hovermode='x unified',
        )

        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}

        return {
            'wavenumber': wavenumber_array,
            'transmittance': transmittance_array,
            'figure': PlotlyFigure(
                label='IR Spectrum',
                index=0,
                figure=figure_json,
                open=True,
            ),
        }

    # Alias for the measurement class naming
    process_ir_file = normalize_ir_data

    # Alias for the measurement class naming
    process_xrd_file = normalize_xrd_data