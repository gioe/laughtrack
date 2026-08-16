import path from "node:path";
import { readdir, readFile } from "node:fs/promises";
import { isLocalDevelopment } from "../../access";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const SCREENSHOT_ROOT = path.resolve(
    process.cwd(),
    "../../ios/fastlane/screenshots/en-US",
);

export async function GET(
    _request: Request,
    { params }: { params: Promise<{ filename: string }> },
) {
    if (!isLocalDevelopment()) {
        return new Response("Not found", { status: 404 });
    }

    const { filename } = await params;
    const availableScreenshots = await readdir(SCREENSHOT_ROOT);
    if (
        filename !== path.basename(filename) ||
        !filename.endsWith(".png") ||
        !availableScreenshots.includes(filename)
    ) {
        return new Response("Not found", { status: 404 });
    }

    const image = await readFile(path.join(SCREENSHOT_ROOT, filename));
    return new Response(image, {
        headers: {
            "Cache-Control": "no-store",
            "Content-Disposition": `inline; filename*=UTF-8''${encodeURIComponent(filename)}`,
            "Content-Type": "image/png",
        },
    });
}
