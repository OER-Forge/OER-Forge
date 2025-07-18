# OER-Forge Build & Robustness Checklist

_Last updated: 2025-07-18_

## 1. Build Pipeline
- [ ] Run `python make.py` to build the site and generate all outputs.
- [ ] Confirm all Markdown (.md) files are converted to all requested formats (PDF, DOCX, LaTeX, EPUB, TXT, etc.).
- [ ] Check that images in Markdown files appear in DOCX, PDF, and LaTeX outputs.
- [ ] Ensure all outputs are placed in the correct section-local directories (next to `index.html` and in `files/` as needed).
- [ ] Remove any duplicate or stub converter functions in `convert.py`.
- [ ] Clean up debug prints and stub counters in production code.

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
