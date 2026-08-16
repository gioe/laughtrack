import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    readFile: vi.fn(),
    readdir: vi.fn(),
}));

vi.mock("node:fs/promises", () => ({
    readFile: mocks.readFile,
    readdir: mocks.readdir,
}));

import { GET } from "./[filename]/route";

const ALLOWED_SCREENSHOT = "iPhone-01-home.png";
const IMAGE_BYTES = new Uint8Array([137, 80, 78, 71]);

function getScreenshot(filename: string) {
    return GET(
        new Request(
            `http://localhost/app-store-storyboard/screenshot/${encodeURIComponent(filename)}`,
        ),
        { params: Promise.resolve({ filename }) },
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("VERCEL_ENV", undefined);
    mocks.readdir.mockResolvedValue([ALLOWED_SCREENSHOT, "notes.txt"]);
    mocks.readFile.mockResolvedValue(IMAGE_BYTES);
});

afterEach(() => {
    vi.unstubAllEnvs();
});

describe("GET /app-store-storyboard/screenshot/[filename]", () => {
    it("serves an allowlisted PNG in local development", async () => {
        const response = await getScreenshot(ALLOWED_SCREENSHOT);

        expect(response.status).toBe(200);
        expect(response.headers.get("Cache-Control")).toBe("no-store");
        expect(response.headers.get("Content-Type")).toBe("image/png");
        expect(response.headers.get("Content-Disposition")).toBe(
            `inline; filename*=UTF-8''${ALLOWED_SCREENSHOT}`,
        );
        expect(new Uint8Array(await response.arrayBuffer())).toEqual(
            IMAGE_BYTES,
        );
        expect(mocks.readFile).toHaveBeenCalledOnce();
        expect(mocks.readFile).toHaveBeenCalledWith(
            expect.stringMatching(
                new RegExp(`/screenshots/en-US/${ALLOWED_SCREENSHOT}$`),
            ),
        );
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

            const response = await getScreenshot(ALLOWED_SCREENSHOT);

            expect(response.status).toBe(404);
            expect(mocks.readdir).not.toHaveBeenCalled();
            expect(mocks.readFile).not.toHaveBeenCalled();
        },
    );

    it.each([
        ["a PNG absent from the directory", "iPhone-99-missing.png"],
        ["a non-PNG file", "notes.txt"],
        ["a traversal path", "../iPhone-01-home.png"],
    ])("returns 404 for %s", async (_label, filename) => {
        const response = await getScreenshot(filename);

        expect(response.status).toBe(404);
        expect(mocks.readFile).not.toHaveBeenCalled();
    });
});
