import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getYouTubeWebSubSettings: vi.fn(),
}));

vi.mock("@/lib/admin/youtubeWebSub", () => ({
    getYouTubeWebSubSettings: mocks.getYouTubeWebSubSettings,
}));

import AdminFeatureFlagsPage from "./page";

beforeEach(() => {
    vi.clearAllMocks();
    mocks.getYouTubeWebSubSettings.mockResolvedValue({
        feedIngestionEnabled: false,
        pushDeliveryEnabled: true,
    });
});

describe("AdminFeatureFlagsPage", () => {
    it("renders the feature flags admin page", async () => {
        const element = await AdminFeatureFlagsPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Feature Flags");
        expect(markup).toContain("Feature flags");
        expect(markup).toContain("Feed ingestion enabled");
        expect(markup).toContain("Push delivery enabled");
    });
});
