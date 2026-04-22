---
name: apple-jwt
description: Regenerate the Apple OAuth JWT secret and update .env.local and Vercel production
---

# Apple JWT Regeneration Skill

Regenerates the `AUTH_APPLE_SECRET` JWT for Apple OAuth sign-in and updates both
`.env.local` and Vercel production. Run this every ~6 months before the token expires.

## Credentials (do not change these)

- **Team ID**: `4HDNC3V5Q6`
- **Key ID**: `53LV856G76`
- **Services ID**: `com.laughtrack.webapp.service`
- **Private key path**: `~/Desktop/AuthKey_53LV856G76.p8`

Keep the `.p8` file somewhere safe — if it's lost, you'll need to revoke the key
in the Apple Developer Console and create a new one (then update Key ID here too).

## Steps

### 1. Generate the new JWT

Run this from the repo root:

```bash
python3 - <<'EOF'
import jwt, time

TEAM_ID = "4HDNC3V5Q6"
KEY_ID = "53LV856G76"
CLIENT_ID = "com.laughtrack.webapp.service"
PRIVATE_KEY_PATH = "/Users/mattgioe/Desktop/AuthKey_53LV856G76.p8"

with open(PRIVATE_KEY_PATH, "r") as f:
    private_key = f.read()

now = int(time.time())
payload = {
    "iss": TEAM_ID,
    "iat": now,
    "exp": now + (86400 * 180),  # 6 months
    "aud": "https://appleid.apple.com",
    "sub": CLIENT_ID,
}
token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": KEY_ID})
print(token)
EOF
```

If `PyJWT` is not installed: `python3 -m pip install PyJWT cryptography`

Capture the output — that is the new `AUTH_APPLE_SECRET`.

### 2. Update .env.local

Replace the `AUTH_APPLE_SECRET` line in `apps/web/.env.local` with the new token.

### 3. Update Vercel production

```bash
cd apps/web
vercel env rm AUTH_APPLE_SECRET production --yes
echo "<new_token>" | vercel env add AUTH_APPLE_SECRET production
```

### 4. Verify

```bash
cd apps/web && vercel env ls | grep APPLE
```

Both `AUTH_APPLE_ID` and `AUTH_APPLE_SECRET` should appear.

### 5. Update the expiry reminder

Edit this skill's header comment or create a task so you remember when to renew next
(180 days from today).

## If the .p8 file is lost

1. Go to [developer.apple.com](https://developer.apple.com) → Keys
2. Revoke key `53LV856G76`
3. Create a new key with Sign In with Apple enabled
4. Download the new `.p8` file and note the new Key ID
5. Update `KEY_ID` and `PRIVATE_KEY_PATH` in this skill
6. Regenerate from Step 1
