import { describe, expect, it } from "vitest";
import { buildMagicLinkEmail, buildWelcomeEmail } from "./emailTemplate";

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

describe("buildWelcomeEmail", () => {
    it("renders branded verification-aware welcome copy with key app links", () => {
        const email = buildWelcomeEmail({ baseUrl: "https://laughtrack.com" });

        expect(email.subject).toBe("Welcome to LaughTrack");
        expect(email.html).toContain("LaughTrack");
        expect(email.html).toContain("logomark-192.png");
        expect(email.html).toContain("Your email is verified");
        expect(email.html).toContain("Find live comedy near you");
        expect(email.html).toContain(
            'href="https://laughtrack.com/show/search"',
        );
        expect(email.html).toContain(
            'href="https://laughtrack.com/comedian/search"',
        );
        expect(email.html).toContain(
            'href="https://laughtrack.com/club/search"',
        );
        expect(email.html).toContain('href="https://laughtrack.com/profile"');
        expect(email.text).toContain("Your email is verified");
        expect(email.text).toContain("https://laughtrack.com/show/search");
        expect(email.text).toContain("https://laughtrack.com/profile");
    });

    it("escapes the base URL before rendering links", () => {
        const email = buildWelcomeEmail({
            baseUrl: "https://laughtrack.com?x=<script>",
        });

        expect(email.html).toContain(
            'href="https://laughtrack.com/show/search"',
        );
        expect(email.html).not.toContain("<script>");
    });
});
