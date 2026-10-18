import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { hostRelationships } from "@/lib/admin/curation/runtime";
import { CurationError } from "@/lib/admin/curation/decisions";
function failure(e: unknown) {
    if (e instanceof z.ZodError)
        return NextResponse.json(
            { error: "Invalid host review payload" },
            { status: 400 },
        );
    if (e instanceof CurationError)
        return NextResponse.json(
            { error: e.message, code: e.code },
            { status: e.status },
        );
    console.error("Host review failed", e);
    return NextResponse.json(
        {
            error: "Host review failed. Check endpoint approvals and unresolved identity reconciliations.",
        },
        { status: 409 },
    );
}
export async function GET(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    try {
        return NextResponse.json({
            relationships: await hostRelationships.history(
                z.coerce
                    .number()
                    .int()
                    .positive()
                    .parse(req.nextUrl.searchParams.get("podcastId")),
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
        const { operation, input } = z
            .object({
                operation: z.enum([
                    "propose",
                    "preview",
                    "submit",
                    "previewReconciliation",
                    "reconcile",
                ]),
                input: z.unknown(),
            })
            .strict()
            .parse(await req.json());
        if (operation === "previewReconciliation")
            return NextResponse.json(
                await hostRelationships.previewReconciliation(
                    z
                        .object({ id: z.string().min(1) })
                        .strict()
                        .parse(input).id,
                ),
            );
        const result =
            operation === "propose"
                ? await hostRelationships.propose(input, gate.context.profileId)
                : operation === "preview"
                  ? await hostRelationships.preview(input)
                  : operation === "submit"
                    ? await hostRelationships.submit(
                          input,
                          gate.context.profileId,
                      )
                    : await hostRelationships.reconcile(
                          input,
                          gate.context.profileId,
                      );
        return NextResponse.json(result, {
            status:
                "status" in result && result.status === "conflict"
                    ? 409
                    : "status" in result && result.status === "failed"
                      ? 500
                      : 200,
        });
    } catch (e) {
        return failure(e);
    }
}
