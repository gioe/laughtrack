import { randomBytes, scryptSync } from "node:crypto";
import { describe, expect, it } from "vitest";
import { verifyReviewPassword } from "./reviewCredentials";

function hash(password: string): string {
    const salt = randomBytes(16);
    const key = scryptSync(password, salt, 64);
    return `scrypt$${salt.toString("hex")}$${key.toString("hex")}`;
}

describe("verifyReviewPassword", () => {
    it("accepts the matching password", () => {
        expect(
            verifyReviewPassword("review-secret", hash("review-secret")),
        ).toBe(true);
    });

    it("rejects a wrong password and malformed hashes", () => {
        const encoded = hash("review-secret");
        expect(verifyReviewPassword("wrong", encoded)).toBe(false);
        expect(verifyReviewPassword("review-secret", "not-a-hash")).toBe(false);
    });

    it("rejects empty and oversized passwords", () => {
        const encoded = hash("review-secret");
        expect(verifyReviewPassword("", encoded)).toBe(false);
        expect(verifyReviewPassword("x".repeat(257), encoded)).toBe(false);
    });
});
