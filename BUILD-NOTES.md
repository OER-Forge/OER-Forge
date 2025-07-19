
# BUILD-NOTES.md

## Current Status (2025-07-19)

### What Works
- **Static site build process**: Markdown files are converted to HTML using Jinja2 templates and markdown-it-py.
- **Navigation**: Top-level and nested navigation is generated from `_content.yml` and slugs, with special-casing for the home page (`index.md` with slug `main`).
- **Asset copying**: Static assets and images are copied to the build directory.
- **Database**: SQLite database is used for content, files, and site info. Initialization and population from content files works.
- **Tests**: Some tests pass, including slugify and export config merging.

### Outstanding Issues (Test Failures)
1. **Migration logic**
   - `test_migrate_database_entrypoint` fails: migration function does not add expected columns (`reason`, `forced`, `custom_label`, `created_at`) to `conversion_results` and `accessibility_results` tables.
   - **Action needed**: Implement a `migrate_database` function in `db_utils.py` that adds missing columns if not present.

2. **Files table registration**
   - `test_files_table_registration` fails: referenced assets (e.g., `sample.png`) are not registered in the `files` table during scan.
   - **Action needed**: Update scan logic to ensure all referenced files (especially images in markdown) are inserted into the `files` table.

3. **Navigation link for About page**
   - `test_top_level_nav_links` fails: About page (slug `main`, file `about.md`) should link to `./about.html`, but currently links to `./main.html`.
   - **Action needed**: Adjust nav logic to only special-case the home page (`index.md` with slug `main` → `index.html`). For other files with slug `main`, use the filename (e.g., `about.md` → `about.html`).

### Next Steps
- [ ] Implement `migrate_database` in `db_utils.py` and ensure it is called in tests and/or build process.
- [ ] Update scan logic to register all referenced assets in the `files` table.
- [ ] Refine nav link logic in `make.py` to match test expectations for About and similar pages.
- [ ] Re-run tests after each fix to confirm resolution.

---

**Reference:** See `make.py`, `db_utils.py`, `scan.py`, and the test suite in `tests/` for details on current logic and test expectations.

# OER-Forge Build & Robustness Checklist

_Last updated: 2025-07-18_

## 1. Build Pipeline
- [x] Run `python make.py` to build the site and generate all outputs.
- [x] Confirm all Markdown (.md) files are converted to all requested formats (PDF, DOCX, LaTeX, EPUB, TXT, etc.).
- [x] Check that images in Markdown files appear in DOCX, PDF, and LaTeX outputs.
- [x] Ensure all outputs are placed in the correct section-local directories (next to `index.html` and in `files/` as needed). Main `index.html` is now always in the build root.
- [ ] Remove any duplicate or stub converter functions in `convert.py`.
- [ ] Clean up debug prints and stub counters in production code.

## 1a. Static Asset Path Robustness (2025-07-18)

- [ ] Review and fix all CSS, JS, and image paths in generated HTML to ensure they are correct relative links from every page (including subdirectories) to the assets in `build/`.
- [ ] Confirm all static assets (css, js, images) are copied to the correct subfolders in `build/` (e.g., `build/css/`, `build/js/`, `build/images/`).
- [ ] Use the database (`db/sqlite.db`) to help resolve and verify asset file paths as needed.
- [ ] Ensure all asset links are correct for static deployment (site is self-contained, all links work regardless of page depth).
- [ ] Confirm that any changes to file links are logged and/or updated in the database if required.

**Note:** The build now syncs site context from `_content.yml` to the `site_info` table in the database and warns if there is a mismatch. Main page is always at `build/index.html` for static hosting. Asset path review/fix is in progress.

## 2. Accessibility (WCAG) Verification
- [ ] Run `verify.py` on all generated HTML files.
- [ ] Log accessibility results in the database.
- [ ] Inject accessibility badges/labels into HTML pages.
- [ ] Generate and link per-page accessibility reports.
- [ ] Summarize accessibility results in the admin/build report.

## 3. Admin Pages & Reporting
- [ ] Implement or update `build/admin/index.html` to summarize all build and accessibility results.
- [ ] Include links to all outputs and per-page accessibility reports.
- [ ] Ensure the admin report is accessible and easy to scan.

## 4. Robustness & Cleanup
- [ ] Remove obsolete outputs from `build/` to match the current export plan.
- [ ] Ensure repeated builds do not leave stale files or DB records.
- [ ] Log all errors and reasons for failed conversions or checks (do not block build).

## 5. CLI & User Experience
- [ ] Add CLI options for `--dry-run`, `--force`, and `--report` in `make.py`.
- [ ] Ensure CLI is intuitive and safe (no destructive actions in dry-run mode).
- [ ] Print build and accessibility summaries to console and write to admin report.

## 6. Documentation & Extensibility
- [ ] Update README and in-code documentation to reflect the current pipeline, config, and output structure.
- [ ] Document all new database fields and config options for future maintainers.
- [ ] Ensure the system is extensible for new export types, accessibility tools, or reporting features.

## 7. Testing & Validation
- [ ] Test all conversions and accessibility checks with real content, including edge cases (images, custom paths, forced conversions).
- [ ] Move or refactor sections and confirm all internal links and assets remain valid.
- [ ] Run repeated builds with config changes to ensure robustness.

---

**Tip:** Work through this checklist after every major refactor or before a release to ensure OER-Forge remains robust, accessible, and maintainable.

---

Filed automatically by GitHub Copilot based on user request.
