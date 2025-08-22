import pdfplumber
import pandas as pd
import re
from io import StringIO

def extract_recipe_from_pdf(pdf_path):
    """
    Extracts recipe data from a PDF file with proper multi-line handling.
    
    Args:
        pdf_path (str): The file path to the PDF document.
        
    Returns:
        pandas.DataFrame: DataFrame containing recipe data with columns:
        '#', 'Action/Annotation', 'Start Time', 'End Time'
    """
    # Extract all text from PDF
    raw_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text += page.extract_text() + "\n"

    # Split the raw text into lines
    lines = raw_text.split('\n')
    
    # Find section boundaries
    recipe_start = None
    trend_start = None
    
    for i, line in enumerate(lines):
        if line.strip() == "4 Recipe":
            recipe_start = i
        elif line.strip() == "5 Trend Graphs":
            trend_start = i
    
    # Extract recipe section
    recipe_lines = lines[recipe_start:trend_start] if recipe_start is not None and trend_start is not None else []
    
    # Process Recipe section
    recipe_data = []
    if recipe_lines:
        # Skip the header line "4 Recipe"
        recipe_lines = recipe_lines[1:]
        
        # Find the header row
        header_found = False
        data_start = 0
        
        for i, line in enumerate(recipe_lines):
            if "#" in line and "Action" in line and "Start" in line and "End" in line:
                header_found = True
                data_start = i + 1
                break
        
        if header_found:
            # First, let's reconstruct the full multi-line entries
            full_entries = []
            current_entry = ""
            
            for line in recipe_lines[data_start:]:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a new step (starts with a number)
                if re.match(r'^\d+\s', line):
                    # Save previous entry if exists
                    if current_entry:
                        full_entries.append(current_entry.strip())
                    
                    # Start new entry
                    current_entry = line
                else:
                    # Continuation of previous entry
                    if current_entry:
                        current_entry += " " + line
            
            # Add the last entry
            if current_entry:
                full_entries.append(current_entry.strip())
            
            # Now process the full entries
            for entry in full_entries:
                # Parse step number
                step_match = re.match(r'^(\d+)\s+(.+)', entry)
                if step_match:
                    step_num = step_match.group(1)
                    remaining = step_match.group(2)
                    
                    # Look for time patterns (HH:MM:SS) - these are the process times
                    time_pattern = r'(\d{2}:\d{2}:\d{2})'
                    times = re.findall(time_pattern, remaining)
                    
                    if len(times) >= 2:
                        # The LAST two times are the process start and end times
                        start_time = times[-2]  # Second to last
                        end_time = times[-1]    # Last
                        
                        # Remove the process times from the end of the action text
                        # We need to remove the last two time patterns from the end
                        action_text = remaining
                        
                        # Use regex to find the pattern: text time1 time2 continuation_text
                        # The format is always: action_text start_time end_time [continuation_text]
                        time_pattern = r'(\d{2}:\d{2}:\d{2})'
                        
                        # Find all time matches with their positions
                        time_matches = list(re.finditer(time_pattern, action_text))
                        
                        if len(time_matches) >= 2:
                            # Get the last two time matches
                            last_time_match = time_matches[-1]
                            second_last_time_match = time_matches[-2]
                            
                            # The action text ends at the start of the start_time
                            action_text_before_times = action_text[:second_last_time_match.start()].strip()
                            # Check if there is text after the end_time
                            text_after_end_time = action_text[last_time_match.end():].strip()
                            
                            # Combine the action text with any continuation text
                            if text_after_end_time:
                                action_text = action_text_before_times + " " + text_after_end_time
                            else:
                                action_text = action_text_before_times
                    else:
                        start_time = ""
                        end_time = ""
                        action_text = remaining
                    
                    recipe_data.append({
                        '#': step_num,
                        'Action/Annotation': action_text,
                        'Start Time': start_time,
                        'End Time': end_time
                    })
    
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

    # Extract all text from PDF
    raw_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text += page.extract_text() + "\n"

    # Split the raw text into lines
    lines = raw_text.split('\n')
    
    # Find section boundaries
    chemistry_start = None
    setup_start = None
    recipe_start = None
    trend_start = None
    
    for i, line in enumerate(lines):
        if line.strip() == "2 Chemistry":
            chemistry_start = i
        elif line.strip() == "3 Setup":
            setup_start = i
        elif line.strip() == "4 Recipe":
            recipe_start = i
        elif line.strip() == "5 Trend Graphs":
            trend_start = i
    
    # Extract sections
    chemistry_lines = lines[chemistry_start:setup_start] if chemistry_start is not None and setup_start is not None else []
    setup_lines = lines[setup_start:recipe_start] if setup_start is not None and recipe_start is not None else []
    recipe_lines = lines[recipe_start:trend_start] if recipe_start is not None and trend_start is not None else []
    
    # Process Chemistry section
    chemistry_data = []
    if chemistry_lines:
        # Skip the header line "2 Chemistry"
        chemistry_lines = chemistry_lines[1:]
        
        # Process data rows (skip the two header lines)
        for line in chemistry_lines[2:]:
            line = line.strip()
            if not line:
                continue
            
            # Split by single spaces and handle the data structure
            parts = line.split()
            
            if len(parts) >= 8:
                # Parse the chemistry data structure
                # Example: "Eu(NO3)3 in EtOH Other 50 g/mol - 0 0 g 100 w/w%"
                
                # Start from the end and work backwards
                conc_notes = parts[-1]  # "w/w%"
                actual_amount_num = parts[-2]  # "100"
                actual_amount_unit = parts[-3]  # "g"
                actual_moles = parts[-4]  # "0" or "0.4" or "0.1"
                stoic_coeff = parts[-5]  # "-"
                mol_weight = parts[-6] + " " + parts[-7]  # "50 g/mol" or "79.102 g/mol"
                type_col = parts[-8]  # "Other"
                
                # Everything before that is the chemical name
                chemical_name = ' '.join(parts[:-8])
                
                chemistry_data.append({
                    'Chemical': chemical_name,
                    'Type': type_col,
                    'Mol Weight': mol_weight,
                    'Stoic. Coeff': stoic_coeff,
                    'Actual Moles': actual_moles,
                    'Actual Amount': actual_amount_num + " " + actual_amount_unit,
                    'Conc. Notes': conc_notes
                })
    
    df_chemistry = pd.DataFrame(chemistry_data)
    
    # Process Setup section
    setup_data = []
    if setup_lines:
        # Skip the header line "3 Setup"
        setup_lines = setup_lines[1:]
        
        current_component = None
        current_description = ""
        
        for line in setup_lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a new component (starts with a word followed by colon)
            if re.match(r'^[A-Za-z]+\s*:', line):
                # Save previous component if exists
                if current_component:
                    setup_data.append({
                        'Component': current_component,
                        'Description': current_description.strip()
                    })
                
                # Parse new component
                parts = line.split(':', 1)
                current_component = parts[0].strip()
                current_description = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Check if this is a standalone component (no colon)
                if not current_component and line and not line.endswith('Description'):
                    current_component = line
                    current_description = ""
                elif current_component:
                    # Continuation of description
                    current_description += " " + line
        
        # Add the last component
        if current_component:
            setup_data.append({
                'Component': current_component,
                'Description': current_description.strip()
            })
    
    df_setup = pd.DataFrame(setup_data)
    
    # Process Recipe section
    recipe_data = []
    if recipe_lines:
        # Skip the header line "4 Recipe"
        recipe_lines = recipe_lines[1:]
        
        # Find the header row
        header_found = False
        data_start = 0
        
        for i, line in enumerate(recipe_lines):
            if "#" in line and "Action" in line and "Start" in line and "End" in line:
                header_found = True
                data_start = i + 1
                break
        
        if header_found:
            # First, let's reconstruct the full multi-line entries
            full_entries = []
            current_entry = ""
            
            for line in recipe_lines[data_start:]:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a new step (starts with a number)
                if re.match(r'^\d+\s', line):
                    # Save previous entry if exists
                    if current_entry:
                        full_entries.append(current_entry.strip())
                    
                    # Start new entry
                    current_entry = line
                else:
                    # Continuation of previous entry
                    if current_entry:
                        current_entry += " " + line
            
            # Add the last entry
            if current_entry:
                full_entries.append(current_entry.strip())
            
            # Now process the full entries
            for entry in full_entries:
                # Parse step number
                step_match = re.match(r'^(\d+)\s+(.+)', entry)
                if step_match:
                    step_num = step_match.group(1)
                    remaining = step_match.group(2)
                    
                    # Look for time patterns (HH:MM:SS) - these are the process times
                    time_pattern = r'(\d{2}:\d{2}:\d{2})'
                    times = re.findall(time_pattern, remaining)
                    
                    if len(times) >= 2:
                        # The LAST two times are the process start and end times
                        start_time = times[-2]  # Second to last
                        end_time = times[-1]    # Last
                        
                        # Remove the process times from the end of the action text
                        # We need to remove the last two time patterns from the end
                        action_text = remaining
                        
                        # Use regex to find the pattern: text time1 time2 continuation_text
                        # The format is always: action_text start_time end_time [continuation_text]
                        time_pattern = r'(\d{2}:\d{2}:\d{2})'
                        
                        # Find all time matches with their positions
                        time_matches = list(re.finditer(time_pattern, action_text))
                        
                        if len(time_matches) >= 2:
                            # Get the last two time matches
                            last_time_match = time_matches[-1]
                            second_last_time_match = time_matches[-2]
                            
                            # The action text ends at the start of the second-to-last time
                            action_text = action_text[:second_last_time_match.start()].strip()
                    else:
                        start_time = ""
                        end_time = ""
                        action_text = remaining
                    
                    recipe_data.append({
                        '#': step_num,
                        'Action/Annotation': action_text,
                        'Start Time': start_time,
                        'End Time': end_time
                    })
    
    df_recipe = pd.DataFrame(recipe_data)
    
    return df_chemistry, df_setup, df_recipe

if __name__ == '__main__':
    # You will need to replace this with the actual path to your PDF file.
    file_path = "Report.pdf" 
    try:
        df_chemistry, df_setup, df_recipe = extract_tables_from_report(file_path)

        print("--- Chemistry ---")
        print(df_chemistry)
        print("\n--- Setup ---")
        print(df_setup)
        print("\n--- Recipe ---")
        print(df_recipe)
        
        # Show full content without truncation
        print("\n" + "="*80)
        print("FULL CONTENT VERIFICATION:")
        print("="*80)
        
        print("\n--- Chemistry (Full Content) ---")
        if not df_chemistry.empty:
            for idx, row in df_chemistry.iterrows():
                print(f"Row {idx}:")
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print("Chemistry DataFrame is empty")
        
        print("\n--- Setup (Full Content) ---")
        if not df_setup.empty:
            for idx, row in df_setup.iterrows():
                print(f"Row {idx}:")
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print("Setup DataFrame is empty")
        
        print("\n--- Recipe (Full Content) ---")
        if not df_recipe.empty:
            for idx, row in df_recipe.iterrows():
                print(f"Row {idx}:")
                for col, value in row.items():
                    print(f"  {col}: '{value}'")
                print()
        else:
            print("Recipe DataFrame is empty")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()