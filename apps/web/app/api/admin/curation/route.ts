import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { curation } from "@/lib/admin/curation/runtime";
import { CurationError, commandSchema } from "@/lib/admin/curation/decisions";
const submission = z
    .object({
        operation: z.enum(["preview", "submit"]),
        command: commandSchema,
    })
    .strict();
function failure(error: unknown) {
    if (error instanceof z.ZodError)
        return NextResponse.json(
            { error: "Invalid curation request." },
            { status: 400 },
        );
    if (error instanceof CurationError)
        return NextResponse.json(
            { error: error.message, code: error.code, current: error.current },
            { status: error.status },
        );
    console.error("Curation request failed", error);
    return NextResponse.json(
        {
            error: "Unable to complete this request. Check request status before retrying.",
        },
        { status: 500 },
    );
}
export async function GET(req: NextRequest) {
    const auth = await requireAdminForApi();
    if (!auth.ok) return auth.response;
    try {
        return NextResponse.json(
            await curation.getRequest(
                z
                    .string()
                    .uuid()
                    .parse(req.nextUrl.searchParams.get("requestId")),
            ),
        );
    } catch (error) {
        return failure(error);
    }
}
export async function POST(req: NextRequest) {
    const auth = await requireAdminForApi();
    if (!auth.ok) return auth.response;
    try {
        const body = submission.parse(await req.json().catch(() => null));
        if (body.operation === "preview")
            return NextResponse.json(await curation.preview(body.command));
        const result = await curation.submit(
            body.command,
            auth.context.profileId,
        );
        return NextResponse.json(result, {
            status:
                result.status === "pending"
                    ? 202
                    : result.status === "conflict"
                      ? 409
                      : result.status === "failed"
                        ? 500
                        : 200,
        });
    } catch (error) {
        return failure(error);
    }
}
