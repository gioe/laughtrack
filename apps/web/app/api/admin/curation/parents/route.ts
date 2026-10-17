import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { parentRelationships } from "@/lib/admin/curation/runtime";
import { CurationError } from "@/lib/admin/curation/decisions";
function failure(error: unknown) {
    if (error instanceof z.ZodError)
        return NextResponse.json(
            {
                error: "Provide both endpoints, a reason and independent same-performer evidence.",
            },
            { status: 400 },
        );
    if (error instanceof CurationError)
        return NextResponse.json(
            { error: error.message, code: error.code },
            { status: error.status },
        );
    console.error("Parent relationship review failed", error);
    return NextResponse.json(
        {
            error: "Unable to change relationship. Refresh the preview and check endpoint eligibility.",
        },
        { status: 409 },
    );
}
export async function GET(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    try {
        return NextResponse.json({
            relationships: await parentRelationships.history(
                z.coerce
                    .number()
                    .int()
                    .positive()
                    .parse(req.nextUrl.searchParams.get("childId")),
            ),
        });
    } catch (e) {
        return failure(e);
    }
}
export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    try {
        const { operation, ...input } = z
            .object({ operation: z.enum(["propose", "preview", "submit"]) })
            .passthrough()
            .parse(await req.json());
        return NextResponse.json(
            operation === "propose"
                ? await parentRelationships.propose(
                      input,
                      gate.context.profileId,
                  )
                : operation === "preview"
                  ? await parentRelationships.preview(input)
                  : await parentRelationships.submit(
                        input,
                        gate.context.profileId,
                    ),
        );
    } catch (e) {
        return failure(e);
    }
}
