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