## 🚀 Release v0.9.2 "Unified Urubu" Highlights

- **Unified All-in-One Build:** The `--all` flag now runs all major build steps in strict order: DOCX (and Markdown) → PDF → Jupyter Book HTML → Custom HTML web output. All output formats are copied to `docs/sources/<notebook_stem>/` for each notebook.
- **Jupyter Book HTML Improvements:** Built into a temp directory, then copied to both `docs/jupyter/` and `docs/sources/jupyterbook_html/` for easy access and deployment.
- **Documentation Overhaul:** `README.md` and `build.md` have been fully rewritten to reflect the new build workflow, directory structure, and usage patterns.
- **Output Directory Clarity:** All outputs are organized in `_build/` (intermediate) and `docs/` (final, published), with clear subfolders for each format. Downloadable sources for each notebook are always available in `docs/sources/<notebook_stem>/`.
- **Robust Image Handling:** All referenced images are collected into `_build/images/` and linked consistently in all output formats.
- **No Automatic Cleanup:** The build system no longer deletes any files or folders automatically; manual cleanup is recommended if needed.

See the `releases/` folder for full historical release notes.

For more details and instructions, see the [Release Notes](https://github.com/dannycab/modern-classical-mechanics/releases).