# OERForge Codebase: Module-by-Module Summary (with Database Usage)

## Task Overview
This section provides a detailed summary of every major module in the OERForge codebase. For each module, we describe its primary function, how it interacts with the database (if at all), and note opportunities for future extensibility. This is intended to aid maintainers, contributors, and users in understanding the architecture and data flow of OERForge.

---

## Step-by-Step Module Summaries

### oerforge/make.py
- **Function:** Main build orchestrator. Scans content, triggers conversions, generates HTML, and manages download link/button creation.
- **Database Usage:** Heavy. Uses `db_utils` to fetch content, file, and conversion records; updates page-file mappings; logs build steps.
- **Extensibility:** Could further modularize page generation and download button logic for easier customization.

### oerforge/convert.py
- **Function:** Handles all file conversions (Markdown to DOCX, PDF, LaTeX, TXT, etc.).
- **Database Usage:** Inserts/updates records in `files` and `conversion_results` tables; logs conversion outcomes.
- **Extensibility:** Could support more formats or conversion backends; add richer error tracking in DB.

### oerforge/copyfile.py
- **Function:** Copies static assets and content files to the build directory; manages `.nojekyll` for GitHub Pages.
- **Database Usage:** Records image and asset usage in DB via `db_utils`.
- **Extensibility:** Could track more asset metadata or support asset versioning.

### oerforge/db_utils.py
- **Function:** Centralizes all database schema, connection, and query logic. Defines tables: `content`, `files`, `conversion_results`, `conversion_capabilities`, `pages_files`, `accessibility_results`, `site_info`.
- **Database Usage:** Core. All DB operations go through here.
- **Extensibility:** Add migrations, richer schema validation, or support for other DB engines.

### oerforge/scan.py
- **Function:** Scans content/ for Markdown and asset files; populates DB with discovered content and asset records; extracts images.
- **Database Usage:** Inserts/updates in `content`, `files`, and related tables.
- **Extensibility:** Could add support for more content types or richer metadata extraction.

### oerforge/export_all.py
- **Function:** Batch export orchestrator. Runs all conversions and asset copies in bulk; logs to export.log.
- **Database Usage:** Indirect, via `convert.py` and `copyfile.py`.
- **Extensibility:** Could add selective export, parallelization, or export presets.

### oerforge/verify.py
- **Function:** Runs accessibility checks (e.g., via Pa11y), stores results, injects badges, and generates accessibility reports.
- **Database Usage:** Writes to `accessibility_results` and related tables.
- **Extensibility:** Could support more accessibility tools or richer reporting.

### oerforge/section.html (Jinja2 template)
- **Function:** Template for section pages; renders content, download buttons, and accessibility badges.
- **Database Usage:** None directly, but expects DB-driven context from `make.py`.
- **Extensibility:** Can be extended for custom layouts or theming.

### oerforge/__init__.py
- **Function:** Package docstring and version.
- **Database Usage:** None.
- **Extensibility:** N/A.

### oerforge_admin/export_db_html.py
- **Function:** Admin tool to export DB tables as HTML for inspection or documentation.
- **Database Usage:** Reads all tables, generates HTML views.
- **Extensibility:** Could add CSV/JSON export, filtering, or search.

### oerforge_admin/generate_docs_index_html.py
- **Function:** Generates a docs index HTML from README.md using a template; copies CSS/JS/image assets.
- **Database Usage:** None.
- **Extensibility:** Could support more doc sources or richer templating.

---

## Documentation Template
For new modules, use this template:

```
### <module path>
- **Function:** <What does this module do?>
- **Database Usage:** <How does it use the DB?>
- **Extensibility:** <How could it be extended in the future?>
```

---

## Example (from codebase)

```
### oerforge/convert.py
- **Function:** Handles all file conversions (Markdown to DOCX, PDF, LaTeX, TXT, etc.).
- **Database Usage:** Inserts/updates records in `files` and `conversion_results` tables; logs conversion outcomes.
- **Extensibility:** Could support more formats or conversion backends; add richer error tracking in DB.
```

---

# End of Module Summary
