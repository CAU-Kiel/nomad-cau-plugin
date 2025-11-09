# Quick Start Guide - PDF Testing

## 🚀 Fastest Way to Test PDF Processing

### Option 1: Run Standalone Script (Recommended for Quick Testing)

```bash
cd /home/lankovas/nomad-distro-dev
uv run --directory packages/nomad-cau-plugin python tests/run_pdf_test.py
```

This will:
1. ✅ Extract Chemistry, Setup, and Recipe data from PDF
2. ✅ Run normalization with PubChem database lookup
3. ✅ Generate `tests/data/test_MRO008_normalized.archive.json`
4. ✅ Display all results in terminal

**Output includes:**
- Extracted tables from PDF
- Chemical information with database references
- PubChem data (formulas, CAS numbers, SMILES)
- Normalized archive JSON file

---

### Option 2: Run with pytest (Recommended for Development)

**Run all tests:**
```bash
cd /home/lankovas/nomad-distro-dev/packages/nomad-cau-plugin
pytest -sv tests/test_pdf_processing.py
```

**Run specific test:**
```bash
# Just PDF extraction
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_pdf_extraction

# Full normalization with database lookup
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_mro004_normalization_with_pdf

# Generate normalized archive
pytest -sv tests/test_pdf_processing.py::TestPDFProcessing::test_generate_normalized_archive
```

---

## 📁 What Gets Created

After running the tests, you'll find:

```
tests/data/test_MRO008_normalized.archive.json
```

This file contains:
- All extracted PDF data (chemistry, setup, recipe)
- PubChem database references
- Molecular formulas, CAS numbers, SMILES notation
- Complete NOMAD archive structure

---

## 🔍 Understanding the Output

### Terminal Output Shows:

1. **Chemistry Data Table**
   ```
   Chemical          | Mol Weight | Actual Amount | ...
   Calcium Nitrate   | 164.09     | 50.0 g       | ...
   ```

2. **PubChem Database Lookup**
   ```
   Chemical 1: Calcium Nitrate
     ✓ PubChem database reference created:
       - Name: Calcium Nitrate
       - Formula: Ca(NO3)2
       - CAS Number: 10124-37-5
       - SMILES: [Ca+2].[N+](=O)([O-])[O-].[N+](=O)([O-])[O-]
   ```

3. **Recipe Steps**
   ```
   ✓ Created 15 recipe steps
   ```

### JSON File Structure:

```json
{
  "data": {
    "m_def": "nomad_cau_plugin.measurements.MRO004.MRO004",
    "chemicals": [
      {
        "chemical_name": "Calcium Nitrate",
        "pure_substance": {
          "name": "Calcium Nitrate",
          "molecular_formula": "Ca(NO3)2",
          "cas_number": "10124-37-5",
          "smile": "[Ca+2].[N+](=O)([O-])[O-]..."
        },
        "mol_weight": "164.09 g/mol",
        "actual_amount": "50.0 g"
      }
    ],
    "steps": [...]
  }
}
```

---

## 🧪 Using with Your Own PDF Files

### Method 1: Update the script

Edit `tests/run_pdf_test.py` and change line:
```python
pdf_path = PROJECT_ROOT / "Your_Report.pdf"
```

### Method 2: Copy PDF to project root

Simply copy your PDF file to `/home/lankovas/nomad-distro-dev/` with the name `Report MRO008.pdf` (or update the path in the test files).

---

## 🔧 Troubleshooting

**Problem:** ModuleNotFoundError
```bash
# Make sure you're in the right directory
cd /home/lankovas/nomad-distro-dev/packages/nomad-cau-plugin

# Install the package in development mode
pip install -e .
```

**Problem:** PDF not found
```bash
# Check if PDF exists
ls -la /home/lankovas/nomad-distro-dev/Report\ MRO008.pdf

# If not, update the path in the test files
```

**Problem:** PubChem database lookup fails
- Check internet connection
- Some chemical names might not be in PubChem
- Check spelling of chemical names in PDF

---

## 📊 Comparing with GUI Upload

### GUI Process:
1. Open NOMAD GUI
2. Upload PDF file
3. Wait for processing
4. View results in browser
5. Export archive

### Test Process:
1. Run: `python tests/run_pdf_test.py`
2. View results in terminal
3. Inspect JSON file: `tests/data/test_MRO008_normalized.archive.json`

**Benefits of test approach:**
- ✅ Faster iteration
- ✅ Automated verification
- ✅ Can run in CI/CD pipeline
- ✅ Easy to debug
- ✅ Can test multiple files in batch

---

## 📚 More Information

See full documentation in:
- `tests/README_PDF_TESTS.md` - Detailed test documentation
- `tests/test_pdf_processing.py` - Test implementation
- `tests/run_pdf_test.py` - Standalone script

---

## ⚡ TL;DR

```bash
cd /home/lankovas/nomad-distro-dev/packages/nomad-cau-plugin
python tests/run_pdf_test.py
```

That's it! 🎉

