# PDF Processing Tests

This directory contains tests for PDF processing and normalization of MRO004 measurements.

## Overview

The test suite verifies:
1. **PDF Extraction**: Extracts Chemistry, Setup, and Recipe data from PDF reports
2. **Database References**: Automatically fetches chemical data from PubChem database
3. **Normalization**: Creates normalized archive with all metadata
4. **Archive Generation**: Outputs normalized archive JSON for inspection

## Running the Tests

### Quick Start - Run All PDF Tests

```bash
cd /home/lankovas/nomad-distro-dev/packages/nomad-cau-plugin
pytest -sv tests/test_pdf_processing.py
```

### Run Individual Tests

**Test 1: PDF Extraction Only**
```bash
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_pdf_extraction
```
This extracts Chemistry, Setup, and Recipe tables from the PDF and displays them.

**Test 2: Full Normalization with Database Lookup**
```bash
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_mro004_normalization_with_pdf
```
This runs the full normalization pipeline:
- Extracts data from PDF
- Creates Chemical objects
- Fetches data from PubChem database
- Displays all chemical information with database references

**Test 3: Generate Normalized Archive**
```bash
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_generate_normalized_archive
```
This creates a complete normalized archive JSON file at:
`tests/data/test_MRO008_normalized.archive.json`

**Test 4: Standalone PDF Extraction**
```bash
pytest -sv tests/test_pdf_processing.py::test_pdf_extraction_standalone
```
Simple standalone test that just extracts and displays PDF data.

### Using pytest with verbose output

For more detailed output:
```bash
pytest -vv --log-cli-level=INFO tests/test_pdf_processing.py
```

## Test Files

- **Test PDF**: `/home/lankovas/nomad-distro-dev/Report MRO008.pdf`
- **Test Script**: `tests/test_pdf_processing.py`
- **Output Archive**: `tests/data/test_MRO008_normalized.archive.json` (generated after running tests)

## What the Tests Do

### 1. PDF Extraction Test
- Opens the PDF file
- Extracts structured data using `pdfplumber`
- Verifies Chemistry, Setup, and Recipe tables are not empty
- Displays extracted data for inspection

### 2. Normalization Test
- Creates an `EntryArchive` with `MRO004` measurement
- Sets the PDF report file
- Runs the NOMAD normalization pipeline
- Verifies Chemical objects are created
- **Automatically looks up each chemical in PubChem database**
- Displays:
  - Chemical names
  - Molecular formulas
  - CAS numbers
  - SMILES notation
  - Molecular weights
  - Amounts and moles

### 3. Archive Generation Test
- Runs the full normalization
- Converts archive to dictionary
- Saves as JSON file
- Creates a file you can inspect to see the complete normalized data structure

## Understanding Database References

The normalizer automatically creates PubChem references for each chemical:

```python
# From the Chemical.normalize() method:
if self.chemical_name and not self.pure_substance:
    self.pure_substance = PubChemPureSubstanceSection(name=self.chemical_name)
```

This automatically fetches:
- Molecular formula
- SMILES notation
- InChI
- CAS number
- And more from the PubChem database

## Inspecting Results

After running the tests, you can:

1. **View console output** - Shows extracted data and database lookups
2. **Inspect JSON file** - Open `tests/data/test_MRO008_normalized.archive.json` to see the complete normalized archive

## Using with nomad parse Command

To use the `nomad parse` command directly (requires NOMAD CLI):

```bash
# Navigate to the project root
cd /home/lankovas/nomad-distro-dev

# Parse the PDF and generate normalized archive
nomad parse packages/nomad-cau-plugin/tests/data/test_MRO004.archive.yaml --show-archive
```

However, for testing PDF files specifically, the pytest approach is recommended as it:
- Provides better debugging output
- Allows testing individual components
- Generates inspection files
- Verifies database connections

## Troubleshooting

**Issue**: PubChem database lookups fail
- Check internet connection
- Some chemicals may not be in PubChem database
- Check chemical name spelling

**Issue**: PDF not found
- Verify the PDF exists at: `/home/lankovas/nomad-distro-dev/Report MRO008.pdf`
- Update the path in the test if needed

**Issue**: Import errors
- Make sure you're in the package directory
- Install dev dependencies: `pip install -e ".[dev]"`

## Adding More Test PDFs

To test with additional PDF files:

1. Copy your PDF to the project root or tests/data directory
2. Update the `pdf_path` fixture in `test_pdf_processing.py`:
   ```python
   @pytest.fixture
   def pdf_path(self):
       pdf_file = Path(__file__).parent / "data" / "your_file.pdf"
       return str(pdf_file)
   ```
3. Run the tests

## Next Steps

After verifying the tests work:
1. Review the generated `test_MRO008_normalized.archive.json` file
2. Verify all expected data is present
3. Check that database references are correctly populated
4. Use this as a template for testing other PDF files

