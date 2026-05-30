import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const noStore = {
    "Cache-Control": "no-store, max-age=0",
};

export const GET = withRequestMetrics(async function GET() {
    try {
        // Cheap round-trip that proves Neon is actually reachable, not just
        // that the app process is up. Returns 503 so UptimeRobot/Grafana can
        // page on a data-layer outage instead of waiting for the homepage canary.
        await db.$queryRaw`SELECT 1`;
    } catch {
        return NextResponse.json(
            {
                status: "error",
                database: "unreachable",
                timestamp: new Date().toISOString(),
            },
            {
                status: 503,
                headers: noStore,
            },
        );
    }

    return NextResponse.json(
        {
            status: "ok",
            database: "ok",
            timestamp: new Date().toISOString(),
        },
        {
            status: 200,
            headers: noStore,
        },
    );
});
