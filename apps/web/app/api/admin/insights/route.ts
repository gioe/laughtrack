import { getAdminInsight, listAdminInsights } from "@/lib/admin/insights";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";
import { getDiscoveryEvaluation } from "@/lib/admin/discoveryInsights";

const executeSchema = z
    .object({
        insight: z.string().trim().min(1).max(100),
        params: z.unknown().optional(),
    })
    .strict();

async function readJson(
    req: NextRequest,
): Promise<
    | { ok: true; body: unknown }
    | { ok: false; response: NextResponse<{ error: string }> }
> {
    try {
        return { ok: true, body: await req.json() };
    } catch {
        return {
            ok: false,
            response: NextResponse.json(
                { error: "Body must be valid JSON" },
                { status: 400 },
            ),
        };
    }
}

function invalidPayload(error: z.ZodError) {
    return NextResponse.json(
        { error: "Invalid payload", issues: error.issues },
        { status: 400 },
    );
}

export const GET = withRequestMetrics(async function GET(req?: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    if (req?.nextUrl.searchParams.get("report") === "discovery") {
        const parsedDays = z.coerce
            .number()
            .int()
            .min(1)
            .max(90)
            .safeParse(req.nextUrl.searchParams.get("days") ?? 14);
        if (!parsedDays.success) {
            return NextResponse.json(
                { error: "days must be an integer between 1 and 90" },
                { status: 400 },
            );
        }
        return NextResponse.json({
            discovery: await getDiscoveryEvaluation({
                days: parsedDays.data,
            }),
        });
    }

    return NextResponse.json({ insights: listAdminInsights() });
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const json = await readJson(req);
    if (!json.ok) return json.response;

    const parsed = executeSchema.safeParse(json.body);
    if (!parsed.success) return invalidPayload(parsed.error);

    const insight = getAdminInsight(parsed.data.insight);
    if (!insight) {
        return NextResponse.json({ error: "Unknown insight" }, { status: 400 });
    }

    let params: ReturnType<typeof insight.parseParams>;
    try {
        params = insight.parseParams(parsed.data.params);
    } catch (error) {
        if (error instanceof z.ZodError) {
            return NextResponse.json(
                { error: "Invalid parameters", issues: error.issues },
                { status: 400 },
            );
        }
        throw error;
    }

    const rows = await db.$queryRaw(insight.buildQuery(params as never));

    return NextResponse.json({
        ok: true,
        insight: insight.name,
        rows,
    });
});
