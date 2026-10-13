import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import {
    decideReview,
    getReview,
    listReviews,
    ReviewConflict,
    reviewFilters,
    reviewSubmission,
    searchReviewComedians,
    undoReview,
} from "@/lib/admin/reviews";
import { reviewWorkflows } from "@/lib/admin/reviewTypes";
import { revalidatePath, revalidateTag } from "next/cache";
function failure(error: unknown) {
    if (error instanceof z.ZodError)
        return NextResponse.json(
            { error: "Invalid review request." },
            { status: 400 },
        );
    if (error instanceof ReviewConflict)
        return NextResponse.json({ error: error.message }, { status: 409 });
    console.error("Admin review request failed", error);
    return NextResponse.json(
        { error: "Could not load or save this review. Please retry." },
        { status: 500 },
    );
}
export async function GET(req: NextRequest) {
    const auth = await requireAdminForApi();
    if (!auth.ok) return auth.response;
    try {
        const params = Object.fromEntries(req.nextUrl.searchParams);
        if (params.search !== undefined)
            return NextResponse.json(
                await searchReviewComedians(
                    z.string().max(200).parse(params.search),
                ),
            );
        if (params.id) {
            const item = await getReview(
                z.enum(reviewWorkflows).parse(params.workflow),
                z.string().max(100).parse(params.id),
            );
            return item
                ? NextResponse.json(item)
                : NextResponse.json(
                      { error: "Review not found." },
                      { status: 404 },
                  );
        }
        return NextResponse.json(
            await listReviews(reviewFilters.parse(params)),
        );
    } catch (error) {
        return failure(error);
    }
}
export async function POST(req: NextRequest) {
    const auth = await requireAdminForApi();
    if (!auth.ok) return auth.response;
    try {
        const body = await req.json().catch(() => null);
        const result =
            body?.action === "undo"
                ? await undoReview(
                      z.string().uuid().parse(body.decisionId),
                      auth.context.profileId,
                  )
                : await decideReview(
                      reviewSubmission.parse(body),
                      auth.context.profileId,
                  );
        if ("revalidateTags" in result)
            for (const tag of result.revalidateTags ?? []) revalidateTag(tag);
        revalidatePath("/club", "layout");
        revalidatePath("/admin/comedians");
        revalidatePath("/admin/clubs");
        revalidatePath("/comedian", "layout");
        revalidatePath("/podcast", "layout");
        revalidatePath("/show", "layout");
        return NextResponse.json(result, {
            status:
                "status" in result && result.status === "pending" ? 202 : 200,
        });
    } catch (error) {
        return failure(error);
    }
}
