# OER-Forge: Recent Changes and Improvements

## Overview
This document summarizes the key changes, enhancements, and fixes made to the OER-Forge static site generator and its supporting Python package during the recent development and debugging sessions.

---

## 1. Section Index File Handling (`_index.md`)
- **Problem:** Section landing pages (`_index.md`) were not being processed unless explicitly referenced in the TOC (`_content.yml`).
- **Solution:** Enhanced the TOC scanning logic in `scan.py` to automatically detect and include `_index.md` files for any section with children, even if not referenced in the TOC. This ensures all section landing pages are built and included in the site.
- **Benefit:** Reduces TOC duplication, follows the Principle of Least Surprise, and keeps content organization DRY and maintainable.

## 2. Internal Markdown Link Rewriting
- **Problem:** Internal links like `[Page](page.md)` in Markdown did not always work in the generated HTML, as they pointed to `.md` files instead of `.html`.
- **Solution:** Added robust link rewriting to the Markdown-to-HTML conversion pipeline in `make.py` using `markdown-it-py`. All internal links to `.md` files are now automatically rewritten to `.html` in the output.
- **Benefit:** Ensures navigation always works in the generated site, regardless of how links are written in the Markdown source.

## 3. Markdown Conversion with `markdown-it-py`
- **Upgrade:** The build pipeline now uses the `markdown-it-py` library for Markdown parsing and rendering, supporting CommonMark, footnotes, and math plugins.
- **Customization:** Custom image rendering and accessibility improvements (e.g., ARIA roles for tables, lists, navigation, etc.) are included in the HTML output.

## 4. Best Practices and Documentation Guidance
- **Internal Links:** Documented the best practice of always linking to `.md` files in Markdown. The build system will handle rewriting for the target output format.
- **Section Indexes:** Documented the new behavior for section landing pages and how to structure the TOC and content directories for clean, maintainable builds.

## 5. General Debugging and Build Pipeline Improvements
- **Database Initialization:** Ensured the database and tables are always created and up-to-date before scanning or building.
- **Logging:** Improved logging for easier debugging and traceability of build steps and asset registration.
- **Error Handling:** Added or improved error handling for missing dependencies, files, and schema mismatches.

---

## Next Steps
- Optionally extend link rewriting to support `.ipynb` output for Jupyter conversion.
- Continue to test and document edge cases for navigation, asset management, and content conversion.

---

*This document is auto-generated to help track recent development and ensure clarity for all contributors.*
