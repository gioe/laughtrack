import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const grafanaDir = dirname(fileURLToPath(import.meta.url));
const dashboardPath = join(grafanaDir, "scraper-health.json");
const alertsPath = join(grafanaDir, "scraper-health-alerts.yaml");

function loadDashboard() {
    return JSON.parse(readFileSync(dashboardPath, "utf8")) as {
        refresh: string;
        panels: Array<{
            title: string;
            type: string;
            targets?: Array<{ rawSql?: string }>;
        }>;
    };
}

describe("Scraper Health Grafana cost controls", () => {
    it("keeps the dashboard from polling Neon by default", () => {
        expect(loadDashboard().refresh).toBe("");
    });

    it("uses a cost-aware alert evaluation cadence", () => {
        const alerts = readFileSync(alertsPath, "utf8");

        expect(alerts).toContain("interval: 6h");
        expect(alerts).toContain("nightly at 21:00 UTC");
    });
});

describe("Ticketless-shows panel and alert (TASK-3680)", () => {
    it("charts per-club ticketless_shows from scraper_run_clubs.raw_stat", () => {
        const dashboard = loadDashboard();
        const panel = dashboard.panels.find(
            (p) => p.title === "Ticketless shows per club (over time)",
        );

        expect(panel).toBeDefined();
        const sql = panel?.targets?.[0]?.rawSql ?? "";
        // Reads the raw_stat JSON key TASK-3629 records, from the per-club table.
        expect(sql).toContain("raw_stat->>'ticketless_shows'");
        expect(sql).toContain("scraper_run_clubs");
        // Only real full scrape runs feed the chart (excludes pipeline/verify).
        expect(sql).toContain("run_type = 'scraper'");
    });

    it("alerts on ticketless shows across consecutive runs, inline (no scraper mv)", () => {
        const alerts = readFileSync(alertsPath, "utf8");

        expect(alerts).toContain("uid: scraper-club-ticketless-consecutive");
        expect(alerts).toContain("Club reporting ticketless shows on consecutive runs");
        // Inline live query against raw_stat — deliberately NOT a materialized view.
        expect(alerts).toContain("raw_stat->>'ticketless_shows'");
        expect(alerts).not.toContain("mv_scraper_health_ticketless");
        // Routed like the other scraper-health rules so provisioning picks it up.
        expect(alerts).toContain("service: scraper-health");
    });
});
