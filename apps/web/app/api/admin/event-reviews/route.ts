import { NextRequest, NextResponse } from "next/server";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { withRequestMetrics } from "@/lib/metrics";
import {
    eventReviewFilters,
    eventReviewSubmission,
    EventReviewConflict,
    getEventReview,
    listEventReviews,
    submitEventReview,
} from "@/lib/admin/eventReviews";

export const dynamic = "force-dynamic";
export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const params = req.nextUrl.searchParams;
    try {
        if (params.has("id")) {
            const id = Number(params.get("id"));
            if (!Number.isSafeInteger(id) || id <= 0)
                return NextResponse.json(
                    { error: "Invalid event ID" },
                    { status: 400 },
                );
            const detail = await getEventReview(id);
            return detail
                ? NextResponse.json(detail)
                : NextResponse.json(
                      { error: "Event not found" },
                      { status: 404 },
                  );
        }
        const parsed = eventReviewFilters.safeParse(Object.fromEntries(params));
        if (!parsed.success)
            return NextResponse.json(
                { error: "Invalid filters" },
                { status: 400 },
            );
        return NextResponse.json(await listEventReviews(parsed.data));
    } catch (error) {
        console.error("Admin event review read failed", error);
        return NextResponse.json(
            { error: "Unable to load event reviews" },
            { status: 500 },
        );
    }
});
export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const parsed = eventReviewSubmission.safeParse(
        await req.json().catch(() => null),
    );
    if (!parsed.success)
        return NextResponse.json(
            { error: "Invalid review: choose an action and provide a reason" },
            { status: 400 },
        );
    try {
        const result = await submitEventReview(
            parsed.data,
            gate.context.profileId,
        );
        return NextResponse.json(result, {
            status: result.status === "pending" ? 202 : 200,
        });
    } catch (error) {
        if (error instanceof EventReviewConflict)
            return NextResponse.json({ error: error.message }, { status: 409 });
        // Concurrent UUID reuse or pending submission is a conflict, not success.
        if (
            typeof error === "object" &&
            error !== null &&
            "code" in error &&
            (error.code === "P2002" ||
                (error.code === "P2010" &&
                    "meta" in error &&
                    String(JSON.stringify(error.meta)).includes("23505")))
        )
            return NextResponse.json(
                {
                    error: "A review was submitted concurrently. Refresh the event.",
                },
                { status: 409 },
            );
        console.error("Admin event review submit failed", error);
        return NextResponse.json(
            { error: "Unable to submit review. Retry with the same request." },
            { status: 500 },
        );
    }
});
