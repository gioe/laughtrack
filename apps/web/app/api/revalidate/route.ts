import { auth } from "@/auth";
import { timingSafeEqual } from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

const SUPPORTED_TAGS = [
    "home-page-data",
    "club-detail-data",
    "comedian-detail-data",
    "show-detail-data",
    "show-metadata",
    "club-search-data",
    "show-search-data",
] as const;

type SupportedTag = (typeof SUPPORTED_TAGS)[number];

export async function POST(req: NextRequest) {
    // Auth: admin session OR Bearer token
    const authHeader = req.headers.get("authorization");
    const bearerToken = authHeader?.startsWith("Bearer ")
        ? authHeader.slice(7)
        : null;

    const revalidateSecret = process.env.REVALIDATE_SECRET;
    let hasValidBearer = false;
    if (bearerToken && revalidateSecret) {
        // Compare byte lengths, not JS string lengths — multi-byte UTF-8 chars
        // can encode to different byte counts at equal code-unit lengths, which
        // would crash timingSafeEqual with a RangeError.
        const bearerBuf = Buffer.from(bearerToken);
        const secretBuf = Buffer.from(revalidateSecret);
        if (bearerBuf.length === secretBuf.length) {
            hasValidBearer = timingSafeEqual(bearerBuf, secretBuf);
        }
    }

    if (!hasValidBearer) {
        const session = await auth();
        const isAdmin = session?.profile?.role === "admin";
        if (!isAdmin) {
            return NextResponse.json(
                { error: "Unauthorized" },
                { status: 401 },
            );
        }
    }

    let tags: SupportedTag[];
    try {
        const body = await req.json().catch(() => ({}));
        if (body.tags !== undefined) {
            if (!Array.isArray(body.tags)) {
                return NextResponse.json(
                    { error: "tags must be an array" },
                    { status: 400 },
                );
            }
            const unknown = body.tags.filter(
                (t: unknown) => !SUPPORTED_TAGS.includes(t as SupportedTag),
            );
            if (unknown.length > 0) {
                return NextResponse.json(
                    { error: `Unknown tags: ${unknown.join(", ")}` },
                    { status: 400 },
                );
            }
            tags = body.tags as SupportedTag[];
        } else {
            tags = [...SUPPORTED_TAGS];
        }
    } catch {
        tags = [...SUPPORTED_TAGS];
    }

    for (const tag of tags) {
        revalidateTag(tag);
    }

    return NextResponse.json({ revalidated: tags });
}
