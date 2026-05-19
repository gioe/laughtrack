/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, waitFor } from "@testing-library/react";
import GlobalSearchClient from "./index";

vi.mock("@/ui/components/cards/entity", () => ({
    default: ({
        children,
        ariaLabel,
    }: {
        children: React.ReactNode;
        ariaLabel?: string;
    }) => <article aria-label={ariaLabel}>{children}</article>,
}));

const fetchMock = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockResolvedValue({
        ok: true,
        json: () =>
            Promise.resolve({
                data: [
                    {
                        id: "podcast-10",
                        entityType: "podcast",
                        title: "Good One",
                        subtitle: "Vulture",
                        href: "https://www.vulture.com/good-one",
                        imageUrl: "https://cdn.example.com/good-one.jpg",
                    },
                ],
                total: 1,
                totals: {
                    all: 1,
                    show: 0,
                    comedian: 0,
                    club: 0,
                    podcast: 1,
                },
            }),
    });
    vi.stubGlobal("fetch", fetchMock);
});

describe("GlobalSearchClient", () => {
    it("filters search results to podcasts and renders podcast row chrome", async () => {
        const { getByLabelText, getByRole, getByText } = render(
            <GlobalSearchClient />,
        );

        fireEvent.change(getByLabelText("Search LaughTrack"), {
            target: { value: "good" },
        });
        fireEvent.click(getByRole("button", { name: "Podcasts" }));

        await waitFor(() =>
            expect(fetchMock).toHaveBeenLastCalledWith(
                "/api/v1/search?q=good&type=podcast&limit=20",
                expect.any(Object),
            ),
        );

        expect(getByText("Good One")).not.toBeNull();
        expect(getByText("Vulture")).not.toBeNull();
        expect(
            getByRole("article", { name: "Good One podcast" }),
        ).not.toBeNull();
    });
});
