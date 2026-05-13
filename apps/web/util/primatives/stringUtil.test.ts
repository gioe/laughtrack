import { describe, it, expect } from "vitest";
import { stripHtmlTags } from "./stringUtil";

describe("stripHtmlTags", () => {
    it("converts closing block tags to a paragraph break", () => {
        expect(
            stripHtmlTags("<p>First paragraph.</p><p>Second paragraph.</p>"),
        ).toBe("First paragraph.\n\nSecond paragraph.");
    });

    it("converts <br> variants to a single newline", () => {
        expect(stripHtmlTags("Line one<br>Line two<br/>Line three")).toBe(
            "Line one\nLine two\nLine three",
        );
    });

    it("renders <li> entries as bulleted lines", () => {
        expect(
            stripHtmlTags("<ul><li>First</li><li>Second</li></ul>"),
        ).toBe("• First\n\n• Second");
    });

    it("decodes named HTML entities", () => {
        expect(stripHtmlTags("Tom &amp; Jerry &mdash; together")).toBe(
            "Tom & Jerry — together",
        );
    });

    it("decodes numeric and hex entities", () => {
        expect(stripHtmlTags("It&#39;s &#x27;quoted&#x27;")).toBe(
            "It's 'quoted'",
        );
    });

    it("strips <strong> and other inline tags but keeps the inner text", () => {
        expect(
            stripHtmlTags("<p><strong>Patton Oswalt</strong> is great.</p>"),
        ).toBe("Patton Oswalt is great.");
    });

    it("collapses runs of three or more newlines back to a single break", () => {
        expect(stripHtmlTags("<p>One.</p><p></p><p>Two.</p>")).toBe(
            "One.\n\nTwo.",
        );
    });
});
