# Laughtrack Scraper Project Context

## Things to Never Do

- Never consider backwards-compatibility. We only have and only ever will have one client.
- Never create a summary markdown file unless explicitly requested.
- Never use BeautifulSoup in any file other than the HtmlScraper. Only that class should have a reference to BeautifulSoup.

## Things to Always Do

- Always refer to scraper-architecture-patterns.md in the docs directory when working on scrapers. Scrapers must follow the patterns outlined there.
- Always delete your testing script files after you have run your tests. We do not want to pollute the root directory.
- Always make sure you are in a virtual environment before installing any packages or expecting to run commands. This is a python project.
- Always use dataclasses instead of typeddicts where possible.
- Always use what's in the Makefile to run commands. Never run scripts directly.
