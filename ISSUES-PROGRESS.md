# OER-Forge Issues Progress Tracker

_Last updated: 2025-07-18_

## Open Issues (GitHub)

### #6 Images in Markdown files missing in DOCX, PDF, and other outputs
- **Status:** Open
- **Summary:** Images appear in HTML, but are missing in DOCX, PDF, and other non-HTML outputs.
- **Progress:** Partial. HTML output is correct (see BUILD-NOTES.md), but other formats still need work.
- **Next Steps:** Focus on image handling in DOCX, PDF, and other converters (see `convert.py`).

### #4 Review and improve inline figures and alt text in markdown
- **Status:** Open
- **Summary:** Improve how inline figures and images are handled in markdown. Ensure descriptive alt text for accessibility.
- **Progress:** Not directly addressed yet.
- **Next Steps:** Review figure markup and alt text requirements in markdown and templates.

### #3 Dark mode: download buttons are hard to see and poorly positioned
- **Status:** Open
- **Summary:** Download buttons lack contrast and are poorly placed in dark mode.
- **Progress:** Not addressed yet.
- **Next Steps:** Update CSS for download buttons in dark mode for better visibility and placement.

### #2 Section index: verify and improve handling of grandchildren
- **Status:** Open
- **Summary:** Section index pages may not display grandchildren (nested descendants) correctly in navigation and content lists.
- **Progress:** Not addressed yet.
- **Next Steps:** Review and improve section index logic and template context for hierarchical navigation.

### #1 Section index menu works, but content missing
- **Status:** Open
- **Summary:** Navigation menu appears, but section content and children are missing or not rendered as expected.
- **Progress:** Not addressed yet.
- **Next Steps:** Investigate rendering logic, context passing, and template for section indices.

---

## Progress vs. Build Checklist
- Build pipeline, HTML output, and main index placement are complete (see BUILD-NOTES.md).
- Asset path review/fix is in progress (see section 1a in BUILD-NOTES.md).
- Issues #6, #4, #3, #2, and #1 remain open and are not fully resolved by recent work.

## Recommendations
- Prioritize image handling in non-HTML outputs (#6).
- Review and improve accessibility and navigation for section indices (#1, #2, #4).
- Update UI for dark mode (#3).
- Continue to update this tracker and BUILD-NOTES.md as progress is made.

---

Filed automatically by GitHub Copilot based on user request.
