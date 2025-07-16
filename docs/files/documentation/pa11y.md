# pa11y.py — OERForge Accessibility Batch Runner

## Overview

`pa11y.py` is a command-line utility for running automated accessibility checks on all HTML files in the OERForge build directory using Pa11y. It loads configuration from YAML, validates required files and directories, and orchestrates the batch checking and reporting workflow. This script is designed for new users and programmers to provide a simple, robust entry point for accessibility validation.

- **Loads Pa11y and site configuration from YAML**
- **Validates existence of build directory, config file, and database**
- **Runs accessibility checks on all HTML files using Pa11y**
- **Uses custom config and WCAG level from YAML**
- **Handles errors and missing files gracefully**
- **Integrates with OERForge reporting and badge generation**

---

## Functions

### main()

Main entry point for the batch accessibility runner.

**Workflow Steps**
1. Sets paths for build directory, config file, and database.
2. Checks that all required files and directories exist.
3. Loads Pa11y configuration and WCAG level from YAML.
4. Validates the Pa11y config file exists.
5. Calls `process_all_html_files` to run checks and generate reports.

**Parameters**
- None

**Returns**
- None

---

## Usage

Run from the command line:

```bash
python pa11y.py
```

Or import and call `main()` from another script:

```python
import pa11y
pa11y.main()
```

---

## Error Handling

- Prints clear error messages and exits if required files or directories are missing.
- Handles missing config values with sensible defaults.
- Validates Pa11y config file before running checks.

## Logging

- All accessibility check results and errors are logged by the underlying OERForge modules (see `log/pa11y.log`).

## Example YAML Configuration

```yaml
pa11y:
  wcag_level: WCAG2AAA
  config: pa11y-config/pa11y.wcag.aaa.json
```

---

## License

See LICENSE in the project root.
