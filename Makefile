.DEFAULT_GOAL := help
.PHONY: help audit-fix neon-usage

help:
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:' $(MAKEFILE_LIST) | grep -v '^help:' | awk -F: '{printf "  %s\n", $$1}'
	@echo ""
	@echo "See apps/scraper/Makefile for scraper-specific targets (e.g. 'make -C apps/scraper club ID=<n>')."

## Run npm audit fix in apps/web with legacy-peer-deps (required for next-auth beta)
audit-fix:
	cd apps/web && npm audit fix --legacy-peer-deps
	@echo "Done. Check 'git diff apps/web/package-lock.json' for implicit transitive version bumps in packages listed in package.json."

## Report Neon compute, storage, PITR/history, network transfer, and branch usage
neon-usage:
	python3 scripts/neon_usage_report.py
