# OERForge Refactor Plan (Verbose, with Accessibility Integration)

## Step-by-Step Refactor Plan

### 1. Database Schema & Utilities (`db_utils.py`)
- Add/alter tables for conversion and accessibility results.
- Add fields: status, reason, forced, timestamp, custom_label, output_path, accessibility status, etc.
- Update all logging/querying functions.
- **Constraints:** Must be backward compatible, atomic writes, data migration for existing records.
- **Issues:** Data migration, atomicity, downstream dependency.

### 2. Configuration Parsing (`make.py`)
- Parse _content.yml for global/per-file export blocks, custom output, label, force.
- Merge global and per-file settings.
- Validate config against supported types.
- **Constraints:** Handle missing/invalid config, merge logic.
- **Issues:** Complex YAML, legacy configs.

### 3. Conversion Logic (`convert.py`)
- Accept/process requested conversions, including forced/unsupported.
- Log all attempts in DB.
- **Constraints:** No overwrites outside export plan, log failures.
- **Issues:** Unsupported conversions, forced conversion errors.

### 4. Accessibility Checks (`verify.py`)
- Run accessibility checks on generated HTML.
- Log results in DB.
- Inject badges/labels into HTML.
- Optionally generate per-page accessibility reports.
- **Constraints:** Run after HTML generation, do not block build on failure.
- **Issues:** Tool failures, sync with page updates.

### 5. Build Directory Cleanup (`make.py`)
- Remove obsolete outputs from build/ to match export plan.
- **Constraints:** Do not delete needed files/reports, idempotent.
- **Issues:** Race conditions, custom paths.

### 6. HTML Generation & Button Rendering (`section.html`, `make.py`)
- Generate download buttons for existing outputs, using custom labels/ARIA.
- Render accessibility badges/labels from `verify.py`.
- **Constraints:** Only show for files that exist, accessible markup.
- **Issues:** ARIA/WCAG compliance, missing accessibility data.

### 7. CLI & Dry-Run/Reporting (`make.py`, `build/admin/index.html`)
- Add CLI options for dry-run, force, reporting.
- Generate build/admin/index.html with build and accessibility summary, links to per-page reports.
- **Constraints:** No destructive actions in dry-run, aggregate conversion/accessibility logs.
- **Issues:** CLI usability, large file/report sets.

---

## Order of Operations
1. Database Schema & Utilities
2. Configuration Parsing
3. Conversion Logic
4. Accessibility Checks
5. Build Directory Cleanup
6. HTML Generation & Button Rendering
7. CLI & Dry-Run/Reporting

---

## Constraints & Issues
- Each step must be testable and not break downstream steps.
- All errors should be logged, not fatal.
- Accessibility is integrated into user/admin outputs.
- Repeated builds should not leave stale files or DB records.
- Extensible for new export types, accessibility tools, or reporting features.

---

## Example Workflow
1. User runs:  
   `python make.py --dry-run --report`
2. System parses _content.yml, determines conversions.
3. For each file, attempts conversions (or simulates in dry-run).
4. Logs all results in DB with timestamps, reasons, forced flag, etc.
5. Runs accessibility checks with verify.py, logs results, and injects badges/labels.
6. Cleans up build/ to match current plan.
7. Generates HTML pages with accessible download buttons and accessibility badges/labels.
8. Writes build/admin/index.html with build and accessibility summary, and links to per-page accessibility reports.

---

## Notes & Considerations (for future self)
- Always start with DB/schema changes, as all logging/reporting depends on this.
- Test config parsing and merging logic in isolation before integrating with conversion.
- Conversion and accessibility logic should be robust to failures and always log reasons.
- Accessibility checks must be run after HTML generation but before final reporting.
- Cleanup logic must be safe and idempotent; test with custom output paths.
- HTML/button rendering must use metadata from config/DB and accessibility results.
- CLI should be intuitive; dry-run must not write or delete files.
- Admin report should aggregate both conversion and accessibility data for full transparency.
- Document all new DB fields and config options for future maintainers.
- If returning after time away, review this plan, DB schema, and config parsing logic first.

---

## Documentation Template (for new/changed modules)

```
### <module path>
- **Function:** <What does this module do?>
- **Database Usage:** <How does it use the DB?>
- **Extensibility:** <How could it be extended in the future?>
```

---

Let this plan guide incremental, testable development. Adjust as needed if requirements or constraints change.
