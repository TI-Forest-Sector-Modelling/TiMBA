# Changelog

## [v1.4.2] - 2026-07-17

### Fix
- .zenodo.json bug fixed
   

## [v1.4.1] - 2026-07-17

### Added
- Migrated dependency management to [uv](https://docs.astral.sh/uv/).
- Added `.python-version` pinning Python 3.11 and a `uv.lock` file for reproducible installs.
- Added macOS to the CI test matrix.
- Documented the uv workflow in `README.md`, `AGENTS.md`, and `CONTRIBUTING.md`.

### Changed
- Updated GitHub Actions workflows (`actions.yml`, `sonarscan.yml`) to use uv for dependency installation and test execution.
- Cleaned up `pyproject.toml` metadata (`requires-python` and classifiers).
- `requirements.txt` is kept as a fallback for non-uv users.


## [v1.4.0] - 2026-07-16

### Added
- Integration of the TiMBA Charts package into TiMBA.
- Added a CLI command to launch the Validation Dashboard.
- Added YAML logging of simulation input parameters for improved traceability and reproducibility.

### Changed
- Revised and streamlined command-line interface (CLI) for executing core functionality.
- Revised path management for the TiMBA Charts integration.
- Updated the branch used from the Additional Info repository.

### Fixed
- Fixed issues in the Validation Dashboard integration.
- Resolved permission errors by adjusting the main execution loop.

### Documentation
- Updated and extended the project README.
- Revised section numbering and the table of contents.
  

## [v1.3.0] - 2025-12-03

### Added
- Added functionality for automatic downloading of required input data using `Load_Data.py` in `data_management`.
- Added load_timba command, including help texts and error messages, to initiate the automated data download.
- Introduced an automatically generated YAML file to store scenario-specific information.
- Added GitHub issue templates for bugs, feature requests, and questions.
- Added import tests for external packages and TiMBA modules.

### Changed
- Centralized and refactored path handling across the model and CLI.
- Adapted the entire project to the new path structure and removed outdated parameters.
- Updated README with revised instructions for data loading, PyPI usage, and CLI descriptions.
- Updated recommended TiMBA citation and added JOSS DOI and Zenodo badge.
- Updated license information in `pyproject.toml`.
- Improved GitHub Actions workflows (`publish.yml`) to support automated PyPI releases.
- Updated `pyproject.toml` settings related to package distribution.
- General formatting and documentation improvements (text adjustments, restructuring).

### Fixed
- Fixed multiple CLI bugs related to the new automated data loading mechanism.
- Fixed path-related issues in `main.py` and CLI commands.
- Resolved issues caused by the new path structure and folder layout.
- Improved handling of permission errors in `Load_Data.py`.
- Adjusted coverage configuration and resolved warnings during test runs.

### Security
- Pinned PyPI publishing GitHub Actions to fixed commit SHAs for improved security.

### Removed
- Removed the previous `data` folder from the repository (data is now downloaded automatically).


## [v1.2.0] - 2025-11-18

### Added
- **Carbon Module implementation**
  - Import and integration of the [Carbon Module](https://github.com/TI-Forest-Sector-Modelling/C-Module) into TiMBA
  - Setup structure for further model extensions

## [v1.1.0] - 2025-10-20

### Added
- Add paper for peer-reviewed JOSS publication
- Add workflow dispatch to enable manual activation of the GitHub Actions

### Changed
- Changed compatibility to Python <= 3.11
- Update default scenario input and default results for test suite
- Revisions of README to comply with JOSS reviews (add section for know issues and installation process)

## [v1.0.3] - 2025-04-09

### Added
- **Forest Model:**  
  - Implementation of an upper bound for forest stand density based on forest resources assessment data.
  - Added option to handle scenario_input with and without forest stand density restriction.
- **Documentation**  
  - Added the TiMBA documentation as a PDF file (DOI: 10.3220/253-2025-16).

### Changed
- **scenario input:**
  - Default `scenario_input.xlsx` has been updated with newest data (FAOSTAT, FRA, WTO, and SSP2).   
- **GitHub Actions:**  
  - Updated `setup-python` in `sonarscan.yml`.  
  - Upgraded `upload-artifact` and `setup-python` in `actions.yml`.
- **Coverage Report:**  
  - Included OS and Python version name.  
- **Package upgrades and dependencies**
  - Upgrade cvxpy solver environment to 1.6.4.
  - Fix osqp solver to 0.6.7.post3 to ensure package compatibility.

## [v1.0.2] - 2025-01-29

### Added
- **Python 3.12 compatibility**:
  - TiMBA is upgraded to run with Python 3.12.6.
  - Successfully tested for Python 3.9, 3.10, 3.11. 
- **GitHub Actions**: 
  - Set up GitHub Actions for TiMBA to integrate automated functionality and quality checks.
  - Added compatibility checks with multiple Python versions (Python 3.9, 3.10, 3.11, 3.12) and operating systems
(Windows and Ubuntu).
- **SonarCloud Integration**: Implemented and optimized code coverage and scans to ensure higher code quality.  
  - Integrated SonarCloud into the GitHub Actions pipeline.  
  - Added a SonarCloud quality status badge to `README.md`.   
- **Badges**: Added project badges like release status, coverage, and Zenodo-DOI.

### Changed
- **Package Upgrades**: All packages are upgraded to a version compatible with Python 3.12.
- **Readme & Compatibility**: Updated compatible Python versions and supported operating systems.
- **Scenario input file**: Changed scenario file for more consistent results.
- **Zipped pkl-files**: pkl-files for TiMBA output are zipped now to save storage space.
- **pkl-files with time stamps**: pkl-files for TiMBA output are now saved with a time stamp to allow unambiguous
identification.

### Fixed
- **GitHub Actions Bugs**:  
  - Various adaptations to fix bugs in the GitHub Actions 
- **Fixes to ensure compatibility with Python 3.12**
  - Resolved an issue with `np.isclose` for compatibility between Python 3.12 and Pandas.  
  - Replaced `iteritems` with `items` for compatibility with Python 3.12.
- **Gitignore Improvements**: Extended `.gitignore` to include additional folders like `timba\data\input`.

### Removed
- **Unnecessary Folders**: Removed virtual environment (`venv`) from the repository.  
- **Unsupported Python Versions**: Removed outdated versions from the test matrix.
