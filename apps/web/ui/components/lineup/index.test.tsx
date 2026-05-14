/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LineupGrid from "./index";

vi.mock("@/objects/class/comedian/Comedian", () => ({
    Comedian: class {},
}));

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
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: false,
    }),
}));

afterEach(() => {
    cleanup();
});

const makeComedian = (overrides: Record<string, unknown> = {}) =>
    ({
        id: 1,
        uuid: "comedian-1",
        name: "Jordan Temple",
        imageUrl: "",
        hasImage: false,
        ...overrides,
    }) as never;

describe("LineupGrid", () => {
    it("renders an explicit role badge below the comedian name", () => {
        render(<LineupGrid lineup={[makeComedian({ role: "Headliner" })]} />);

        expect(screen.getByText("Headliner")).not.toBeNull();
    });

    it("does not render a role badge when role is absent", () => {
        render(<LineupGrid lineup={[makeComedian()]} />);

        expect(screen.queryByText("Headliner")).toBeNull();
    });
});
