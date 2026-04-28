/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import PopularClubCard from "./index";

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

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
    }),
}));

describe("PopularClubCard", () => {
    it("renders a branded fallback instead of the gray placeholder image", () => {
        const { container } = render(
            <PopularClubCard
                entity={{
                    id: 12,
                    name: "No Photo Comedy Club",
                    zipCode: "10001",
                    imageUrl: "/placeholders/club-placeholder.svg",
                    active_comedian_count: 4,
                }}
            />,
        );

        expect(
            container.querySelector(
                'img[src="/placeholders/club-placeholder.svg"]',
            ),
        ).toBeNull();
        expect(
            container.querySelector('[data-testid="club-image-fallback"]'),
        ).not.toBeNull();
    });
});
