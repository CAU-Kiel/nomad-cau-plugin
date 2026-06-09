from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO

import numpy as np
import pandas as pd

MIN_REQUIRED_ROWS = 6
MIN_REQUIRED_COLUMNS = 2
DATA_START_ROW = 5


@dataclass(frozen=True)
class LuminescenceData:
    measurement_start: datetime
    time_seconds: list[float]
    wavelength_nm: list[float]
    intensity_matrix: list[list[float]]


def _decode_csv_bytes(csv_bytes: bytes) -> str:
    try:
        return csv_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return csv_bytes.decode('latin-1')


def _normalize_sheet_names(sheet_names: list[str] | None) -> list[str]:
    if not sheet_names:
        return []
    return [
        name.strip()
        for name in sheet_names
        if isinstance(name, str) and name.strip()
    ]


def _read_luminescence_table(
    file_path: str,
    file_bytes: bytes,
    sheet_names: list[str] | None = None,
) -> pd.DataFrame:
    suffix = os.path.splitext(file_path)[1].lower()
    if suffix in {'.xls', '.xlsx', '.xlsm'}:
        workbook = pd.read_excel(
            BytesIO(file_bytes),
            header=None,
            dtype=str,
            sheet_name=None,
        )
        if not workbook:
            raise ValueError('Luminescence spreadsheet does not contain any sheets.')

        requested = _normalize_sheet_names(sheet_names)
        if requested:
            for name in requested:
                if name in workbook:
                    return workbook[name]
            available = ', '.join(workbook.keys())
            requested_text = ', '.join(requested)
            raise ValueError(
                f'None of the requested sheet names were found. '
                f'Requested: {requested_text}. Available: {available}.'
            )

        return next(iter(workbook.values()))

    csv_text = _decode_csv_bytes(file_bytes)
    return pd.read_csv(StringIO(csv_text), sep=';', header=None, dtype=str)


def _parse_time_row(row: pd.Series) -> tuple[datetime, np.ndarray]:
    # Row 1, columns 2..N contain absolute timestamps.
    timestamps = pd.to_datetime(row.iloc[1:], errors='coerce')
    valid = timestamps.notna()
    if not valid.any():
        raise ValueError('No valid timestamp values found in the first row.')

    parsed = timestamps[valid]
    measurement_start = parsed.iloc[0].to_pydatetime()
    time_seconds = (
        (parsed - parsed.iloc[0]).dt.total_seconds().astype(float).to_numpy()
    )
    return measurement_start, time_seconds


def luminescence_from_csv_bytes(
    file_path: str,
    file_bytes: bytes,
    sheet_names: list[str] | None = None,
) -> LuminescenceData:
    """Parse luminescence matrix data into time, wavelength and intensity arrays.

    Expected format:
    - Row 1: column 1 is label, columns 2..N are absolute timestamps.
    - Rows 2..5: metadata, ignored.
    - From row 6: column 1 wavelength (nm), columns 2..N intensity values.
    """

    raw = _read_luminescence_table(file_path, file_bytes, sheet_names=sheet_names)

    if raw.shape[0] < MIN_REQUIRED_ROWS or raw.shape[1] < MIN_REQUIRED_COLUMNS:
        raise ValueError('Luminescence CSV does not contain required rows/columns.')

    measurement_start, time_seconds = _parse_time_row(raw.iloc[0])

    # Data starts at line 6: wavelength in first column, intensities after.
    data = raw.iloc[DATA_START_ROW:, :].copy()
    wavelength = pd.to_numeric(
        data.iloc[:, 0].str.replace(',', '.', regex=False), errors='coerce'
    )

    # Use only the same count of intensity columns as valid timestamps.
    n_times = len(time_seconds)
    intensity_cells = data.iloc[:, 1 : 1 + n_times].apply(
        lambda col: pd.to_numeric(
            col.astype(str).str.replace(',', '.', regex=False), errors='coerce'
        )
    )

    valid_rows = wavelength.notna()
    wavelength_values = wavelength[valid_rows].astype(float).to_numpy()
    intensity_matrix = intensity_cells.loc[valid_rows].to_numpy(dtype=float)

    if wavelength_values.size == 0 or intensity_matrix.size == 0:
        raise ValueError('No luminescence wavelength/intensity data found in CSV.')

    # Replace missing values with 0 to keep matrix shape consistent for plotting.
    intensity_matrix = np.nan_to_num(intensity_matrix, nan=0.0)

    return LuminescenceData(
        measurement_start=measurement_start,
        time_seconds=time_seconds.tolist(),
        wavelength_nm=wavelength_values.tolist(),
        intensity_matrix=intensity_matrix.tolist(),
    )
