import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    notFound: vi.fn(() => {
        throw new Error("NEXT_NOT_FOUND");
    }),
    readFile: vi.fn(),
    readdir: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    notFound: mocks.notFound,
}));

vi.mock("node:fs/promises", () => ({
    readFile: mocks.readFile,
    readdir: mocks.readdir,
}));

import AppStoreStoryboardPage from "./page";

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("VERCEL_ENV", undefined);
    mocks.readFile.mockResolvedValue("Fixture metadata");
    mocks.readdir.mockResolvedValue(["iPhone-01-home.png"]);
});

afterEach(() => {
    vi.unstubAllEnvs();
});

describe("AppStoreStoryboardPage", () => {
    it.each([
        ["plain local development", undefined],
        ["Vercel CLI development", "development"],
    ])("loads in %s", async (_label, vercelEnvironment) => {
        vi.stubEnv("VERCEL_ENV", vercelEnvironment);

        const page = await AppStoreStoryboardPage();

        expect(page.type).toBe("main");
        expect(mocks.notFound).not.toHaveBeenCalled();
        expect(mocks.readdir).toHaveBeenCalledOnce();
        expect(mocks.readFile).toHaveBeenCalled();
    });

    it.each([
        ["Vercel preview", "production", "preview"],
        ["Vercel preview with development mode", "development", "preview"],
        ["Vercel production", "production", "production"],
        ["standalone production", "production", undefined],
        ["an unknown runtime", undefined, undefined],
        ["an unknown Vercel environment", "development", "staging"],
    ])(
        "returns 404 in %s",
        async (_label, nodeEnvironment, vercelEnvironment) => {
            vi.stubEnv("NODE_ENV", nodeEnvironment);
            vi.stubEnv("VERCEL_ENV", vercelEnvironment);

            await expect(AppStoreStoryboardPage()).rejects.toThrow(
                "NEXT_NOT_FOUND",
            );

            expect(mocks.notFound).toHaveBeenCalledOnce();
            expect(mocks.readdir).not.toHaveBeenCalled();
            expect(mocks.readFile).not.toHaveBeenCalled();
        },
    );
});
