# Developer Handover Guide: nomad-cau-plugin

## 1. Purpose and Scope

This document is the technical handover for the CAU NOMAD plugin project. It explains:

- what the plugin does,
- how the code is structured,
- how it is developed and tested,
- how it is integrated with `nomad-distro-dev`,
- how it is deployed through `nomad-oasis-image`,
- and what the most recent in-progress changes are.

The target reader is a new developer taking over maintenance and feature work.

## 2. Project in the Larger NOMAD Ecosystem

## 2.1 Repository Roles

### `CAU-Kiel/nomad-cau-plugin`

Domain-specific plugin for CAU experimental data.

Main responsibilities:

- schema definitions for CAU experiments,
- parser utilities for XRD, IR, DLS, UV-Vis, luminescence, and PDF table extraction,
- normalizers that convert uploaded files into archive quantities and Plotly figures.

### `lankovas/nomad-distro-dev`

Local development distribution that assembles NOMAD core plus local plugins in one workspace.

Main responsibilities:

- editable multi-package development with `uv` workspaces,
- local API/worker startup,
- shared infrastructure services via Docker Compose (Mongo, Elastic, RabbitMQ, Temporal),
- local test and lint orchestration.

### `CAU-Kiel/nomad-oasis-image`

Deployment distribution for production-like Oasis usage.

Main responsibilities:

- building and publishing Docker images containing configured plugin sets,
- CI image rebuild on `main` updates,
- deployment instructions for new and existing Oasis instances,
- optional Jupyter/NORTH image integration.

### Other repositories present in the workspace

- `packages/nomad-FAIR`: NOMAD core codebase used in local development.
- `packages/nomad-material-processing`: shared base sections plugin that can complement domain plugins.

## 2.2 Practical relationship between repos

Development loop:

1. Implement in `nomad-cau-plugin`.
2. Run and test through `nomad-distro-dev` (editable install).
3. Deploy by adding/updating plugin dependencies in `nomad-oasis-image` and using image pipeline.

This separation is intentional:

- `nomad-cau-plugin` is code and logic.
- `nomad-distro-dev` is local integration and developer productivity.
- `nomad-oasis-image` is delivery and operations.

## 3. Current Code Architecture

## 3.1 Entry points and registration

Plugin entry points are declared in `pyproject.toml` under `[project.entry-points.'nomad.plugin']`.

Important active schema entry points:

- `MRO004_schema`
- `MRO005_schema`
- `UVVis_schema`

Also present:

- template parser/normalizer/schema entry points (`NewParser`, `NewNormalizer`, `NewSchemaPackage`) from cookiecutter scaffold.

Important note:

- The real business logic is currently centered in schema classes and normalizer utility modules, not in the top-level `NewParser` class.

## 3.2 Main modules and responsibilities

### Measurements (`src/nomad_cau_plugin/measurements`)

- `CaP_experiments.py`
  - Main CaP experiment schema (reactor, XRD, luminescence, chemistry, recipe steps).
  - Executes normalization pipeline and populates figures.
- `MRO005.py`
  - MRO005-specific schema and normalization hook.
- `UVVis.py`
  - UV-Vis schema and trace selection behavior.

### Normalizers (`src/nomad_cau_plugin/normalizers`)

- `CaP_experiments_normalizer.py`
  - Core processing for reactor CSV, report PDF, XRD, IR, DLS, luminescence.
  - Plot generation using Plotly.
- `Michaela_experiments_normalizer.py`
  - Alias/subclass wrapper around `CaPNormalizer` for schema package naming clarity.
- `mro005_normalizer.py`
  - MRO005 Excel + recipe processing.
- `uvvis_normalizer.py`
  - UV-Vis trace extraction and plotting.
- `column_utils.py`
  - Column name matching utilities for multilingual/variant headers.

### Parsers (`src/nomad_cau_plugin/parsers`)

- `xrd_from_cif.py`
  - Reference-file dispatch by extension (`.xy`, `.xyd`, `.cif`, `.vasp`).
  - Pattern computation using `pymatgen` for structure files.
- `ir_from_dpt.py`
  - Two-column `.dpt` parsing with robust decoding.
- `dls_from_xls.py`
  - DLS text-style `.xls` parsing for intensity/volume/number distributions.
- `uvvis_spreadsheet.py`
  - Pairwise-column trace extraction from CSV/Excel.
- `luminescence_csv.py`
  - Matrix parsing with timestamp row and wavelength/intensity data.
- `pdf_extract.py`
  - Chemistry/setup/recipe extraction from report PDFs.

### Schema package (`src/nomad_cau_plugin/schema_packages/schema_package.py`)

Contains higher-level process model (`Michaela`) with synthesis/refinement/characterization sections and normalization orchestration.

## 3.3 Data flow

For file-driven measurements, the dominant flow is:

1. User uploads raw files in ELN section fields.
2. Schema `normalize()` calls normalizer helper methods.
3. Parser helpers decode and validate files.
4. Quantities are filled in archive sections.
5. Plotly figures are generated and attached.

For XRD, the comparison logic includes:

- measurement curve normalization,
- q-axis conversion using wavelength,
- optional reference overlays rendered as peak sticks.

## 4. Development History and Milestones

The repository history shows a clear evolution path:

### Foundation phase

- Initial commit and cookiecutter-based plugin scaffold.
- Early CAU plugin implementation and first uploads.

### Parsing and extraction phase

- PDF extraction for recipe and chemistry sections.
- Separation and maturation of normalizer modules.

### XRD and plotting phase

- Initial XRD plotting support.
- Expanded XRD generation features.
- q-axis support and multiple reference formats.
- duplicate-figure prevention on repeated saves.

### Spectroscopy expansion phase

- Luminescence CSV parser.
- IR `.dpt` support.
- DLS support for intensity/volume/number distributions.
- UV-Vis measurement support.

### Hardening phase

- Extensive Ruff lint cleanup across normalizers, parsers, tests.
- Schema unit consistency fixes (percent-like values to `dimensionless`).
- XRD alpha handling robustness for float and pint quantity inputs.

## 5. Current In-Progress Change Set (Included in this handover)

At handover time, local modifications were present and are now treated as part of the working baseline.

### 5.1 Changes in `CaP_experiments.py`

- XRD reference modeling shifts toward flat aligned arrays:
  - `reference_files: list[str]`
  - `reference_alphas: list[float]`
- Removal of dedicated `XRDReference` subsection object from this file path.
- Normalization logic updated to align alphas with files by index and pad missing alphas with `None`.
- Support for `use_measurement_alpha_for_all_references` maintained with alpha propagation.
- Minor ordering/formatting cleanup and class ordering adjustments.

Why it matters:

- Simpler ELN data model for multi-reference upload.
- Easier one-to-one mapping of references and wavelengths in normalizer calls.

### 5.2 Changes in `schema_package.py`

- `Michaela` normalization path updated to prefer flat `reference_files/reference_alphas` arrays.
- Backward-compatible fallback remains for `xrd_references` subsection if present.
- Propagation logic now safely accesses legacy fields via `getattr` where needed.

Why it matters:

- Migration path is smoother for existing archives.
- New and legacy reference representations can coexist during transition.

## 6. Prerequisites for a New Developer

Minimum environment:

- Linux recommended (or WSL/devcontainer on Windows).
- Docker with Compose.
- `uv` >= 0.5.14.
- Python 3.10+ (3.11 is practical default here).
- Node.js 20 and Yarn 1.22 (for GUI tasks through distro).

Python dependencies of `nomad-cau-plugin` include:

- `nomad-lab`
- `pdfplumber`
- `pymatgen`
- `openpyxl` (through distro dependency set)

## 7. Setup and Daily Development Workflow

Recommended path uses `nomad-distro-dev` as the top-level workspace.

## 7.1 One-time setup

1. Clone `nomad-distro-dev` fork.
2. Initialize submodules:

```bash
git submodule update --init --recursive
```

3. Ensure `packages/nomad-cau-plugin` is present as submodule.
4. Ensure distro `pyproject.toml` has both:
   - dependency `nomad-cau-plugin`
   - source `nomad-cau-plugin = { workspace = true }`
5. Start infrastructure:

```bash
docker compose up -d
```

6. Install/sync env and generate local config:

```bash
uv run poe setup
```

## 7.2 Run services

Backend app/worker:

```bash
uv run poe start
```

GUI:

```bash
uv run poe gui start
```

## 7.3 Work inside plugin package

Run tests:

```bash
uv run --directory packages/nomad-cau-plugin pytest -sv tests
```

Run lint:

```bash
uv run --directory packages/nomad-cau-plugin ruff check .
uv run --directory packages/nomad-cau-plugin ruff format . --check
```

## 8. Testing Strategy and What Is Covered

Current tests cover:

- parser behavior for XRD dispatch/range filtering,
- UV-Vis trace extraction,
- luminescence CSV/Excel parsing and sheet selection,
- basic parser/normalizer smoke tests.

Recommended additions for takeover:

- regression tests for flat `reference_files/reference_alphas` path in both CaP and Michaela schema normalization,
- migration tests that validate old `xrd_references` archives still normalize correctly,
- integration test that runs through full upload -> normalize -> figure generation for XRD + references.

## 9. Deployment Path with `nomad-oasis-image`

When code is ready for Oasis deployment:

1. Add/update plugin dependency in `nomad-oasis-image/pyproject.toml` under plugin optional dependencies.
2. Commit and push to `main` in `nomad-oasis-image` repository.
3. CI builds new app and jupyter images.
4. Pull and restart on target Oasis:

```bash
docker compose down
docker compose pull
docker compose up -d
```

Operational caveats:

- If image package is private, GHCR authentication/PAT is required.
- For HTTPS deployments, proxy and TLS certificate setup must be configured in compose/proxy files.

## 10. Role of `nomad-material-processing`

`nomad-material-processing` is not a replacement for this plugin. It provides reusable base sections and domain-agnostic processing structures that can be composed with custom plugin schemas.

Use it when:

- you want to align CAU schemas with FAIRmat-wide processing abstractions,
- you need shared section semantics across multiple plugins.

Keep `nomad-cau-plugin` for:

- lab-specific file formats,
- CAU-specific ELN field design,
- custom normalization and plotting logic.

## 11. Known Risks and Operational Notes

- Mixed legacy/new XRD reference representation can cause subtle migration bugs if not tested.
- Some parser modules rely on input-format conventions (header lines, delimiters, row offsets). Unexpected vendor exports may require parser adaptation.
- Plot generation logic removes/replaces figures by label; if labels change, duplicate-figure behavior can regress.
- `NewParser`/`NewNormalizer` template stubs still exist and may confuse new contributors; document clearly that core behavior is schema-normalizer driven.

## 12. Recommended First Actions for a New Maintainer

1. Run full plugin test suite locally in distro environment.
2. Add regression tests for the new flat XRD reference arrays.
3. Create one golden example archive per major measurement type (XRD, UV-Vis, DLS, IR, luminescence).
4. Review and clean remaining template artifacts only after confirming no deployment depends on them.
5. Establish release tagging and changelog practice (repository currently has no tags).

## 13. Quick Command Reference

From distro root:

```bash
docker compose up -d
uv run poe setup
uv run poe start
uv run poe gui start
uv run --directory packages/nomad-cau-plugin pytest -sv tests
uv run --directory packages/nomad-cau-plugin ruff check .
```

From plugin root:

```bash
python -m pytest -sv tests
ruff check .
ruff format . --check
mkdocs serve
```

## 14. Ownership Snapshot

History indicates development is heavily concentrated in a single main contributor. For continuity, prioritize:

- test depth,
- documented conventions,
- and explicit release process.

This handover is intended to be the baseline for that continuity.