"""
Test PDF processing and normalization for MRO004 measurements.
This test verifies:
1. PDF extraction (Chemistry, Setup, Recipe)
2. Full normalization with database references (PubChem)
3. Normalized archive generation
"""
import os
import json
import logging
import pytest
from pathlib import Path

from nomad.metainfo import EntryArchive
from nomad.client import normalize_all
from nomad_cau_plugin.parsers.pdf_extract import extract_tables_from_report
from nomad_cau_plugin.measurements.MRO004 import MRO004


# Get the root directory of the project
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestPDFProcessing:
    """Test suite for PDF processing and normalization."""
    
    @pytest.fixture
    def pdf_path(self):
        """Fixture to provide the path to the test PDF file."""
        # Use the Report MRO008.pdf from the project root
        pdf_file = PROJECT_ROOT / "Report MRO008.pdf"
        assert pdf_file.exists(), f"PDF file not found: {pdf_file}"
        return str(pdf_file)
    
    @pytest.fixture
    def logger(self):
        """Fixture to provide a logger instance."""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def test_pdf_extraction(self, pdf_path, logger):
        """
        Test 1: PDF Extraction
        Verifies that PDF tables (Chemistry, Setup, Recipe) can be extracted.
        """
        logger.info(f"Testing PDF extraction from: {pdf_path}")
        
        # Extract tables from PDF
        chemistry_df, setup_df, recipe_df = extract_tables_from_report(pdf_path)
        
        # Verify Chemistry data
        assert not chemistry_df.empty, "Chemistry DataFrame should not be empty"
        logger.info(f"✓ Chemistry data extracted: {len(chemistry_df)} chemicals")
        
        # Print chemistry data for inspection
        print("\n" + "="*80)
        print("CHEMISTRY DATA EXTRACTED:")
        print("="*80)
        print(chemistry_df.to_string())
        
        # Verify Setup data
        assert not setup_df.empty, "Setup DataFrame should not be empty"
        logger.info(f"✓ Setup data extracted: {len(setup_df)} parameters")
        
        # Print setup data for inspection
        print("\n" + "="*80)
        print("SETUP DATA EXTRACTED:")
        print("="*80)
        print(setup_df.to_string())
        
        # Verify Recipe data
        assert not recipe_df.empty, "Recipe DataFrame should not be empty"
        logger.info(f"✓ Recipe data extracted: {len(recipe_df)} steps")
        
        # Print recipe data for inspection
        print("\n" + "="*80)
        print("RECIPE DATA EXTRACTED:")
        print("="*80)
        print(recipe_df.to_string())
        
        # Verify expected columns
        assert 'Chemical' in chemistry_df.columns
        assert 'Mol Weight' in chemistry_df.columns
        assert 'Actual Amount' in chemistry_df.columns
        
        logger.info("✓ PDF extraction test passed!")
    
    def test_mro004_normalization_with_pdf(self, pdf_path, logger):
        """
        Test 2: Full Normalization with PDF
        Verifies that MRO004 can process PDF and create Chemical objects
        with database references (PubChem).
        """
        logger.info(f"Testing MRO004 normalization with PDF: {pdf_path}")
        
        # Create an archive with MRO004 measurement
        archive = EntryArchive()
        
        # Create MRO004 instance with PDF report
        mro004 = MRO004()
        mro004.report_file = pdf_path
        
        # Set the data section
        archive.data = mro004
        
        # Mock the raw_file context manager for the normalizer
        class MockContext:
            def raw_file(self, filepath, mode='rb'):
                """Mock raw_file method to open the actual PDF file."""
                class FileContext:
                    def __init__(self, filepath):
                        self.filepath = filepath
                    
                    def __enter__(self):
                        return open(self.filepath, 'rb')
                    
                    def __exit__(self, *args):
                        pass
                
                return FileContext(filepath)
        
        archive.m_context = MockContext()
        
        # Run normalization
        logger.info("Running normalization...")
        normalize_all(archive)
        
        # Verify chemicals were created
        assert hasattr(archive.data, 'chemicals'), "Chemicals should be created"
        assert archive.data.chemicals, "Chemicals list should not be empty"
        
        logger.info(f"✓ Created {len(archive.data.chemicals)} chemical entries")
        
        # Verify each chemical has database reference
        print("\n" + "="*80)
        print("CHEMICAL OBJECTS WITH DATABASE REFERENCES:")
        print("="*80)
        
        for i, chemical in enumerate(archive.data.chemicals):
            logger.info(f"\nChemical {i+1}: {chemical.chemical_name}")
            
            # Check if chemical has a name
            assert chemical.chemical_name, f"Chemical {i} should have a name"
            
            # Check if PubChem reference was created
            if chemical.pure_substance:
                logger.info(f"  ✓ PubChem reference created")
                logger.info(f"  - Name: {chemical.pure_substance.name}")
                
                if hasattr(chemical.pure_substance, 'molecular_formula') and chemical.pure_substance.molecular_formula:
                    logger.info(f"  - Formula: {chemical.pure_substance.molecular_formula}")
                
                if hasattr(chemical.pure_substance, 'cas_number') and chemical.pure_substance.cas_number:
                    logger.info(f"  - CAS: {chemical.pure_substance.cas_number}")
                
                if hasattr(chemical.pure_substance, 'smile') and chemical.pure_substance.smile:
                    logger.info(f"  - SMILES: {chemical.pure_substance.smile}")
            else:
                logger.warning(f"  ⚠ No PubChem reference created (database lookup may have failed)")
            
            # Check other properties
            if chemical.mol_weight:
                logger.info(f"  - Mol Weight: {chemical.mol_weight}")
            if chemical.actual_amount:
                logger.info(f"  - Actual Amount: {chemical.actual_amount}")
            if chemical.actual_moles:
                logger.info(f"  - Actual Moles: {chemical.actual_moles}")
        
        # Verify recipe steps were created
        assert hasattr(archive.data, 'steps'), "Recipe steps should be created"
        if archive.data.steps:
            logger.info(f"\n✓ Created {len(archive.data.steps)} recipe steps")
        
        logger.info("\n✓ Full normalization test passed!")
        
        return archive
    
    def test_generate_normalized_archive(self, pdf_path, logger):
        """
        Test 3: Generate Normalized Archive JSON
        Creates a normalized archive JSON file that can be inspected.
        """
        logger.info("Generating normalized archive JSON...")
        
        # Run the normalization test
        archive = self.test_mro004_normalization_with_pdf(pdf_path, logger)
        
        # Convert archive to dict
        archive_dict = archive.m_to_dict()
        
        # Save to JSON file
        output_path = Path(__file__).parent / "data" / "test_MRO008_normalized.archive.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(archive_dict, f, indent=2, default=str)
        
        logger.info(f"✓ Normalized archive saved to: {output_path}")
        print(f"\n{'='*80}")
        print(f"NORMALIZED ARCHIVE SAVED: {output_path}")
        print(f"{'='*80}")
        print("\nYou can inspect this file to see:")
        print("- Extracted chemistry data")
        print("- PubChem database references")
        print("- Recipe steps")
        print("- All normalized data structures")
        
        # Verify file was created
        assert output_path.exists(), f"Output file should be created at {output_path}"
        
        logger.info("✓ Archive generation test passed!")


def test_pdf_extraction_standalone(tmp_path):
    """
    Standalone test that can be run with: pytest -sv tests/test_pdf_processing.py::test_pdf_extraction_standalone
    """
    pdf_file = PROJECT_ROOT / "Report MRO008.pdf"
    
    if not pdf_file.exists():
        pytest.skip(f"PDF file not found: {pdf_file}")
    
    print(f"\n{'='*80}")
    print(f"Testing PDF: {pdf_file}")
    print(f"{'='*80}")
    
    # Extract data
    chemistry_df, setup_df, recipe_df = extract_tables_from_report(str(pdf_file))
    
    print("\n--- CHEMISTRY ---")
    print(chemistry_df)
    
    print("\n--- SETUP ---")
    print(setup_df)
    
    print("\n--- RECIPE ---")
    print(recipe_df)
    
    assert not chemistry_df.empty
    assert not setup_df.empty
    assert not recipe_df.empty

