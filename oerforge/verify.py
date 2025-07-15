import datetime
import logging
from typing import List, Dict
import os

def run_wcag_zoo_on_page(page_path: str, browser: str) -> Dict:
    """
    Run axe-selenium-python accessibility tests on a single HTML page using the specified browser.
    Args:
        page_path: Path to the HTML file to test.
        browser: Browser to use ('chrome', 'firefox', etc.).
    Returns:
        Dictionary with results.
    """
    logging.info(f"Starting Axe Selenium test for {page_path} on {browser}")
    try:
        from selenium import webdriver
        from axe_selenium_python import Axe
        # Choose browser
        if browser.lower() == 'firefox':
            driver = webdriver.Firefox()
        elif browser.lower() == 'chrome':
            driver = webdriver.Chrome()
        else:
            raise ValueError(f"Unsupported browser: {browser}")
        # Open the local HTML file
        import os
        abs_path = os.path.abspath(page_path)
        driver.get(f"file://{abs_path}")
        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        violations = results.get('violations', [])
        result = {
            'page': page_path,
            'browser': browser,
            'status': 'success' if not violations else 'fail',
            'issues': violations,
            'axe_results': results
        }
        driver.quit()
        logging.info(f"Axe Selenium test completed for {page_path} on {browser}: {result}")
        return result
    except Exception as e:
        logging.error(f"Axe Selenium test failed for {page_path} on {browser}: {e}")
        return {'page': page_path, 'browser': browser, 'status': 'error', 'error': str(e)}

def run_wcag_zoo_on_all_pages(pages: List[str], browsers: List[str]) -> Dict[str, Dict[str, Dict]]:
    """
    Run axe-selenium-python tests on all pages for all browsers.
    Args:
        pages: List of HTML file paths.
        browsers: List of browsers to test.
    Returns:
        Nested dictionary: {page: {browser: results}}
    """
    results = {}
    for page in pages:
        results[page] = {}
        for browser in browsers:
            res = run_wcag_zoo_on_page(page, browser)
            results[page][browser] = res
    return results

def generate_markdown_report(results: Dict[str, Dict[str, Dict]]) -> str:
    """
    Generate a markdown report from the axe-selenium-python results.
    Args:
        results: Nested dictionary from run_wcag_zoo_on_all_pages.
    Returns:
        Markdown string summarizing results.
    """
    md = f"# Axe Selenium Accessibility Report\n\n"
    md += f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    for page, browser_results in results.items():
        md += f"## Page: {page}\n\n"
        for browser, result in browser_results.items():
            md += f"### Browser: {browser}\n\n"
            status = result.get('status', 'Unknown')
            md += f"**Status:** {status}\n\n"
            error = result.get('error', None)
            if error:
                md += f"**Error:** {error}\n\n"
            issues = result.get('issues', [])
            if issues:
                md += "#### Issues Found\n"
                for issue in issues:
                    desc = issue.get('description', '')
                    help_url = issue.get('helpUrl', '')
                    impact = issue.get('impact', '')
                    md += f"- **{issue.get('id', 'Unknown')}**: {desc} (Impact: {impact}) [More info]({help_url})\n"
                    for node in issue.get('nodes', []):
                        md += f"    - Element: {node.get('html', '')}\n"
                        for failure in node.get('failureSummary', '').split('\n'):
                            if failure.strip():
                                md += f"        - {failure.strip()}\n"
            else:
                md += "No accessibility issues found.\n"
            md += "\n"
    return md

def save_report_to_build_folder(report_md: str) -> str:
    """
    Save the markdown report as a page in build/files/wcag-reports/ with today's date and time.
    Args:
        report_md: Markdown report string.
    Returns:
        Path to the saved markdown file.
    """
    now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_dir = os.path.join("build", "files", "wcag-reports")
    if not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"wcag_report_{now}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    return report_path

def generate_one_markdown_report(result: Dict) -> str:
    """
    Generate a markdown report for a single axe-selenium-python result (for testing).
    Args:
        result: Dictionary from run_wcag_zoo_on_page.
    Returns:
        Markdown string summarizing the result.
    """
    # ...existing code...
    page = result.get('page', 'Unknown')
    browser = result.get('browser', 'Unknown')
    status = result.get('status', 'Unknown')
    issues = result.get('issues', [])
    error = result.get('error', None)
    md = f"# WCAG Report\n\n"
    md += f"**Page:** {page}\n\n"
    md += f"**Browser:** {browser}\n\n"
    md += f"**Status:** {status}\n\n"
    if error:
        md += f"**Error:** {error}\n\n"
    if issues:
        md += "## Issues Found\n"
        for issue in issues:
            md += f"- {issue}\n"
    else:
        md += "No accessibility issues found.\n"
    return md