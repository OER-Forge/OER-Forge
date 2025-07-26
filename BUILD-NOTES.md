# BUILD-NOTES.md

OER-Forge Build Notes
=====================

## Current Functionality

OER-Forge is a database-driven static site generator for open educational resources (OER). The build process is managed by Python scripts and a SQLite database, with the following core features:

- **Markdown to HTML Conversion**: All Markdown files listed in `_content.yml` are converted to HTML using markdown-it-py and rendered with Jinja2 templates.
- **Database-Driven Navigation**: The SQLite database (`db/sqlite.db`) tracks all content, navigation, and asset relationships. Navigation menus are built from the database and `_content.yml` TOC.
- **Relative Link Rewriting**: All internal links and asset references are rewritten to be relative to the `build/` directory, ensuring compatibility with static hosting.
- **Static Asset Management**: Static files (CSS, JS, images) are copied to the build directory. Database-tracked images are also copied.
- **Site Metadata**: Site info (title, author, theme, etc.) is synced from `_content.yml` to the database.
- **Logging**: All build steps and errors are logged to `log/build.log` for debugging and inspection.

## Next Steps / Planned Features

1. **verify.py Integration**
   - Implement and integrate `verify.py` for automated validation of build output, link checking, and content integrity.

2. **Image Embedding**
   - Support for embedding both local and remote images in HTML output.
   - Ensure all images referenced in Markdown or the database are handled and copied/embedded as needed.

3. **IPYNB and DOCX Conversion**
   - Add support for converting Jupyter Notebooks (`.ipynb`) and Word documents (`.docx`) to HTML and other formats.
   - Integrate conversion results into the database and navigation.

4. **Download/Linked File Buttons**
   - Add UI buttons for downloading or linking to related files (e.g., PDF, DOCX, EPUB) on each page.
   - Start with buttons for all files linked in the database for each content page.

5. **Admin View**
   - Build an admin dashboard for inspecting and managing site content, conversions, and assets.
   - The presence and configuration of the admin view will be controlled by `_content.yml`.

## How to Build

1. Ensure all dependencies are installed (see `requirements.txt`).
2. Run `python build.py` or execute `make.py` directly to build the site.
3. Output is written to the `build/` directory, ready for static hosting.
4. Logs are available in `log/build.log`.

## Developer Notes

- All content and navigation are defined in `_content.yml` and tracked in the database.
- The build process is modular and extensible; new converters and features can be added with minimal changes to the core scripts.
- For best results, keep `_content.yml` and the database in sync, and check logs after each build.

---

For more details, see the code documentation in each script and the README.md.
