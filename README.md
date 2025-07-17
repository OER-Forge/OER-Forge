<div align="center">
  <img src="docs/images/logo.png" alt="OER-Forge Logo" width="120" />
  
  # OER-Forge 🛠️
  
  **Build, share, and improve WCAG-compliant Open Educational Resources with Python!**
</div>

## Overview

OER-Forge is an open source Python toolkit for building, organizing, and publishing accessible Open Educational Resources (OERs). It helps authors create sites and documents that meet [WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/) standards, with a focus on clean code, extensibility, and fun!

- **Accessible by design:** All templates and outputs aim for [WCAG compliance](https://www.w3.org/WAI/standards-guidelines/wcag/).
- **Database-driven navigation:** Section indices, menus, and hierarchy are managed in SQLite for robust, extensible site structure.
- **Multi-format export:** Markdown, DOCX, PDF, LaTeX, and more.
- **Built for maintainers:** Clean Code, SOLID principles, and a growing suite of tests.
- **Fun to hack:** Professional, but not boring. ☕️❤️

## Quick Start

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

- **Section indices & navigation:** DB-driven, supports arbitrary hierarchy, top-level and nested menus.
- **Accessibility:** ARIA labels, alt text, color contrast, keyboard navigation.
- **Download options:** Export pages in multiple formats (PDF, DOCX, TXT, etc.).
- **Dark mode:** Toggle theme for better readability ([issue #3](https://github.com/OER-Forge/OER-Forge/issues/3)).
- **Inline figures:** Markdown images with alt text for accessibility ([issue #4](https://github.com/OER-Forge/OER-Forge/issues/4)).
- **Extensible templates:** Jinja2-based, easy to customize.
- **Robust build system:** Automated, logs to `log/` for debugging.

## Open Issues & Roadmap

- [Section index content missing](https://github.com/OER-Forge/OER-Forge/issues/1)
- [Verify and improve handling of grandchildren in navigation](https://github.com/OER-Forge/OER-Forge/issues/2)
- [Dark mode download button visibility](https://github.com/OER-Forge/OER-Forge/issues/3)
- [Inline figures and alt text](https://github.com/OER-Forge/OER-Forge/issues/4)
- [Review verify.py for efficiency](https://github.com/OER-Forge/OER-Forge/issues)

See all issues and contribute: [GitHub Issues](https://github.com/OER-Forge/OER-Forge/issues)

## Contributing

We welcome your feedback, suggestions, and pull requests! Check out [good first issues](https://github.com/OER-Forge/OER-Forge/labels/good%20first%20issue) or [help wanted](https://github.com/OER-Forge/OER-Forge/labels/help%20wanted) to get started.

- **Report a bug:** [File an issue](https://github.com/OER-Forge/OER-Forge/issues/new?labels=bug)
- **Request a feature:** [File an enhancement](https://github.com/OER-Forge/OER-Forge/issues/new?labels=enhancement)
- **Ask a question:** [Open a question](https://github.com/OER-Forge/OER-Forge/issues/new?labels=question)

## License

Content and code are licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

---

Made with ☕️ and ❤️ for students and educators everywhere. | Built with [OER-Forge](https://github.com/OER-Forge/OER-Forge)
