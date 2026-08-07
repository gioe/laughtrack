/**
 * @vitest-environment happy-dom
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    DISCOVERY_RAIL_CATALOG,
    DISCOVERY_RAIL_CATALOG_VERSION,
    getDefaultDiscoveryRailPolicy,
} from "@/lib/discovery/railPolicy";
import AdminDiscoveryRailsPage from "./page";

function apiResponse() {
    return {
        catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
        catalog: Object.values(DISCOVERY_RAIL_CATALOG).map((entry) => ({
            ...entry,
            supportedPlatforms: [...entry.supportedPlatforms],
            catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
        })),
        platforms: [
            {
                ...getDefaultDiscoveryRailPolicy("web"),
                provenance: "stored",
                updatedAt: "2026-08-07T14:30:00.000Z",
                updatedBy: {
                    profileId: "profile-admin",
                    name: "Rail Operator",
                    email: "operator@example.com",
                },
            },
            {
                ...getDefaultDiscoveryRailPolicy("ios"),
                provenance: "built_in_default",
                updatedAt: null,
                updatedBy: null,
            },
            {
                ...getDefaultDiscoveryRailPolicy("android"),
                provenance: "built_in_default",
                updatedAt: null,
                updatedBy: null,
            },
        ],
    };
}

beforeEach(() => {
    vi.stubGlobal(
        "fetch",
        vi.fn(
            async () =>
                new Response(JSON.stringify(apiResponse()), { status: 200 }),
        ),
    );
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("AdminDiscoveryRailsPage", () => {
    it("displays effective policy metadata for web, iOS, and Android", async () => {
        render(<AdminDiscoveryRailsPage />);

        expect(
            screen.getByRole("heading", { name: "Discover rail policies" }),
        ).toBeTruthy();

        await waitFor(() => {
            expect(
                screen.getByRole("button", { name: /Web.*Version 2/i }),
            ).toBeTruthy();
            expect(
                screen.getByRole("button", { name: /iOS.*Version 2/i }),
            ).toBeTruthy();
            expect(
                screen.getByRole("button", { name: /Android.*Version 2/i }),
            ).toBeTruthy();
        });

        expect(screen.getByText("Stored admin policy")).toBeTruthy();
        expect(screen.getAllByText("Built-in default policy")).toHaveLength(2);
        expect(screen.getByText(/Updated .* by Rail Operator/)).toBeTruthy();
        expect(screen.getAllByText(/24-hour cadence/)).toHaveLength(3);
    });
});
