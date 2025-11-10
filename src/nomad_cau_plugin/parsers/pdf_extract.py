import re

import pandas as pd
import pdfplumber


def _extract_text_from_pdf(pdf_path):
    raw_text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text += page.extract_text() + '\n'
    return raw_text.split('\n')


def _find_section_indices(lines, start_marker, end_marker):
    start, end = None, None
    for i, line in enumerate(lines):
        if line.strip() == start_marker:
            start = i
        elif line.strip() == end_marker:
            end = i
    return start, end


def _get_recipe_lines(lines, recipe_start, trend_start):
    if recipe_start is not None and trend_start is not None:
        return lines[recipe_start + 1 : trend_start]
    return []


def _find_recipe_header(recipe_lines):
    for i, line in enumerate(recipe_lines):
        if '#' in line and 'Action' in line and 'Start' in line and 'End' in line:
            return i + 1
    return None


def _reconstruct_entries(recipe_lines, data_start):
    full_entries = []
    current_entry = ''
    for line in recipe_lines[data_start:]:
        line = line.strip()  # noqa: PLW2901
        if not line:
            continue
        if re.match(r'^\d+\s', line):
            if current_entry:
                full_entries.append(current_entry.strip())
            current_entry = line
        elif current_entry:
            current_entry += ' ' + line
    if current_entry:
        full_entries.append(current_entry.strip())
    return full_entries


def _parse_recipe_entry(entry):
    step_match = re.match(r'^(\d+)\s+(.+)', entry)
    if not step_match:
        return None
    step_num = step_match.group(1)
    remaining = step_match.group(2)
    TIME_COUNT_FOR_PROCESS = 2
    time_pattern = r'(\d{2}:\d{2}:\d{2})'
    times = re.findall(time_pattern, remaining)
    if len(times) >= TIME_COUNT_FOR_PROCESS:
        start_time = times[-TIME_COUNT_FOR_PROCESS]
        end_time = times[-1]
        action_text = remaining
        time_matches = list(re.finditer(time_pattern, action_text))
        if len(time_matches) >= TIME_COUNT_FOR_PROCESS:
            second_last_time_match = time_matches[-TIME_COUNT_FOR_PROCESS]
            last_time_match = time_matches[-1]
            action_text_before_times = action_text[
                : second_last_time_match.start()
            ].strip()  # noqa: E501
            text_after_end_time = action_text[last_time_match.end() :].strip()
            if text_after_end_time:
                action_text = action_text_before_times + ' ' + text_after_end_time
            else:
                action_text = action_text_before_times
    else:
        start_time = ''
        end_time = ''
        action_text = remaining
    return {
        '#': step_num,
        'Action/Annotation': action_text,
        'Start Time': start_time,
        'End Time': end_time,
    }


def extract_recipe_from_pdf(pdf_path):
    """
    Extracts recipe data from a PDF file with proper multi-line handling.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        pandas.DataFrame: DataFrame containing recipe data with columns:
        '#', 'Action/Annotation', 'Start Time', 'End Time'
    """
    lines = _extract_text_from_pdf(pdf_path)
    recipe_start, trend_start = _find_section_indices(
        lines, '4 Recipe', '5 Trend Graphs'
    )
    recipe_lines = _get_recipe_lines(lines, recipe_start, trend_start)
    recipe_data = []
    if recipe_lines:
        data_start = _find_recipe_header(recipe_lines)
        if data_start is not None:
            full_entries = _reconstruct_entries(recipe_lines, data_start)
            for entry in full_entries:
                parsed = _parse_recipe_entry(entry)
                if parsed:
                    recipe_data.append(parsed)
    return pd.DataFrame(recipe_data)


def _extract_section_indices(lines):
    indices = {}
    for i, line in enumerate(lines):
        marker = line.strip()
        if marker in ['2 Chemistry', '3 Setup', '4 Recipe', '5 Trend Graphs']:
            indices[marker] = i
    return indices


def _extract_chemistry_table(chemistry_lines):
    chemistry_data = []
    if chemistry_lines:
        chemistry_lines = chemistry_lines[1:]
        for line in chemistry_lines[2:]:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            parts = stripped_line.split()
            if len(parts) >= 8:  # noqa: PLR2004
                conc_value = parts[-1]
                conc_num = parts[-2]
                actual_amount_unit = parts[-3]
                actual_amount_num = parts[-4]
                actual_moles = parts[-5]
                mol_weight_value = parts[-8]
                chemical_name_parts = parts[:-8]
                if chemical_name_parts and chemical_name_parts[-1] == 'Other':
                    chemical_name_parts = chemical_name_parts[:-1]
                chemical_name = ' '.join(chemical_name_parts)
                try:
                    actual_moles_float = float(actual_moles)
                    # actual_amount_float = float(actual_amount_num)
                    if actual_moles_float > 0:
                        chemistry_data.append(
                            {
                                'Chemical': chemical_name,
                                'Mol Weight': mol_weight_value + ' g/mol',
                                'Actual Moles': actual_moles + ' mol',
                                'Actual Amount': actual_amount_num
                                + ' '
                                + actual_amount_unit,  # noqa: E501
                                'Concentration': conc_num + ' ' + conc_value,
                            }
                        )
                except ValueError:
                    continue
    return pd.DataFrame(chemistry_data)


def _extract_setup_table(setup_lines):
    setup_data = []
    if setup_lines:
        setup_lines = setup_lines[1:]
        current_component = None
        current_description = ''
        for line in setup_lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if re.match(r'^[A-Za-z]+\s*:', stripped_line):
                if current_component:
                    setup_data.append(
                        {
                            'Component': current_component,
                            'Description': current_description.strip(),
                        }
                    )
                parts = stripped_line.split(':', 1)
                current_component = parts[0].strip()
                current_description = parts[1].strip() if len(parts) > 1 else ''
            elif (
                not current_component
                and stripped_line
                and not stripped_line.endswith('Description')
            ):  # noqa: E501
                current_component = stripped_line
                current_description = ''
            elif current_component:
                current_description += ' ' + stripped_line
        if current_component:
            setup_data.append(
                {
                    'Component': current_component,
                    'Description': current_description.strip(),
                }
            )
    return pd.DataFrame(setup_data)


def _extract_recipe_table(recipe_lines):
    recipe_data = []
    if not recipe_lines:
        return pd.DataFrame(recipe_data)

    recipe_lines = recipe_lines[1:]
    data_start = _find_recipe_header(recipe_lines)

    if data_start is not None:
        full_entries = _reconstruct_entries(recipe_lines, data_start)
        for entry in full_entries:
            parsed = _parse_recipe_entry(entry)
            if parsed:
                recipe_data.append(parsed)

    return pd.DataFrame(recipe_data)


def extract_tables_from_report(pdf_path):
    """
    Parses a PDF report to extract and structure data from the 'Chemistry',
    'Setup', and 'Recipe' sections into pandas DataFrames.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        tuple: A tuple containing three pandas DataFrames:
               (chemistry_df, setup_df, recipe_df)
    """
    raw_text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text += page.extract_text() + '\n'
    lines = raw_text.split('\n')
    indices = _extract_section_indices(lines)
    chemistry_lines = (
        lines[indices.get('2 Chemistry', 0) : indices.get('3 Setup', 0)]
        if '2 Chemistry' in indices and '3 Setup' in indices
        else []
    )  # noqa: E501
    setup_lines = (
        lines[indices.get('3 Setup', 0) : indices.get('4 Recipe', 0)]
        if '3 Setup' in indices and '4 Recipe' in indices
        else []
    )  # noqa: E501
    recipe_lines = (
        lines[indices.get('4 Recipe', 0) : indices.get('5 Trend Graphs', 0)]
        if '4 Recipe' in indices and '5 Trend Graphs' in indices
        else []
    )  # noqa: E501
    df_chemistry = _extract_chemistry_table(chemistry_lines)
    df_setup = _extract_setup_table(setup_lines)
    df_recipe = _extract_recipe_table(recipe_lines)
    return df_chemistry, df_setup, df_recipe


if __name__ == '__main__':
    # You will need to replace this with the actual path to your PDF file.
    file_path = 'Report.pdf'
    try:
        df_chemistry, df_setup, df_recipe = extract_tables_from_report(file_path)

        print('--- Chemistry ---')
        print(df_chemistry)
        print('\n--- Setup ---')
        print(df_setup)
        print('\n--- Recipe ---')
        print(df_recipe)

        # Show full content without truncation
        print('\n' + '=' * 80)
        print('FULL CONTENT VERIFICATION:')
        print('=' * 80)

        print('\n--- Chemistry (Full Content) ---')
        if not df_chemistry.empty:
            for idx, row in df_chemistry.iterrows():
                print(f'Row {idx}:')
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print('Chemistry DataFrame is empty')

        print('\n--- Setup (Full Content) ---')
        if not df_setup.empty:
            for idx, row in df_setup.iterrows():
                print(f'Row {idx}:')
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print('Setup DataFrame is empty')

        print('\n--- Recipe (Full Content) ---')
        if not df_recipe.empty:
            for idx, row in df_recipe.iterrows():
                print(f'Row {idx}:')
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print('Recipe DataFrame is empty')

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f'An error occurred: {e}')
        import traceback

        traceback.print_exc()
