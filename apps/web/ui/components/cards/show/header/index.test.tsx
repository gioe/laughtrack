/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowCardHeader from "./index";
import { Show } from "@/objects/class/show/Show";
import type { ShowDTO } from "@/objects/class/show/show.interface";

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

const baseShow: ShowDTO = {
    id: 42,
    clubID: 24,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [],
    tickets: [
        {
            price: 24,
            purchaseUrl: "https://example.com/tickets",
            soldOut: false,
            type: "General admission",
        },
    ],
    timezone: "America/New_York",
};

afterEach(() => {
    cleanup();
});

describe("ShowCardHeader", () => {
    it("uses show name as the primary heading and club as secondary text", () => {
        render(<ShowCardHeader show={new Show(baseShow)} />);

        expect(
            screen.getByRole("heading", { level: 3, name: "Late Show" }),
        ).toBeTruthy();
        expect(screen.getByText("The Copper Room")).toBeTruthy();
    });

    it("shows available ticket price metadata", () => {
        render(<ShowCardHeader show={new Show(baseShow)} />);

        expect(screen.getAllByText("$24")).toHaveLength(1);
    });
});
