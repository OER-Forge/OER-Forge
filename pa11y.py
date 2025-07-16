from oerforge.verify import process_all_html_files, load_pa11y_config

db_path = "db/sqlite.db"
config_data = load_pa11y_config("_content.yml")
wcag_level = config_data.get("wcag_level", "WCAG2AA")
config_file = config_data.get("config", "pa11y-config/pa11y.wcag.aa.json")

process_all_html_files(build_dir="build", wcag=wcag_level, config_file=config_file, db_path=db_path)