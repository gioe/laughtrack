/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import type { ClubDTO } from "@/objects/class/club/club.interface";

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

vi.mock("framer-motion", () => {
    const passthrough =
        (Tag: keyof JSX.IntrinsicElements) =>
        ({
            children,
            className,
        }: {
            children?: React.ReactNode;
            className?: string;
        }) =>
            React.createElement(Tag, { className }, children);
    return {
        motion: {
            div: passthrough("div"),
            h1: passthrough("h1"),
            p: passthrough("p"),
            ul: passthrough("ul"),
        },
    };
});

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        mt: (transition: unknown) => transition,
        prefersReducedMotion: true,
    }),
}));

afterEach(() => {
    cleanup();
});

const club: ClubDTO = {
    id: 1,
    imageUrl: "",
    name: "Comedy Cellar",
    address: "117 MacDougal St",
    city: "New York",
    state: "NY",
    zipCode: "10012",
    description:
        "Legendary West Village club hosting nightly stand-up showcases.",
    clubType: "club",
};

describe("ClubDetailHero About description", () => {
    it("renders the club description paragraph inside the hero block", () => {
        render(<ClubDetailHeader club={club} />);

        expect(
            screen.getByText(
                "Legendary West Village club hosting nightly stand-up showcases.",
            ),
        ).toBeTruthy();
    });

    it("omits the description paragraph when the club has no description", () => {
        render(<ClubDetailHeader club={{ ...club, description: "" }} />);

        expect(
            screen.queryByText(
                "Legendary West Village club hosting nightly stand-up showcases.",
            ),
        ).toBeNull();
    });
});
