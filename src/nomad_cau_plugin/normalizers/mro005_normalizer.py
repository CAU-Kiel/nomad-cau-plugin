import re
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from nomad.units import ureg
from nomad.datamodel.metainfo.plot import PlotlyFigure
from .column_utils import (
    find_calcium_nitrate_column, 
    find_conductivity_column, 
    find_ph_column, 
    find_temperature_column
)


class MRO005Normalizer:
    """
    Normalizer for MRO005 measurement data.
    Handles Excel data processing, chemistry extraction, and recipe extraction.
    """
    
    @staticmethod
    def process_chemistry_data(archive, data_file, logger):
        """
        Process chemistry data from Excel file (if Chemistry sheet exists).
        
        Args:
            archive: The archive containing the data
            data_file: Path to the Excel data file
            logger: Logger instance
            
        Returns:
            list: List of Chemical objects (empty if no Chemistry sheet found)
        """
        chemicals = []
        
        try:
            with archive.m_context.raw_file(data_file, 'rb') as file:
                # Try to read Chemistry sheet
                try:
                    df = pd.read_excel(file, sheet_name='Chemistry')
                    logger.info(f"Successfully read Chemistry sheet from Excel file")
                except ValueError:
                    # Chemistry sheet doesn't exist - this is OK
                    logger.info("No Chemistry sheet found in Excel file - skipping chemistry data")
                    return chemicals
                except Exception as e:
                    logger.warning(f"Could not read Chemistry sheet: {e}")
                    return chemicals
            
            # Process chemistry data if we have it
            if not df.empty:
                # Import Chemical class dynamically to avoid circular import
                from nomad_cau_plugin.measurements.MRO005 import Chemical
                
                # Assuming the Chemistry sheet has columns like:
                # 'Chemical', 'Mol Weight', 'Actual Moles', 'Actual Amount', 'Concentration'
                for i, row in df.iterrows():
                    chemical = Chemical()
                    
                    # Get chemical name from first column (adapt column name as needed)
                    chem_name_col = df.columns[0] if 'Chemical' not in df.columns else 'Chemical'
                    chemical.name = str(row[chem_name_col])
                    chemical.chemical_name = str(row[chem_name_col])
                    
                    # NOTE: PubChem/CAS database lookup happens automatically!
                    # When Chemical.normalize() is called, it will create a
                    # PubChemPureSubstanceSection with the chemical_name,
                    # which will automatically fetch molecular formula, SMILES,
                    # InChI, CAS number, and more from PubChem database.
                    
                    # Parse molecular weight if available
                    if 'Mol Weight' in df.columns or 'Molecular Weight' in df.columns:
                        mol_weight_col = 'Mol Weight' if 'Mol Weight' in df.columns else 'Molecular Weight'
                        try:
                            mol_weight_value = float(str(row[mol_weight_col]).split()[0])
                            chemical.mol_weight = ureg.Quantity(mol_weight_value, 'g/mol')
                        except:
                            pass
                    
                    # Parse actual moles if available
                    if 'Actual Moles' in df.columns:
                        try:
                            actual_moles_value = float(str(row['Actual Moles']).split()[0])
                            chemical.actual_moles = ureg.Quantity(actual_moles_value, 'mol')
                        except:
                            pass
                    
                    # Parse actual amount if available
                    if 'Actual Amount' in df.columns:
                        try:
                            actual_amount_value = float(str(row['Actual Amount']).split()[0])
                            chemical.actual_amount = ureg.Quantity(actual_amount_value, 'g')
                        except:
                            pass
                    
                    # Parse concentration if available
                    if 'Concentration' in df.columns:
                        try:
                            chemical.concentration = str(row['Concentration'])
                        except:
                            pass
                    
                    chemical.normalize()
                    chemicals.append(chemical)
                
                logger.info(f"Processed {len(chemicals)} chemicals from Excel Chemistry sheet")
        
        except Exception as e:
            logger.warning(f"Error processing chemistry data from Excel: {e}")
        
        return chemicals
    
    @staticmethod
    def process_excel_data(archive, data_file, logger):
        """
        Process Excel data file and create plots.
        
        Args:
            archive: The archive containing the data
            data_file: Path to the Excel data file
            logger: Logger instance
        """
        with archive.m_context.raw_file(data_file, 'rb') as file:
            try:
                df = pd.read_excel(file, sheet_name='Measured values')
                #df = pd.read_excel(file, sheet_name='Measured values', engine='openpyxl')
                logger.info(f"Successfully read Excel file")
            except Exception as e:
                logger.error(f"Failed to read Excel file: {e}")
                raise
        
        # Create quantities
        process_time = df['process_time']
        
        # Find calcium nitrate column dynamically
        calcium_nitrate_col = find_calcium_nitrate_column(df)
        if calcium_nitrate_col is None:
            logger.error(f"Available columns: {list(df.columns)}")
            raise ValueError("No column starting with 'Ca(NO3)2' found in the data")
        calcium_nitrate_complex = df[calcium_nitrate_col]
        # Store the actual column name for display purposes
        calcium_nitrate_display_name = calcium_nitrate_col
        logger.info(f"Found calcium nitrate column: {calcium_nitrate_col}")
        
        # Find other columns dynamically
        conductivity_col = find_conductivity_column(df)
        if conductivity_col is None:
            raise ValueError("No conductivity column found in the data")
        conductivity = df[conductivity_col]
        
        ph_col = find_ph_column(df)
        if ph_col is None:
            raise ValueError("No pH column found in the data")
        ph = df[ph_col]
        
        stirring_speed = df['R']  # Keep this as is for now
        temp_col = find_temperature_column(df)
        if temp_col is None:
            raise ValueError("No temperature column found in the data")
        temperature = df[temp_col]
        
        # Create plot
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=process_time,
                        y=calcium_nitrate_complex,
                        name=calcium_nitrate_display_name,
                        yaxis='y')
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=conductivity,
                    name='Conductivity', yaxis='y2'),
                    secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=ph,
                    name='pH', yaxis='y3'),
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=stirring_speed,
                    name='Stirring_Speed', yaxis='y4'),
        )
        fig.add_trace(
            go.Scatter(x=process_time, y=temperature,
                    name='Temperature', yaxis='y5'),
        )
        fig.update_layout(
            title='Process Parameters Over Time',
            xaxis=dict(title='Process Time (s)'),
            yaxis=dict(title=f'{calcium_nitrate_display_name} (ml)',
                       titlefont=dict(color='blue'),
                       tickfont=dict(color='blue')),
            yaxis2=dict(title='Conductivity (mS/cm)', titlefont=dict(color='red'),
                        tickfont=dict(color='red'),
                        overlaying='y', side='right'),
            yaxis3=dict(title='pH', titlefont=dict(color='green'),
                        tickfont=dict(color='green'),
                        overlaying='y', side='left', position=0.05),
            yaxis4=dict(title='Stirring Speed (rpm)', titlefont=dict(color='orange'),
                        tickfont=dict(color='orange'),
                        overlaying='y', side='right', position=0.95),
            yaxis5=dict(title='Temperature (°C)', titlefont=dict(color='purple'),
                        tickfont=dict(color='purple'),
                        overlaying='y', side='left', position=0.15),
        )
        figure_json = fig.to_plotly_json()
        figure_json['config'] = {'staticPlot': True}
        
        return {
            'process_time': process_time,
            'calcium_nitrate_complex': calcium_nitrate_complex,
            'calcium_nitrate_display_name': calcium_nitrate_display_name,
            'conductivity': conductivity,
            'ph': ph,
            'stirring_speed': stirring_speed,
            'temperature': temperature,
            'figure': PlotlyFigure(label='Process Parameters Over Time',
                                   index=0,
                                   figure=figure_json,
                                   open=True)
        }
    
    @staticmethod
    def process_recipe_data(archive, data_file, logger):
        """
        Process recipe data from Excel file.
        
        Args:
            archive: The archive containing the data
            data_file: Path to the Excel data file
            logger: Logger instance
            
        Returns:
            list: List of Recipe objects
        """
        with archive.m_context.raw_file(data_file, 'rb') as file:
            try:
                df = pd.read_excel(file, sheet_name='Recipe')
                logger.info(f"Successfully read Recipe sheet from Excel file")
            except Exception as e:
                logger.error(f"Failed to read Recipe sheet from Excel file: {e}")
                raise
        
        steps = []
        # Import Recipe class dynamically to avoid circular import
        from nomad_cau_plugin.measurements.MRO005 import Recipe
        for i, row in df.iterrows():
            step = Recipe()
            step.name = 'step ' + str(row['#'])
            step.action = row['Action / Annotation']
            
            # Calculate duration
            dt_duration = pd.to_timedelta(row['Duration']).total_seconds()
            step.duration = ureg.Quantity(dt_duration, 'seconds')
            
            # Set start and end times
            step.start_time = row['Start Time']
            step.end_time = row['End Time']
            
            # Extract temperature
            match = re.search(r'[\d.]+', str(row['Tr']))
            temperature_numeric = float(match.group()) if match else None
            step.temperature = ureg.Quantity(temperature_numeric, 'celsius')
            
            steps.append(step)
        
        return steps
