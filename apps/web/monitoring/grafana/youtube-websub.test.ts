import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const grafanaDir = dirname(fileURLToPath(import.meta.url));
const dashboardPath = join(grafanaDir, "youtube-websub.json");
const grantsPath = join(
    grafanaDir,
    "../../prisma/scripts/create_grafana_readonly_role.sql",
);

function loadDashboard() {
    return JSON.parse(readFileSync(dashboardPath, "utf8")) as {
        title: string;
        uid: string;
        panels: Array<{
            title: string;
            targets?: Array<{ rawSql?: string }>;
        }>;
    };
}

function allPanelSql(dashboard: ReturnType<typeof loadDashboard>): string {
    return dashboard.panels
        .flatMap((panel) => panel.targets ?? [])
        .map((target) => target.rawSql ?? "")
        .join("\n");
}

describe("YouTube WebSub Grafana dashboard", () => {
    it("covers WebSub callback, lease, verification, and push delivery health", () => {
        const dashboard = loadDashboard();

        expect(dashboard.title).toBe("YouTube WebSub");
        expect(dashboard.uid).toBe("youtube-websub");
        expect(dashboard.panels.map((panel) => panel.title)).toEqual([
            "WebSub callbacks received",
            "Subscription renewal health",
            "Verification outcomes",
            "YouTube live push delivery",
        ]);

        const sql = allPanelSql(dashboard);

        expect(sql).toContain("youtube_websub_events");
        expect(sql).toContain("received_at");
        expect(sql).toContain("youtube_websub_subscriptions");
        expect(sql).toContain("lease_expires_at");
        expect(sql).toContain("verification_status");
        expect(sql).toContain("youtube_live_notifications");
        expect(sql).toContain("youtube_live_notification_deliveries");
        expect(sql).toContain("suppressed");
        expect(sql).toContain("sent");
        expect(sql).toContain("failed");
    });

    it("grants the Grafana read-only role access to WebSub observability tables", () => {
        const grants = readFileSync(grantsPath, "utf8");

        expect(grants).toContain("public.youtube_websub_events");
        expect(grants).toContain("public.youtube_websub_subscriptions");
        expect(grants).toContain("public.youtube_live_notifications");
        expect(grants).toContain("public.youtube_live_notification_deliveries");
    });
});
