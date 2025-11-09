#!/usr/bin/env python3
"""
Standalone script to test PDF processing and normalization.
Run with: python tests/run_pdf_test.py
"""
import sys
import json
import logging
from pathlib import Path

# Add the src directory to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "nomad-cau-plugin" / "src"))

from nomad.metainfo import EntryArchive
from nomad.client import normalize_all
from nomad_cau_plugin.parsers.pdf_extract import extract_tables_from_report
from nomad_cau_plugin.measurements.MRO004 import MRO004


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")


def test_pdf_extraction(pdf_path, logger):
    """Extract and display data from PDF."""
    print_header("STEP 1: PDF EXTRACTION")
    
    logger.info(f"Extracting data from: {pdf_path}")
    
    # Extract tables
    chemistry_df, setup_df, recipe_df = extract_tables_from_report(pdf_path)
    
    # Display Chemistry
    print("\n--- CHEMISTRY DATA ---")
    print(chemistry_df.to_string())
    print(f"\n✓ Extracted {len(chemistry_df)} chemicals")
    
    # Display Setup
    print("\n--- SETUP DATA ---")
    print(setup_df.to_string())
    print(f"\n✓ Extracted {len(setup_df)} setup parameters")
    
    # Display Recipe
    print("\n--- RECIPE DATA ---")
    print(recipe_df.to_string())
    print(f"\n✓ Extracted {len(recipe_df)} recipe steps")
    
    return chemistry_df, setup_df, recipe_df


def test_normalization(pdf_path, logger):
    """Run full normalization with database lookup."""
    print_header("STEP 2: NORMALIZATION WITH DATABASE LOOKUP")
    
    logger.info("Creating MRO004 archive...")
    
    # Create archive
    archive = EntryArchive()
    mro004 = MRO004()
    mro004.report_file = pdf_path
    archive.data = mro004
    
    # Mock context for file access
    class MockContext:
        def raw_file(self, filepath, mode='rb'):
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
    logger.info("Running normalization (this may take a moment for database lookups)...")
    normalize_all(archive)
    
    # Display results
    if hasattr(archive.data, 'chemicals') and archive.data.chemicals:
        print(f"\n✓ Created {len(archive.data.chemicals)} chemical entries\n")
        
        for i, chemical in enumerate(archive.data.chemicals, 1):
            print(f"\nChemical {i}: {chemical.chemical_name}")
            print("-" * 60)
            
            if chemical.pure_substance:
                print("  ✓ PubChem database reference created:")
                print(f"    - Name: {chemical.pure_substance.name}")
                
                if hasattr(chemical.pure_substance, 'molecular_formula') and chemical.pure_substance.molecular_formula:
                    print(f"    - Formula: {chemical.pure_substance.molecular_formula}")
                
                if hasattr(chemical.pure_substance, 'cas_number') and chemical.pure_substance.cas_number:
                    print(f"    - CAS Number: {chemical.pure_substance.cas_number}")
                
                if hasattr(chemical.pure_substance, 'smile') and chemical.pure_substance.smile:
                    print(f"    - SMILES: {chemical.pure_substance.smile}")
                
                if hasattr(chemical.pure_substance, 'inchi') and chemical.pure_substance.inchi:
                    print(f"    - InChI: {chemical.pure_substance.inchi[:50]}...")
            else:
                print("  ⚠ No PubChem reference (database lookup may have failed)")
            
            if chemical.mol_weight:
                print(f"  - Molecular Weight: {chemical.mol_weight}")
            if chemical.actual_amount:
                print(f"  - Actual Amount: {chemical.actual_amount}")
            if chemical.actual_moles:
                print(f"  - Actual Moles: {chemical.actual_moles}")
    
    if hasattr(archive.data, 'steps') and archive.data.steps:
        print(f"\n✓ Created {len(archive.data.steps)} recipe steps")
    
    return archive


def save_normalized_archive(archive, output_path, logger):
    """Save normalized archive to JSON file."""
    print_header("STEP 3: SAVE NORMALIZED ARCHIVE")
    
    logger.info(f"Saving normalized archive to: {output_path}")
    
    # Convert to dict
    archive_dict = archive.m_to_dict()
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(archive_dict, f, indent=2, default=str)
    
    print(f"\n✓ Normalized archive saved successfully!")
    print(f"\nFile location: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")
    
    print("\nThis file contains:")
    print("  - All extracted chemistry data")
    print("  - PubChem database references")
    print("  - Recipe steps and setup parameters")
    print("  - Complete normalized data structures")


def main():
    """Main function to run all tests."""
    logger = setup_logging()
    
    print_header("PDF PROCESSING AND NORMALIZATION TEST")
    
    # Get PDF path
    pdf_path = PROJECT_ROOT / "Report MRO008.pdf"
    
    if not pdf_path.exists():
        print(f"❌ ERROR: PDF file not found at: {pdf_path}")
        print("\nPlease ensure the PDF file exists or update the path in this script.")
        sys.exit(1)
    
    print(f"Testing PDF: {pdf_path}\n")
    
    try:
        # Step 1: Extract PDF data
        chemistry_df, setup_df, recipe_df = test_pdf_extraction(str(pdf_path), logger)
        
        # Step 2: Run normalization with database lookup
        archive = test_normalization(str(pdf_path), logger)
        
        # Step 3: Save normalized archive
        output_path = Path(__file__).parent / "data" / "test_MRO008_normalized.archive.json"
        save_normalized_archive(archive, output_path, logger)
        
        # Summary
        print_header("TEST SUMMARY")
        print("✓ PDF extraction: SUCCESS")
        print("✓ Normalization: SUCCESS")
        print("✓ Archive generation: SUCCESS")
        print("\nAll tests passed! 🎉")
        
        print("\nNext steps:")
        print(f"  1. Review the generated file: {output_path}")
        print("  2. Verify database references are correct")
        print("  3. Use this as a template for other PDF files")
        
    except Exception as e:
        print_header("ERROR")
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

