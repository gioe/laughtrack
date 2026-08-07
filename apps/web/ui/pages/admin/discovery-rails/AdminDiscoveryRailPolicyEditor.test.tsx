/**
 * @vitest-environment happy-dom
 */

import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AdminDiscoveryRailPolicyEditor from "./AdminDiscoveryRailPolicyEditor";

const catalog = [
    {
        key: "shows_tonight",
        label: "Shows tonight",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ["web", "ios", "android"],
        catalogVersion: 2,
    },
    {
        key: "trending_this_week",
        label: "Trending this week",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ["web", "ios", "android"],
        catalogVersion: 2,
    },
    {
        key: "trending_comedians",
        label: "Trending comedians",
        contentKind: "comedian",
        requiresAuth: false,
        supportedPlatforms: ["web", "ios", "android"],
        catalogVersion: 2,
    },
    {
        key: "popular_clubs",
        label: "Popular clubs",
        contentKind: "club",
        requiresAuth: false,
        supportedPlatforms: ["web", "ios", "android"],
        catalogVersion: 2,
    },
] as const;

function rails() {
    return [
        {
            railKey: "shows_tonight",
            enabled: true,
            position: 0,
            rotationPool: null,
            weight: 1,
        },
        {
            railKey: "trending_this_week",
            enabled: true,
            position: 1,
            rotationPool: null,
            weight: 1,
        },
        {
            railKey: "trending_comedians",
            enabled: true,
            position: 2,
            rotationPool: "weekly_mix",
            weight: 3,
        },
        {
            railKey: "popular_clubs",
            enabled: true,
            position: 2,
            rotationPool: "weekly_mix",
            weight: 1,
        },
    ];
}

function policyResponse(webVersion = 7) {
    return {
        catalogVersion: 2,
        catalog,
        platforms: [
            {
                platform: "web",
                catalogVersion: 2,
                version: webVersion,
                cycleCadenceHours: 24,
                rails: rails(),
                provenance: "stored",
                updatedAt: "2026-08-07T14:30:00.000Z",
                updatedBy: {
                    profileId: "profile-1",
                    name: "Matt Admin",
                    email: "matt@example.com",
                },
            },
            {
                platform: "ios",
                catalogVersion: 2,
                version: 4,
                cycleCadenceHours: 12,
                rails: rails(),
                provenance: "built_in_default",
                updatedAt: null,
                updatedBy: null,
            },
            {
                platform: "android",
                catalogVersion: 2,
                version: 5,
                cycleCadenceHours: 6,
                rails: rails(),
                provenance: "stored",
                updatedAt: "2026-08-06T09:00:00.000Z",
                updatedBy: {
                    profileId: "profile-2",
                    name: null,
                    email: "ops@example.com",
                },
            },
        ],
    };
}

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

async function renderLoadedEditor() {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse(policyResponse()));
    render(<AdminDiscoveryRailPolicyEditor />);
    await screen.findByRole("heading", { name: "Web policy settings" });
    return fetchMock;
}

beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("AdminDiscoveryRailPolicyEditor", () => {
    it("loads and displays effective policy metadata for every platform", async () => {
        await renderLoadedEditor();

        expect(
            screen
                .getByRole("button", { name: /^Web Version/ })
                .getAttribute("aria-pressed"),
        ).toBe("true");
        expect(
            screen.getByRole("button", { name: /iOS/ }).textContent,
        ).toContain("Version 4 · 12-hour cadence");
        expect(
            screen.getByRole("button", { name: /Android/ }).textContent,
        ).toContain("Version 5 · 6-hour cadence");
        expect(screen.getAllByText("Stored admin policy")).toHaveLength(2);
        expect(screen.getByText("Built-in default policy")).toBeTruthy();
        expect(screen.getByText(/Matt Admin/)).toBeTruthy();
        expect(screen.getByText(/ops@example.com/)).toBeTruthy();
        expect(
            screen.getByText(
                "No admin update recorded; using the built-in policy.",
            ),
        ).toBeTruthy();

        fireEvent.click(screen.getByRole("button", { name: /iOS/ }));
        expect(
            screen.getByRole("heading", { name: "iOS policy settings" }),
        ).toBeTruthy();
        expect(
            (
                screen.getByLabelText(
                    "Rotation cadence (hours)",
                ) as HTMLInputElement
            ).value,
        ).toBe("12");
    });

    it("edits accessible controls and PATCHes a normalized policy", async () => {
        const fetchMock = await renderLoadedEditor();

        fireEvent.click(screen.getByLabelText("Enable Trending this week"));
        fireEvent.click(
            screen.getByRole("button", {
                name: "Move Shows tonight down",
            }),
        );
        fireEvent.click(
            screen.getByRole("button", { name: "Pin Trending comedians" }),
        );
        fireEvent.change(
            screen.getByLabelText("Rotation group for Trending comedians"),
            { target: { value: "lead" } },
        );
        fireEvent.change(
            screen.getByLabelText("Weight for Trending comedians"),
            {
                target: { value: "5" },
            },
        );
        fireEvent.change(screen.getByLabelText("Rotation cadence (hours)"), {
            target: { value: "12" },
        });

        fetchMock
            .mockResolvedValueOnce(
                jsonResponse({
                    ok: true,
                    policy: {
                        ...policyResponse().platforms[0],
                        version: 8,
                    },
                }),
            )
            .mockResolvedValueOnce(jsonResponse(policyResponse(8)));

        fireEvent.click(
            screen.getByRole("button", { name: "Save Web policy" }),
        );

        await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
        expect(fetchMock.mock.calls[1][0]).toBe("/api/admin/discovery-rails");
        expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PATCH" });
        const body = JSON.parse(
            String(fetchMock.mock.calls[1][1]?.body ?? "{}"),
        );
        expect(body).toMatchObject({
            platform: "web",
            expectedVersion: 7,
            cycleCadenceHours: 12,
        });
        expect(body.rails).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    railKey: "trending_this_week",
                    enabled: false,
                }),
                expect.objectContaining({
                    railKey: "trending_comedians",
                    rotationPool: "lead",
                    weight: 5,
                }),
            ]),
        );
        expect(
            new Set(
                body.rails.map((rail: { position: number }) => rail.position),
            ),
        ).toEqual(new Set([0, 1, 2, 3]));
        expect(await screen.findByText("Web policy saved.")).toBeTruthy();
    });

    it("keeps the last valid preview and saved policy on preview and validation failures", async () => {
        const fetchMock = await renderLoadedEditor();

        expect(
            screen.getByRole("heading", { name: "Current cycle" }),
        ).toBeTruthy();
        expect(
            screen.getByRole("heading", { name: "Next cycle" }),
        ).toBeTruthy();

        fireEvent.click(screen.getByLabelText("Enable Trending comedians"));
        fireEvent.click(screen.getByLabelText("Enable Popular clubs"));

        expect(
            await screen.findByText(/must have at least one enabled rail/),
        ).toBeTruthy();
        expect(screen.getByText("Showing last valid preview")).toBeTruthy();
        expect(
            (
                screen.getByRole("button", {
                    name: "Save Web policy",
                }) as HTMLButtonElement
            ).disabled,
        ).toBe(true);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(
            screen.getByRole("button", { name: /^Web Version/ }).textContent,
        ).toContain("Version 7");

        fireEvent.click(
            screen.getByRole("button", { name: "Reset unsaved changes" }),
        );
        await waitFor(() =>
            expect(screen.queryByText("Showing last valid preview")).toBeNull(),
        );
        expect(
            (
                screen.getByLabelText(
                    "Enable Trending comedians",
                ) as HTMLInputElement
            ).checked,
        ).toBe(true);
        expect(
            (screen.getByLabelText("Enable Popular clubs") as HTMLInputElement)
                .checked,
        ).toBe(true);
    });

    it("gives conflict and network guidance without replacing saved state", async () => {
        const fetchMock = await renderLoadedEditor();
        const cadence = screen.getByLabelText("Rotation cadence (hours)");

        fireEvent.change(cadence, { target: { value: "18" } });
        fetchMock.mockResolvedValueOnce(
            jsonResponse(
                { error: "Discovery rail policy for web has changed" },
                409,
            ),
        );
        fireEvent.click(
            screen.getByRole("button", { name: "Save Web policy" }),
        );

        expect(
            await screen.findByText(
                /Reload policies to review the newer version/,
            ),
        ).toBeTruthy();
        expect(
            screen.getByRole("button", { name: /^Web Version/ }).textContent,
        ).toContain("Version 7");
        expect((cadence as HTMLInputElement).value).toBe("18");

        fireEvent.change(cadence, { target: { value: "20" } });
        fetchMock.mockRejectedValueOnce(new Error("Connection lost"));
        fireEvent.click(
            screen.getByRole("button", { name: "Save Web policy" }),
        );

        expect(
            await screen.findByText(
                /Your last saved policy is unchanged; retry or reload/,
            ),
        ).toBeTruthy();
        expect(
            screen.getByRole("button", { name: /^Web Version/ }).textContent,
        ).toContain("Version 7");
        expect((cadence as HTMLInputElement).value).toBe("20");
    });

    it("requires a reload when a saved policy cannot be refreshed", async () => {
        const fetchMock = await renderLoadedEditor();

        fireEvent.change(screen.getByLabelText("Rotation cadence (hours)"), {
            target: { value: "18" },
        });
        fetchMock
            .mockResolvedValueOnce(jsonResponse({ ok: true }))
            .mockRejectedValueOnce(new Error("Refresh unavailable"));

        fireEvent.click(
            screen.getByRole("button", { name: "Save Web policy" }),
        );

        expect(
            await screen.findByText(
                "The policy was saved, but its latest version could not be reloaded. Reload policies before making more changes.",
            ),
        ).toBeTruthy();
        expect(
            screen.getByRole("button", { name: /^Web Version/ }).textContent,
        ).toContain("Version 7");
        expect(
            (
                screen.getByRole("button", {
                    name: "Save Web policy",
                }) as HTMLButtonElement
            ).disabled,
        ).toBe(true);
    });
});
