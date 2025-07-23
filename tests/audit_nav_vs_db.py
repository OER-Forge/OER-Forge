"""
Audit script for navigation menu vs. database output paths.

This script checks that every nav menu link generated from the TOC matches an actual output_path in the database.
It also reports any mismatches or missing links for easier debugging of navigation issues.

Usage:
    python tests/audit_nav_vs_db.py

Requirements:
    - The site must be built and the database must exist.
    - Assumes the default DB_PATH and _content.yml locations.
"""
import os
import sqlite3
import yaml

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'sqlite.db')
CONTENT_YML = os.path.join(os.path.dirname(__file__), '..', '_content.yml')


def load_toc():
    with open(CONTENT_YML, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('toc', [])


def get_content_lookup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_path, slug, output_path FROM content WHERE mime_type = '.md'")
    lookup = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
    conn.close()
    return lookup


def build_nav_links(items, content_lookup, parent_slugs=None):
    nav_links = []
    parent_slugs = parent_slugs or []
    for item in items:
        if not item.get('menu', True):
            continue
        file_path = item.get('file', '')
        slug = item.get('slug', None)
        # Logic mirrors make.py build_nav
        if (file_path in ("index.md", "content/index.md") and slug == "main"):
            link = './index.html'
        elif slug == "main" and file_path.endswith(".md"):
            link = './' + os.path.splitext(os.path.basename(file_path))[0] + '.html'
        else:
            full_slugs = parent_slugs + [slug] if slug else parent_slugs
            output_path = content_lookup.get((file_path, slug))
            if output_path:
                link = './' + output_path.replace('build/', '').lstrip('/')
            elif full_slugs:
                link = './' + '/'.join(full_slugs) + '.html'
            else:
                link = './' + file_path.replace('.md', '.html').replace('content/', '').lstrip('/')
        nav_links.append({'title': item.get('title', ''), 'link': link, 'file': file_path, 'slug': slug})
        if 'children' in item and item['children']:
            nav_links.extend(build_nav_links(item['children'], content_lookup, parent_slugs + ([slug] if slug else [])))
    return nav_links


def main():
    toc = load_toc()
    content_lookup = get_content_lookup()
    nav_links = build_nav_links(toc, content_lookup)
    # Build set of all output_paths for quick lookup
    all_output_paths = set(content_lookup.values())
    print("\n--- Navigation Menu Audit ---\n")
    errors = 0
    for nav in nav_links:
        # Remove leading './' for comparison
        nav_path = nav['link'][2:] if nav['link'].startswith('./') else nav['link']
        if nav_path not in all_output_paths:
            # Try to find a close match in the DB for this nav item
            file = nav['file']
            slug = nav['slug']
            # Look up by (file, slug)
            db_output = content_lookup.get((file, slug))
            suggestion = ""
            # Also check for DB entries with or without 'content/' prefix
            file_variants = set([file])
            if not file.startswith('content/'):
                file_variants.add('content/' + file)
            elif file.startswith('content/'):
                file_variants.add(file[len('content/'):])
            # Find all DB entries for any variant of this file
            db_matches = [(f, s, v) for (f, s), v in content_lookup.items() if f in file_variants]
            if db_output:
                suggestion = f"Resolution: Update your TOC or nav logic to use './{db_output.replace('build/', '').lstrip('/')}' for this menu item."
            elif db_matches:
                print(f"[MISSING] Nav link '{nav['link']}' (title: '{nav['title']}', file: '{file}', slug: '{slug}') not found in DB output paths.")
                print(f"         Potential matches in DB for this file (any slug):")
                for match_file, match_slug, match_path in db_matches:
                    print(f"           source_path: '{match_file}', slug: '{match_slug}' -> './{match_path.replace('build/', '').lstrip('/')}'")
                suggestion = "Resolution: Check the slug and file path in your TOC and match it to one of the above output paths."
            else:
                print(f"[MISSING] Nav link '{nav['link']}' (title: '{nav['title']}', file: '{file}', slug: '{slug}') not found in DB output paths.")
                suggestion = "Resolution: Check that the file exists and is included in your build/database."
            if db_output:
                print(f"         DB output path: './{db_output.replace('build/', '').lstrip('/')}'")
            print(f"         {suggestion}")
            errors += 1
    if errors == 0:
        print("All nav menu links match database output paths!\n")
    else:
        print(f"\n{errors} nav menu links did not match any database output path. See above for suggested resolutions.\n")

if __name__ == "__main__":
    main()
