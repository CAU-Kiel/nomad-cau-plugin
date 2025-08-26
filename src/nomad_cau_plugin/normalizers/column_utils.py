def find_calcium_nitrate_column(df):
    """
    Find the column that starts with 'Ca(NO3)2' in the dataframe.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        str: Column name that starts with 'Ca(NO3)2' or None if not found
    """
    for col in df.columns:
        if col.startswith('Ca(NO3)2'):
            return col
    return None

def find_column_by_pattern(df, pattern):
    """
    Find a column that matches a specific pattern.
    
    Args:
        df: pandas DataFrame
        pattern: str pattern to match (e.g., 'Ca(NO3)2', 'Leitfähigkeit')
        
    Returns:
        str: Column name that matches the pattern or None if not found
    """
    for col in df.columns:
        if pattern in col:
            return col
    return None

def find_conductivity_column(df):
    """
    Find the conductivity column in the dataframe.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        str: Column name for conductivity or None if not found
    """
    # Try different possible conductivity column names
    conductivity_patterns = ['Leitfähigkeit', 'Conductivity', 'conductivity']
    for pattern in conductivity_patterns:
        col = find_column_by_pattern(df, pattern)
        if col:
            return col
    return None

def find_ph_column(df):
    """
    Find the pH column in the dataframe.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        str: Column name for pH or None if not found
    """
    # Try different possible pH column names
    ph_patterns = ['pH-Druck', 'pH', 'ph']
    for pattern in ph_patterns:
        col = find_column_by_pattern(df, pattern)
        if col:
            return col
    return None

def find_temperature_column(df):
    """
    Find the temperature column in the dataframe.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        str: Column name for temperature or None if not found
    """
    # Try different possible temperature column names
    temp_patterns = ['Tr', 'Temperature', 'temperature', 'Temp']
    for pattern in temp_patterns:
        col = find_column_by_pattern(df, pattern)
        if col:
            return col
    return None
