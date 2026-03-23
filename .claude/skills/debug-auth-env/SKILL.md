---
name: debug-auth-env
description: Debug production auth failures by pulling Vercel env vars and checking for leading/trailing whitespace in AUTH_URL and other auth-related variables.
allowed-tools: Bash
---

# Debug Auth Env Skill

Pulls production environment variables from Vercel and checks for leading/trailing
whitespace in auth-related vars — the most common silent cause of OAuth callback
URL mismatches in production.

## Background

The Vercel dashboard only shows "Encrypted" for secret values. A trailing space in
`AUTH_URL` (e.g. `"https://laugh-track.com "`) causes OAuth callback URL mismatches
that fail silently with no useful error message. Vercel does not support in-place
edits — the fix is to remove and re-add the variable.

## Steps

1. Link the project and pull production env vars to a temp file:

```bash
cd apps/web && vercel link --yes --project laughtrack 2>/dev/null
vercel env pull --environment production /tmp/vercel-prod-env
```

2. Check for leading/trailing whitespace in auth-related variables:

```bash
python3 - <<'EOF'
import re

AUTH_VARS = [
    "AUTH_URL", "AUTH_SECRET", "AUTH_GOOGLE_ID", "AUTH_GOOGLE_SECRET",
    "AUTH_APPLE_ID", "AUTH_APPLE_SECRET", "NEXTAUTH_URL", "NEXTAUTH_SECRET",
]

issues = []
with open("/tmp/vercel-prod-env") as f:
    for line in f:
        line = line.rstrip("\n")
        if "=" not in line or line.startswith("#"):
            continue
        key, _, val = line.partition("=")
        # Strip surrounding quotes if present
        if val.startswith('"') and val.endswith('"'):
            inner = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            inner = val[1:-1]
        else:
            inner = val
        if key in AUTH_VARS and inner != inner.strip():
            issues.append((key, inner))

if issues:
    print("\n⚠️  WHITESPACE DETECTED in the following auth variables:\n")
    for key, val in issues:
        print(f"  {key} = {repr(val)}")
    print("\nFix commands (run from apps/web/):\n")
    for key, val in issues:
        clean = val.strip()
        print(f'  vercel env rm {key} production --yes')
        print(f'  echo "{clean}" | vercel env add {key} production')
        print()
else:
    print("\n✅  No whitespace issues found in auth variables.")

print("\nFull env dump:")
EOF
```

3. Print the full env file for manual inspection:

```bash
cat /tmp/vercel-prod-env
rm /tmp/vercel-prod-env
```

4. If whitespace was detected, the fix commands were printed above. After running them,
   re-run `/debug-auth-env` to confirm the values are clean.
