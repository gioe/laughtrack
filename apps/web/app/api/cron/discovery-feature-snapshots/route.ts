import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { runDiscoveryFeatureSnapshotJob } from "@/lib/discovery/featureSnapshotJob";
import { withRequestMetrics } from "@/lib/metrics";

function hasValidCronBearer(request: NextRequest): boolean {
    const authHeader = request.headers.get("authorization");
    const bearerToken = authHeader?.startsWith("Bearer ")
        ? authHeader.slice(7)
        : null;
    const cronSecret = process.env.CRON_SECRET;
    if (!bearerToken || !cronSecret) return false;

    const bearerBuffer = Buffer.from(bearerToken);
    const secretBuffer = Buffer.from(cronSecret);
    return (
        bearerBuffer.length === secretBuffer.length &&
        timingSafeEqual(bearerBuffer, secretBuffer)
    );
}

async function handleDiscoveryFeatureSnapshots(request: NextRequest) {
    if (!hasValidCronBearer(request)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const asOfParam = request.nextUrl.searchParams.get("asOf");
    const asOf = asOfParam ? new Date(asOfParam) : undefined;
    if (asOf && Number.isNaN(asOf.getTime())) {
        return NextResponse.json({ error: "invalid_as_of" }, { status: 400 });
    }

    try {
        const result = await runDiscoveryFeatureSnapshotJob({ asOf });
        if (result.failed > 0) {
            return NextResponse.json(
                {
                    error: "discovery_feature_snapshot_partial_failure",
                    ...result,
                },
                { status: 500 },
            );
        }
        return NextResponse.json(result);
    } catch (error) {
        console.error("[cron/discovery-feature-snapshots] failed:", error);
        return NextResponse.json(
            { error: "discovery_feature_snapshot_job_failed" },
            { status: 500 },
        );
    }
}

export const GET = withRequestMetrics(handleDiscoveryFeatureSnapshots);
export const POST = withRequestMetrics(handleDiscoveryFeatureSnapshots);
