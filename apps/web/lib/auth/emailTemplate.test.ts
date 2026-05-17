import { describe, expect, it } from "vitest";
import { buildMagicLinkEmail } from "./emailTemplate";

describe("buildMagicLinkEmail", () => {
    it("renders branded magic-link copy with the original sign-in URL", () => {
        const url =
            "https://laughtrack.com/api/auth/callback/email?callbackUrl=https%3A%2F%2Flaughtrack.com%2Fshows&token=token-123&email=user%40example.com";

        const email = buildMagicLinkEmail({ url });

        expect(email.subject).toBe("Sign in to LaughTrack");
        expect(email.html).toContain("LaughTrack");
        expect(email.html).toContain("See what&apos;s on next");
        expect(email.html).toContain(
            'href="' + url.replaceAll("&", "&amp;") + '"',
        );
        expect(email.html).toContain("laughtrack.com");
        expect(email.html).toContain("If the button does not work");
        expect(email.text).toContain("Sign in to LaughTrack");
        expect(email.text).toContain(url);
        expect(email.text).toContain("If you did not request this email");
    });
});
