<div align="center">
  <img src="images/logo.png" alt="OER-Forge Logo" width="120" />
  
  # OER-Forge
  
  **Build, share, and improve WCAG-compliant Open Educational Resources with Python!**
</div>

## Welcome

OER-Forge is an open source Python toolkit for building, organizing, and publishing accessible Open Educational Resources (OERs). Our goal: make it easy and fun to create sites and documents that meet [WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/) standards.

- **Accessible by design:** All templates and outputs aim for [WCAG compliance](https://www.w3.org/WAI/standards-guidelines/wcag/).
- **Database-driven navigation:** Section indices, menus, and hierarchy are managed in SQLite for robust, extensible site structure.
- **Multi-format export:** Markdown, DOCX, PDF, LaTeX, and more.
- **Built for maintainers:** Clean Code, SOLID principles, and a growing suite of tests.
- **Fun to hack:** Professional, but not boring. ☕️❤️

## Get Started

1. **Clone the repo:**
   ```sh
   git clone https://github.com/OER-Forge/OER-Forge.git
   cd OER-Forge
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Build the site:**
   ```sh
   python build.py
   ```
4. **View your site:**
   Open `build/index.html` in your browser.

## Features

- Section indices & navigation: DB-driven, supports arbitrary hierarchy, top-level and nested menus.
- Accessibility: ARIA labels, alt text, color contrast, keyboard navigation.
- Download options: Export pages in multiple formats (PDF, DOCX, TXT, etc.).
- Dark mode: Toggle theme for better readability.
- Inline figures: Markdown images with alt text for accessibility.
- Extensible templates: Jinja2-based, easy to customize.
- Robust build system: Automated, logs to `log/` for debugging.

## Get Involved

We welcome your feedback, suggestions, and contributions!

- [GitHub Issues](https://github.com/OER-Forge/OER-Forge/issues) 
- [Help wanted](https://github.com/OER-Forge/OER-Forge/labels/help%20wanted)

- **Report a bug:** [File an issue](https://github.com/OER-Forge/OER-Forge/issues/new?labels=bug)
- **Request a feature:** [File an enhancement](https://github.com/OER-Forge/OER-Forge/issues/new?labels=enhancement)
-**Ask a question:** [Open a question](https://github.com/OER-Forge/OER-Forge/issues/new?labels=question)

## License

Content and code are licensed under CC BY-NC-SA 4.0.


---
![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)
![GitHub Issues](https://img.shields.io/github/issues/OER-Forge/OER-Forge)
![Pull Requests](https://img.shields.io/github/issues-pr/OER-Forge/OER-Forge)
![GitHub Releases](https://img.shields.io/github/v/release/OER-Forge/OER-Forge)

