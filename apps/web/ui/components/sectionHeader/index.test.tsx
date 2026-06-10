/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SectionHeader from "@/ui/components/sectionHeader";

vi.mock("next/link", () => ({
    default: ({
        children,
        href,
        className,
        ...props
    }: {
        children: React.ReactNode;
        href: string;
        className?: string;
    }) => (
        <a href={href} className={className} {...props}>
            {children}
        </a>
    ),
}));

afterEach(() => {
    cleanup();
});

describe("SectionHeader eyebrow", () => {
    it("renders the eyebrow with copper uppercase tracking-widest styling when provided", () => {
        render(<SectionHeader eyebrow="This week" title="Best shows" />);

        const eyebrow = screen.getByText("This week");
        expect(eyebrow.tagName).toBe("SPAN");
        expect(eyebrow.className).toContain("uppercase");
        expect(eyebrow.className).toContain("tracking-widest");
        expect(eyebrow.className).toContain("text-copper");
    });

    it("renders no eyebrow span when the prop is omitted", () => {
        const { container } = render(<SectionHeader title="Best shows" />);

        expect(screen.queryByText("This week")).toBeNull();
        expect(container.querySelector("span")).toBeNull();
    });
});

describe("SectionHeader titleId", () => {
    it("forwards titleId to the h2 so aria-labelledby resolves on a wrapping section", () => {
        const { container } = render(
            <section aria-labelledby="shows-tonight-heading">
                <SectionHeader
                    titleId="shows-tonight-heading"
                    title="Shows tonight"
                />
            </section>,
        );

        const heading = screen.getByRole("heading", {
            level: 2,
            name: "Shows tonight",
        });
        expect(heading.id).toBe("shows-tonight-heading");

        const section = container.querySelector("section");
        expect(section?.getAttribute("aria-labelledby")).toBe(heading.id);
        // The id the section points at must resolve to the rendered heading
        expect(
            container.querySelector("#shows-tonight-heading"),
        ).toBe(heading);
    });

    it("renders the h2 without an id when titleId is omitted", () => {
        render(<SectionHeader title="Shows tonight" />);

        const heading = screen.getByRole("heading", {
            level: 2,
            name: "Shows tonight",
        });
        expect(heading.hasAttribute("id")).toBe(false);
    });
});

describe("SectionHeader action link", () => {
    it("renders the action Link when both actionHref and actionLabel are provided", () => {
        render(
            <SectionHeader
                title="Shows tonight"
                actionHref="/show/search"
                actionLabel="See more"
            />,
        );

        const link = screen.getByRole("link", { name: /see more/i });
        expect(link.getAttribute("href")).toBe("/show/search");
    });

    it("renders no link when only actionHref is provided", () => {
        render(
            <SectionHeader title="Shows tonight" actionHref="/show/search" />,
        );

        expect(screen.queryByRole("link")).toBeNull();
    });

    it("renders no link when only actionLabel is provided", () => {
        render(<SectionHeader title="Shows tonight" actionLabel="See more" />);

        expect(screen.queryByRole("link")).toBeNull();
    });
});

describe("SectionHeader subtitle", () => {
    it("renders the subtitle paragraph when provided", () => {
        render(
            <SectionHeader
                title="Shows tonight"
                subtitle="Stand-up near you"
            />,
        );

        const subtitle = screen.getByText("Stand-up near you");
        expect(subtitle.tagName).toBe("P");
    });

    it("renders no paragraph when subtitle is omitted", () => {
        const { container } = render(<SectionHeader title="Shows tonight" />);

        expect(container.querySelector("p")).toBeNull();
    });
});
