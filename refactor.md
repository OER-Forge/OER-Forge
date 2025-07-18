# OERForge Refactor Plan

## Management Plan

### 1. Configuration & Parsing
- Parse _content.yml for global and per-file export: blocks.
- Support custom output paths, labels, and force flags.
- Validate and merge global/per-file settings.

### 2. Conversion Orchestration

### 3. HTML Generation
  - Add WCAG compliance badges/labels to pages.
  - Optionally generate individual accessibility reports per page.
  - Ensure accessibility info is included in admin/build reports.
### 4. CLI & Reporting
- Add CLI options for dry-run, force, and admin reporting.
  - Generate build/admin/index.html summarizing the build (successes, failures, missing, accessibility, etc.).
  - Integrate accessibility summary from verify.py into admin report.
---

  - Ensure accessibility results are written to `accessibility_results` and related tables.
  - Provide functions to inject badges/labels into generated HTML pages.
  - Generate individual accessibility reports per page if desired.
  - Generate an administrative accessibility summary for build/admin/index.html.
- **Function:** Orchestrates the build process.
- **Refactor:**
  - Render WCAG/accessibility badges/labels as provided by verify.py.
  - Support CLI flags (dry-run, force, report).
- **Testable Chunks:**
  - Include accessibility summary from verify.py (WCAG compliance, issues, etc.).
  - Include timestamps, reasons, and links to outputs.
  - Link to or embed individual page accessibility reports if generated.
  - Accessible and easy to scan.
- **Function:** Handles file conversions.
- **Refactor:**
  - Accept list of requested conversions (type, output path, force, label).
  - Attempt conversions, including forced/unsupported.
  - Log all attempts in conversion_results (add columns: status, reason, forced, timestamp, custom_label, output_path).
  - Return results to make.py.
- **Testable Chunks:**
  - Conversion logic per type.
  - Logging and DB updates.
 5. Runs accessibility checks with verify.py, logs results, and injects badges/labels.
 6. Generates HTML pages with accessible download buttons and accessibility badges/labels.
 7. Writes build/admin/index.html with build and accessibility summary, and links to per-page accessibility reports.
  - Forced/unsupported conversion handling.

### oerforge/db_utils.py
- **Function:** DB schema and queries.
- **Refactor:**
  - Add/alter conversion_results table (new columns: status, reason, forced, timestamp, custom_label, output_path).
  - Add helper functions for logging conversion attempts and querying by build run.
- **Testable Chunks:**
  - Schema migration.
  - Logging/querying functions.

### oerforge/scan.py
- **Function:** Scans content/ for files/assets.
- **Refactor:**
  - No major changes unless asset export is needed.
  - Ensure DB is up-to-date before build.
- **Testable Chunks:**
  - File/asset discovery.

### oerforge/copyfile.py
- **Function:** Copies static assets.
- **Refactor:**
  - No major changes unless asset export is needed.
  - Ensure only current assets are in build/.
- **Testable Chunks:**
  - Asset copy logic.

### oerforge/section.html (Jinja2 template)
- **Function:** Renders content and download buttons.
- **Refactor:**
  - Accept button metadata (label, path, ARIA label).
  - Use accessible markup and existing CSS/JS.
  - Only show buttons for files that exist.
- **Testable Chunks:**
  - Button rendering logic.
  - Accessibility compliance.

### CLI (new or in make.py)
- **Function:** User interface for build.
- **Refactor:**
  - Add CLI options: --dry-run, --force, --report.
  - Print summary to console and write build/admin/index.html.
- **Testable Chunks:**
  - CLI parsing.
  - Dry-run logic.
  - Report generation.

### build/admin/index.html (new)
- **Function:** Build/admin report.
- **Refactor:**
  - Summarize all conversion attempts (success, fail, missing, forced, etc.).
  - Include timestamps, reasons, and links to outputs.
  - Accessible and easy to scan.
- **Testable Chunks:**
  - Report generation from DB.

---

## Example Workflow

1. User runs:  
   `python make.py --dry-run --report`
2. System parses _content.yml, determines conversions.
3. For each file, attempts conversions (or simulates in dry-run).
4. Logs all results in DB with timestamps, reasons, forced flag, etc.
5. Cleans up build/ to match current plan.
6. Generates HTML pages with accessible download buttons.
7. Writes build/admin/index.html with build summary.

---

## Documentation Template (for new/changed modules)

```
### <module path>
- **Function:** <What does this module do?>
- **Database Usage:** <How does it use the DB?>
- **Extensibility:** <How could it be extended in the future?>
```

---

Let me know if you want to adjust any part of this plan, or if you’re ready for code generation for a specific module!
