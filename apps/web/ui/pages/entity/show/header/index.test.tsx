/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowDetailHeader from "./index";
import type { ShowDetailDTO } from "@/lib/data/show/detail/interface";

vi.mock("next/link", () => ({
    default: ({
        children,
        href,
        className,
    }: {
        children: React.ReactNode;
        href: string;
        className?: string;
    }) => (
        <a href={href} className={className}>
            {children}
        </a>
    ),
}));

vi.mock("next/image", () => ({
    default: ({
        alt,
        src,
        className,
    }: {
        alt: string;
        src: string;
        className?: string;
    }) => <img alt={alt} src={src} className={className} />,
}));

vi.mock("framer-motion", () => ({
    motion: {
        div: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <div className={className}>{children}</div>,
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mt: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

const baseShow: ShowDetailDTO = {
    id: 42,
    clubId: 24,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room-wide.jpg",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
    showPageUrl: "https://example.com/show",
};

afterEach(() => {
    cleanup();
});

describe("ShowDetailHeader", () => {
    it("renders the venue eyebrow as an uppercase copper link to the club page", () => {
        render(<ShowDetailHeader show={baseShow} />);

        const eyebrow = screen.getByRole("link", {
            name: "The Copper Room",
        });
        expect(eyebrow.getAttribute("href")).toBe("/club/The Copper Room");
        expect(eyebrow.className).toContain("uppercase");
        expect(eyebrow.className).toContain("text-accent-strong");
    });

    it("renders the title uppercase", () => {
        render(<ShowDetailHeader show={baseShow} />);

        const title = screen.getByRole("heading", { level: 1 });
        expect(title.textContent).toBe("Late Show");
        expect(title.className).toContain("uppercase");
    });

    it("frames the poster with a dashed copper ring and fills the square crop", () => {
        render(<ShowDetailHeader show={baseShow} />);

        const frame = screen.getByTestId("marquee-poster-frame");
        expect(frame.className).toContain("border-dashed");
        expect(frame.className).toContain("border-accent-strong");

        // Square poster crops like the iOS scaledToFill poster — the old
        // wide-banner object-contain treatment no longer applies.
        const image = screen.getByAltText("The Copper Room");
        expect(image.className).toContain("object-cover");
    });

    it("renders the ticket-icon fallback inside the ring when the image is the placeholder", () => {
        render(
            <ShowDetailHeader
                show={{
                    ...baseShow,
                    imageUrl: "/placeholders/club-placeholder.svg",
                }}
            />,
        );

        expect(screen.getByTestId("marquee-poster-fallback")).toBeTruthy();
        expect(screen.queryByAltText("The Copper Room")).toBeNull();
    });

    it("falls back to a venue heading when the show has no name", () => {
        render(<ShowDetailHeader show={{ ...baseShow, name: "" }} />);

        const title = screen.getByRole("heading", { level: 1 });
        expect(title.textContent).toBe("Comedy at The Copper Room");
    });

    it("still renders the countdown badge", () => {
        render(<ShowDetailHeader show={baseShow} />);

        // The base show date is in the past relative to the test run.
        expect(screen.getByText(/^Ended .* ago$/)).toBeTruthy();
    });

    it("maps countdown tones to the iOS badge recipes: live → accent, future → highlight, past → neutral", () => {
        const { unmount: unmountLive } = render(
            <ShowDetailHeader
                show={{
                    ...baseShow,
                    // 10 minutes ago — inside the live window.
                    date: new Date(
                        Date.now() - 10 * 60 * 1000,
                    ).toISOString() as never as Date,
                }}
            />,
        );
        const liveBadge = screen.getByText("Happening now");
        expect(liveBadge.className).toContain("bg-accent-muted/45");
        expect(liveBadge.className).toContain("text-accent-strong");
        expect(liveBadge.className).toContain("border-accent-strong/35");
        expect(liveBadge.className).not.toContain("emerald");
        expect(liveBadge.className).not.toContain("text-white");
        unmountLive();

        const { unmount: unmountFuture } = render(
            <ShowDetailHeader
                show={{
                    ...baseShow,
                    date: new Date(
                        Date.now() + 24 * 60 * 60 * 1000,
                    ).toISOString() as never as Date,
                }}
            />,
        );
        const futureBadge = screen.getByText(/^Show in /);
        expect(futureBadge.className).toContain("bg-highlight/85");
        expect(futureBadge.className).toContain("text-foreground");
        expect(futureBadge.className).toContain("border-strong/50");
        unmountFuture();

        render(<ShowDetailHeader show={baseShow} />);
        const pastBadge = screen.getByText(/^Ended .* ago$/);
        expect(pastBadge.className).toContain("bg-canvas");
        expect(pastBadge.className).toContain("text-foreground");
        expect(pastBadge.className).toContain("border-subtle");
    });
});
