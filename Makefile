.PHONY: audit-fix

## Run npm audit fix in apps/web with legacy-peer-deps (required for next-auth beta)
audit-fix:
	cd apps/web && npm audit fix --legacy-peer-deps
	@echo "Done. Check 'git diff apps/web/package-lock.json' for implicit transitive version bumps in packages listed in package.json."
