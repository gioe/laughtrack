import { scryptSync, timingSafeEqual } from "node:crypto";

const HASH_PATTERN = /^scrypt\$([0-9a-f]{32})\$([0-9a-f]{128})$/i;
const MAX_PASSWORD_LENGTH = 256;

/**
 * Verify a store-review password against a `scrypt$<salt-hex>$<key-hex>` value.
 * The plaintext credential lives only in App Store Connect / Play Console and
 * is never stored in the database or deployment environment.
 */
export function verifyReviewPassword(
    password: string,
    encodedHash: string,
): boolean {
    if (!password || password.length > MAX_PASSWORD_LENGTH) return false;

    const match = HASH_PATTERN.exec(encodedHash);
    if (!match) return false;

    const salt = Buffer.from(match[1], "hex");
    const expected = Buffer.from(match[2], "hex");
    const actual = scryptSync(password, salt, expected.length);

    return timingSafeEqual(actual, expected);
}
