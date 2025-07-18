# Section-Local Files Directory Strategy

## Overview
All static assets (images, PDFs, EPUBs, etc.) for a section or page are placed in a `files/` directory at the same level as the section's `index.html`. This ensures robust, portable, and maintainable internal linking.

## Directory Layout
- Each section/page:  
  - `index.html`
  - `files/` (all assets for this section)

## Linking
- Use relative links: `./files/asset.png`
- No need to rewrite links when moving or copying sections.

## Moving or Refactoring Sections
- Move the entire section directory (including `files/`).
- All internal links remain valid.

## Conversion Pipeline
- During conversion, output all assets to the local `files/` directory.
- Rewrite links in HTML/Markdown to point to `./files/asset.ext`.
- Update the database with the relative asset paths.

## Benefits
- Maximum modularity and portability.
- Easy offline use and remixing.
- Minimal maintenance for internal links.

# OER-Forge Modular Output: File Move and Conversion Logic

## Overview
This document describes the logic and best practices for modular, section-local output in the OER-Forge static site generator. It explains how the conversion pipeline determines output paths for all requested formats, ensuring a strict, config-driven, filename-based directory structure.

## Output Path Logic
- Each content file is assigned an `output_path` in the database, reflecting its section-local, modular location (e.g., `build/section/index.html`).
- All export types (e.g., `.md`, `.pdf`, `.tex`, `.docx`, `.epub`, `.txt`) are generated in the same directory as the `output_path`, swapping only the extension.
- Children of slug-rewritten sections are output to the correct parent folder, as determined by the TOC and config.

## Example
If a content file has `output_path` set to:
```
build/sample-resources/activities/activities.html
```
Then all export types will be generated as:
```
build/sample-resources/activities/activities.md
build/sample-resources/activities/activities.pdf
build/sample-resources/activities/activities.tex
build/sample-resources/activities/activities.docx
build/sample-resources/activities/activities.epub
build/sample-resources/activities/activities.txt
```

## Implementation Details
- The main conversion loop in `oerforge/convert.py` uses the `output_path` from the database as the base for all export types.
- The extension is swapped for each requested format, as specified in the export config.
- The logic is driven by the merged export config and TOC hierarchy from `_content.yml`.
- Section-local files/ directories are determined by the parent folder of `output_path`.

## Best Practices
- Always use the `output_path` from the database as the base for all exports.
- Avoid hardcoding output directories; rely on config and TOC-driven logic.
- Ensure all outputs (including `.md`) are generated in the correct modular, section-local directory.
- Use docstrings and comments to clarify logic in the codebase.

## References
- See `oerforge/convert.py` for the main conversion logic.
- See `scan.py` for section path propagation and TOC-driven output structure.
- See `_content.yml` for site config and TOC.

---
_Last updated: 2025-07-18_