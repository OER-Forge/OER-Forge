# OER-Forge Conversion Pipeline: Progress Notes

## Current Status (2025-07-18)

### What Has Been Done
- The build pipeline runs and scans content, populates the database, and attempts conversions.
- All possible Markdown (.md) converters have been implemented using Pandoc or standard Python, with image handling where relevant:
  - `.md` → `.txt`: Pandoc to plain text (images ignored)
  - `.md` → `.md`: File copy (identity)
  - `.md` → `.marp`: File copy (for Marp slides)
  - `.md` → `.tex`: Pandoc to LaTeX (images as includegraphics)
  - `.md` → `.pdf`: Pandoc to PDF (images embedded)
  - `.md` → `.docx`: Pandoc to DOCX (images extracted and embedded)
  - `.md` → `.ppt`: Pandoc to PPTX (images embedded)
  - `.md` → `.jupyter`: Pandoc to Jupyter Notebook (images as attachments)
- All converter stubs for other file types are present, but only the above are implemented.
- There were duplicate function definitions for .md converters; these should be cleaned up (keep only the real implementations).

### What Needs Attention
- Remove duplicate .md converter function definitions to avoid Python errors.
- Implement or improve converters for other file type pairs as needed.
- Some Pandoc conversions (e.g., to PDF) may fail if the Markdown contains unsupported Unicode or LaTeX issues.
- The pipeline prints debug info and stub counts; this can be cleaned up for production.

### Next Steps
- Clean up duplicate function definitions in `convert.py`.
- Test all .md conversions with real content, especially image handling.
- Decide which other converters to implement next (e.g., .docx, .ipynb, .marp, etc.).
- Document the conversion pipeline and usage in the README.

---

*This file is auto-generated to help you track the current state of the OER-Forge conversion pipeline. Update as you make progress!*
