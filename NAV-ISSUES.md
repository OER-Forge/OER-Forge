# Navigation Menu Issues and Progress Log

## Overview
This document tracks the investigation, debugging, and resolution of navigation menu (nav) issues in the OER-Forge static site generator. The nav menu must always be present and correct on all pages, with links that match the actual output paths for all content, including nested/section roots and children. This log is intended for future reference and further improvements.

---

## Problem Statement
- **Initial Issue:**
  - Navigation menu links were sometimes incorrect, especially for nested/section root pages (e.g., `sample-resources/index.html`), and for children/grandchildren of sections.
  - In some builds, the nav menu was missing entirely from all pages.
  - The nav menu logic was not robust in resolving the correct output path for each menu item, especially for nested items.

- **Requirements:**
  - All nav menu links must use the output path as defined in the database (DB), not by fallback or guesswork.
  - The nav menu must be present and correct on every generated HTML page.
  - The audit script and nav builder must use the same logic for path resolution.

---

## Key Files and Functions
- `oerforge/make.py`: Main nav menu builder logic. Responsible for constructing the `top_menu` and rendering it into templates.
- `oerforge/scan.py`: Computes output paths for all content and writes them to the DB.
- `tests/audit_nav_vs_db.py`: Script to audit nav menu links against the DB for all menu items.
- `_content.yml`: Table of contents (TOC) source for menu structure.
- `layouts/_default/base.html`: Jinja2 template where the nav menu is rendered.
- `log/build.log`: Debug output for build and nav logic.

---

## Debugging and Fixes

### 1. **Initial Diagnosis**
- Found that nav menu links for section roots and children were not matching the DB output paths.
- The nav menu was sometimes missing due to failed DB lookups for menu items.
- Fallback logic in `make.py` caused inconsistencies.

### 2. **Audit Script**
- Created `tests/audit_nav_vs_db.py` to check all nav menu links against the DB output paths.
- Enhanced the script to check all menu items, including children and grandchildren.
- Ensured the audit script uses the same path resolution logic as the nav builder.

### 3. **Nav Builder Logic (make.py)**
- Patched the nav builder to always use the DB output path for every menu item.
- Removed fallback logic that guessed or constructed paths outside the DB.
- Enhanced DB lookup logic to try multiple path variants for each menu item:
  - `file_path`
  - `'content/' + file_path`
  - `'content/' + '/'.join(parent_slugs) + '/' + file_path` (for children/grandchildren)
- Added debug logging to trace nav link construction and DB lookups.

### 4. **Verification**
- Rebuilt the site (`python build.py`).
- Inspected generated HTML files for the presence and correctness of the nav menu.
- Used `grep` to confirm that `<nav>` is present and populated in all HTML files.
- Verified that all menu items (including nested/child items) link to the correct output paths as defined in the DB.

---

## Example: Nav Menu Output
For a nested page (e.g., `build/sample-resources/newton/newton.html`), the nav menu now renders as:

```html
<nav class="site-nav" role="navigation" aria-label="Main menu">
  <ul class="nav-menu">
      <li><a href="./index.html">Home</a></li>
      <li><a href="./sample-resources/index.html">Sample</a></li>
      <li><a href="./about.html">About</a></li>
  </ul>
</nav>
```

---

## Lessons Learned & Best Practices
- **Always use the DB output path** for nav menu links. Never guess or hardcode.
- **Keep audit and nav builder logic in sync** to avoid future regressions.
- **Add debug logging** for all DB lookups and nav construction steps.
- **Test all pages** (including nested/child pages) after any nav logic change.

---

## Next Steps / Open Questions
- Consider adding dropdowns or hierarchical nav for sections with children.
- Automate nav menu regression tests as part of CI.
- Document nav logic in code comments and README for future maintainers.

---

## References to Code
- See `oerforge/make.py` for nav menu construction and DB lookup logic.
- See `oerforge/scan.py` for output path computation and DB population.
- See `tests/audit_nav_vs_db.py` for nav-vs-DB audit logic.
- See `layouts/_default/base.html` for nav menu template rendering.

---

*Last updated: 2025-07-23*
