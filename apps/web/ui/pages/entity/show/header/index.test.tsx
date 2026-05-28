/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

describe("ShowDetailHeader", () => {
    it("contains club artwork so wide venue images are not cropped", () => {
        render(<ShowDetailHeader show={baseShow} />);

        const image = screen.getByAltText("The Copper Room");
        expect(image.className).toContain("object-contain");
        expect(image.className).not.toContain("object-cover");
    });
});
