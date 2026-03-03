# Prevent pytest module name collision with Broadway tests that also use the
# basename 'test_scraper_helpers.py'. We keep our CC-specific helpers in
# 'test_scraper_helpers_cc.py' and ignore the legacy filename in this folder.
collect_ignore_glob = [
    "test_scraper_helpers.py",
]
