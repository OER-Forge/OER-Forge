
# OER-Forge

OER-Forge is a database-driven static site generator for open educational resources (OER). It converts Markdown and other source files into a fully navigable, static HTML website, using a SQLite database as the source of truth for content, navigation, and assets.

## Features

- **Markdown to HTML Conversion**: Converts all Markdown files listed in `_content.yml` to HTML using markdown-it-py and Jinja2 templates.
- **Database-Driven Navigation**: Navigation menus and content relationships are managed in a SQLite database (`db/sqlite.db`), populated from `_content.yml`.
- **Relative Link Rewriting**: All internal links and asset references are rewritten to be relative to the `build/` directory for static hosting compatibility.
- **Static Asset Management**: Copies CSS, JS, and image assets to the build directory. Images referenced in the database are also copied.
- **Site Metadata**: Site information (title, author, theme, etc.) is synced from `_content.yml` to the database.
- **Logging**: All build steps and errors are logged to `log/build.log` for debugging and inspection.

## Getting Started

### Prerequisites
- Python 3.8+
- All dependencies listed in `requirements.txt`

### Build Instructions
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Edit `_content.yml` to define your site structure, navigation, and metadata.
3. Run the build:
   ```sh
   python build.py
   # or
   python oerforge/make.py
   ```
4. The generated site will be in the `build/` directory, ready for static hosting.
5. Check `log/build.log` for build details and errors.

## Project Structure

- `build/` — Output directory for generated HTML and assets
- `content/` — Source Markdown and other content files
- `db/` — SQLite database and related files
- `layouts/` — Jinja2 HTML templates
- `log/` — Build and database logs
- `oerforge/` — Core Python package (build scripts, utilities)
- `tests/` — Test scripts
- `_content.yml` — Site structure, navigation, and metadata
- `requirements.txt` — Python dependencies
- `README.md` — This file
- `BUILD-NOTES.md` — Developer build notes and roadmap

## Next Steps / Roadmap

- **verify.py Integration**: Automated validation of build output, link checking, and content integrity.
- **Image Embedding**: Support for embedding both local and remote images in HTML output.
- **IPYNB and DOCX Conversion**: Add support for converting Jupyter Notebooks (`.ipynb`) and Word documents (`.docx`).
- **Download/Linked File Buttons**: UI buttons for downloading or linking to related files (PDF, DOCX, EPUB, etc.) on each page.
- **Admin View**: Admin dashboard for managing site content and conversions, controlled by `_content.yml`.

## Contributing

Contributions are welcome! Please:
- Keep code clean, DRY, and well-documented.
- Reference the database and `_content.yml` structure in your changes.
- Add or update docstrings and usage examples as needed.
- Run tests and check logs before submitting a pull request.

## License

See `LICENSE` for details.

---

For more information, see `BUILD-NOTES.md` and the code documentation in each script.
