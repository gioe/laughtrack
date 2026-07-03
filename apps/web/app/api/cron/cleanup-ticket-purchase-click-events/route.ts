import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";

const RETENTION_MONTHS = 13;

type CleanupResult = {
    deleted_count: bigint | number | string | null;
};

async function handleTicketPurchaseClickCleanup(req: NextRequest) {
    if (!hasValidCronBearer(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const rows = await db.$queryRaw<CleanupResult[]>`
            SELECT cleanup_old_ticket_purchase_click_events() AS deleted_count
        `;
        const deleted = Number(rows[0]?.deleted_count ?? 0);

        console.info(
            `[cron/cleanup-ticket-purchase-click-events] deleted ${deleted} ` +
                `ticket purchase click events older than ${RETENTION_MONTHS} months`,
        );

        return NextResponse.json({
            deleted,
            retentionMonths: RETENTION_MONTHS,
        });
    } catch (error) {
        console.error(
            "[cron/cleanup-ticket-purchase-click-events] failed:",
            error,
        );
        return NextResponse.json(
            { error: "ticket_purchase_click_cleanup_failed" },
            { status: 500 },
        );
    }
}

export const GET = withRequestMetrics(handleTicketPurchaseClickCleanup);
export const POST = withRequestMetrics(handleTicketPurchaseClickCleanup);

function hasValidCronBearer(req: NextRequest): boolean {
    const authHeader = req.headers.get("authorization");
    const bearerToken = authHeader?.startsWith("Bearer ")
        ? authHeader.slice(7)
        : null;
    const cronSecret = process.env.CRON_SECRET;

    if (!bearerToken || !cronSecret) {
        return false;
    }

    const bearerBuf = Buffer.from(bearerToken);
    const secretBuf = Buffer.from(cronSecret);

    return (
        bearerBuf.length === secretBuf.length &&
        timingSafeEqual(bearerBuf, secretBuf)
    );
}
