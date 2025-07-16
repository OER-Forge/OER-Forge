# Pa11y Accessibility Integration

This project supports optional accessibility compliance checking using [Pa11y](https://github.com/pa11y/pa11y).

## How it works
- If you want to check accessibility, install Pa11y locally (requires Node.js):
  ```sh
  npm install -g pa11y
  ```
- The `verify.py` script will detect if Pa11y is installed and, if so, run accessibility checks on built HTML files.
- If Pa11y is not installed, accessibility checks are skipped and a message is shown.

## Next steps
- This document will be updated as the integration is developed.
- Planned: CLI options, reporting, and integration with CI.
