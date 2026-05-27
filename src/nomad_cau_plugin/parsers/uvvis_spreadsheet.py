from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from io import BytesIO, StringIO

import pandas as pd

MIN_UVVIS_ROWS = 3
MIN_UVVIS_COLUMNS = 2


@dataclass(frozen=True)
class UVVisTrace:
    name: str
    x_label: str
    y_label: str
    x_values: list[float]
    y_values: list[float]


def _decode_text_bytes(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1')


def _read_spreadsheet(file_path: str, file_bytes: bytes) -> pd.DataFrame:
    suffix = os.path.splitext(file_path)[1].lower()
    if suffix in {'.xls', '.xlsx', '.xlsm'}:
        return pd.read_excel(BytesIO(file_bytes), header=None, dtype=str)

    rows = list(csv.reader(StringIO(_decode_text_bytes(file_bytes)), delimiter=';'))
    if not rows:
        return pd.DataFrame()

    width = max(len(row) for row in rows)
    padded_rows = [row + [''] * (width - len(row)) for row in rows]
    return pd.DataFrame(padded_rows)


def _normalize_cell(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    text = str(value).strip()
    return '' if text.lower() == 'nan' else text


def uvvis_traces_from_spreadsheet_bytes(
    file_path: str,
    file_bytes: bytes,
) -> list[UVVisTrace]:
    raw = _read_spreadsheet(file_path, file_bytes)
    if raw.shape[0] < MIN_UVVIS_ROWS or raw.shape[1] < MIN_UVVIS_COLUMNS:
        raise ValueError('UV-Vis file does not contain enough rows or columns.')

    traces: list[UVVisTrace] = []
    for start_col in range(0, raw.shape[1] - 1, 2):
        name = _normalize_cell(raw.iat[0, start_col])
        x_label = _normalize_cell(raw.iat[1, start_col])
        y_label = _normalize_cell(raw.iat[1, start_col + 1])

        if not name:
            continue

        data = raw.iloc[2:, [start_col, start_col + 1]].copy()
        x_series = pd.to_numeric(
            data.iloc[:, 0].astype(str).str.replace(',', '.', regex=False),
            errors='coerce',
        )
        y_series = pd.to_numeric(
            data.iloc[:, 1].astype(str).str.replace(',', '.', regex=False),
            errors='coerce',
        )
        valid = x_series.notna() & y_series.notna()
        if not valid.any():
            continue

        traces.append(
            UVVisTrace(
                name=name,
                x_label=x_label,
                y_label=y_label,
                x_values=x_series[valid].astype(float).to_list(),
                y_values=y_series[valid].astype(float).to_list(),
            )
        )

    if not traces:
        raise ValueError('No valid UV-Vis traces found in spreadsheet.')

    return traces