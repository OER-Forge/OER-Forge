<img src="images/logo.png" alt="OER-Forge Logo" width="400" />
  
# OER-Forge
  
**Build, share, and improve WCAG-compliant Open Educational Resources with Python!**

[**Jump to Font Controls**](#font-controls)

## Welcome

OER-Forge is an open source Python toolkit for building, organizing, and publishing accessible Open Educational Resources (OERs). Our goal: make it easy and fun to create sites and documents that meet [WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/) standards.

- **Accessible by design:** All templates and outputs aim for [WCAG compliance](https://www.w3.org/WAI/standards-guidelines/wcag/).
- **Database-driven navigation:** Section indices, menus, and hierarchy are managed in SQLite for robust, extensible site structure.
- **Multi-format input:** Write content in Markdown ✅, DOCX ⏳, and Jupyter Notebooks ⏳.
- **Multi-format export:** Markdown ✅, DOCX ✅, PDF ✅, LaTeX ✅, and TXT ✅.
- (optional) **Validation using Pa11y:** Automated checks ✅ and open reporting ⏳ during and after build to ensure compliance. [Pa11y on GitHub](https://github.com/pa11y/pa11y)

## Get Started

1. **Clone the repo:**
   ```sh
   git clone https://github.com/OER-Forge/OER-Forge.git
   cd OER-Forge
   ```
2. (optional) **Create a virtual environment and activate it:**
   ```sh
   python -m venv venv
   source venv/bin/activate
   ```
   **On Windows use:**
   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Build the sample site:**
   ```sh
   python build.py
   ```
5. **View your site:**
   Open `build/index.html` or `docs/index.html` in your browser.

## Features

### Accessibility & Usability
- **Accessible by design:** ARIA labels, alt text, color contrast, and keyboard navigation. ✅
- **Adjustable interface:** User controls for text size, spacing, and layout. ✅
- **Dark mode:** Toggle theme for better readability. ✅
- **Responsive design:** Mobile-friendly layouts and navigation. ✅

### Content & Input Formats
- **Multi-format input:** Markdown ✅, DOCX ⏳, Jupyter Notebooks ⏳
- **Tables & lists:** Advanced Markdown tables, nested lists, and task lists. ✅
- **Inline figures:** Markdown images with alt text for accessibility. ✅
- **Math support:** LaTeX-style math rendering with MathJax. ✅
- **Syntax highlighting:** Beautiful code blocks with Pygments. ✅

### Navigation & Structure
- **Section indices & navigation:** Database-driven, supports arbitrary hierarchy, top-level and nested menus. ✅
- **Cross-references:** Link sections, figures, tables, and listings easily. ⏳
- **Footnotes & endnotes:** Standard Markdown syntax for notes. ⏳

### Export & Download
- **Download options:** Export pages in multiple formats (PDF, DOCX, TXT, etc.). ✅

### Citations & References
- **Citations & references:** Manage bibliographies with BibTeX. ⏳

### Presentation & Customization
- **Callouts & alerts:** Styled boxes for tips, warnings, and important info. ✅
- **Extensible templates:** Jinja2-based, easy to customize. ✅

### Build System
- **Robust build system:** Automated, logs to `log/` for debugging. ✅

## Documentation

[Comprehensive documentation](https://oer-forge.github.io/docs/) is available and hosted on [GitHub](https://github.com/OER-Forge/docs).

## Get Involved

We welcome your feedback, suggestions, and contributions! Please use [GitHub Issues](https://github.com/OER-Forge/OER-Forge/issues) to report bugs, request features, or ask questions.

- **Contribute a Pull Request:** [Help wanted](https://github.com/OER-Forge/OER-Forge/labels/help%20wanted)
- **Report a bug:** [File an issue](https://github.com/OER-Forge/OER-Forge/issues/new?labels=bug)
- **Request a feature:** [File an enhancement](https://github.com/OER-Forge/OER-Forge/issues/new?labels=enhancement)
- **Ask a question:** [Open a question](https://github.com/OER-Forge/OER-Forge/issues/new?labels=question)

## License

Content and code are licensed under CC BY-NC-SA 4.0.

## Getting OER-Forge

OER-Forge is hosted on [GitHub](https://github.com/OER-Forge/OER-Forge).

![Last Commit](https://img.shields.io/github/last-commit/OER-Forge/OER-Forge)
![Size](https://img.shields.io/github/languages/code-size/OER-Forge/OER-Forge)
![Contributors](https://img.shields.io/github/contributors/OER-Forge/OER-Forge)
![Stars](https://img.shields.io/github/stars/OER-Forge/OER-Forge)

![GitHub Issues](https://img.shields.io/github/issues/OER-Forge/OER-Forge)
![Pull Requests](https://img.shields.io/github/issues-pr/OER-Forge/OER-Forge)

![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)

