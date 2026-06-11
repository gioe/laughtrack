/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
        onLoad,
        onError,
    }: {
        alt: string;
        src: string;
        className?: string;
        onLoad?: React.ReactEventHandler<HTMLImageElement>;
        onError?: React.ReactEventHandler<HTMLImageElement>;
    }) => (
        <img
            alt={alt}
            src={src}
            className={className}
            onLoad={onLoad}
            onError={onError}
        />
    ),
}));

// Simulates the image finishing its load with the given intrinsic size —
// happy-dom never fetches, so naturalWidth/naturalHeight must be stubbed
// before firing the load event the component's letterbox detection reads.
const fireLoadWithSize = (
    image: HTMLElement,
    naturalWidth: number,
    naturalHeight: number,
) => {
    Object.defineProperty(image, "naturalWidth", { value: naturalWidth });
    Object.defineProperty(image, "naturalHeight", { value: naturalHeight });
    fireEvent.load(image);
};

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

vi.mock("@/hooks", async () => {
    const { mockUseMotionProps } = await import("@/test/motionProps");
    return { useMotionProps: mockUseMotionProps };
});

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

        // Square poster crops like the iOS scaledToFill poster by default
        // (before load, and for anything below the wordmark threshold).
        const image = screen.getByAltText("The Copper Room");
        expect(image.className).toContain("object-cover");
    });

    it("keeps the cover crop for venue photos below the 2:1 wordmark threshold", () => {
        render(<ShowDetailHeader show={baseShow} />);

        // 500x281 — the 16:9 venue-photo shape (e.g. Cobb's at 1.78:1).
        const image = screen.getByAltText("The Copper Room");
        fireLoadWithSize(image, 500, 281);

        expect(image.className).toContain("object-cover");
        expect(image.className).not.toContain("object-contain");
        expect(image.parentElement?.className).not.toContain(
            "bg-surface-muted",
        );
    });

    it("letterboxes exactly-2:1 images — the threshold is inclusive", () => {
        render(<ShowDetailHeader show={baseShow} />);

        // 250x125 — the BABS Comedy Club shape from the TASK-2787 survey;
        // pins the >= comparison so a regression to > can't slip through.
        const image = screen.getByAltText("The Copper Room");
        fireLoadWithSize(image, 250, 125);

        expect(image.className).toContain("object-contain");
        expect(image.parentElement?.className).toContain("bg-surface-muted");
    });

    it("letterboxes wide wordmark logos at or beyond 2:1 on surface-muted", () => {
        render(<ShowDetailHeader show={baseShow} />);

        // 475x125 — Goodnights' 3.8:1 wordmark, the TASK-2787 repro.
        const image = screen.getByAltText("The Copper Room");
        fireLoadWithSize(image, 475, 125);

        expect(image.className).toContain("object-contain");
        expect(image.className).not.toContain("object-cover");
        // Letterbox gutters get the muted backing inside the unchanged ring.
        expect(image.parentElement?.className).toContain("bg-surface-muted");
        expect(
            screen.getByTestId("marquee-poster-frame").className,
        ).toContain("border-dashed");
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

    it("hides the show ID for non-admin viewers", () => {
        render(<ShowDetailHeader show={baseShow} />);
        expect(screen.queryByTestId("show-detail-admin-id")).toBeNull();
    });

    it("renders the show ID for admin viewers", () => {
        render(<ShowDetailHeader show={baseShow} isAdmin />);
        const badge = screen.getByTestId("show-detail-admin-id");
        expect(badge.textContent).toBe("Show ID: 42");
    });
});
