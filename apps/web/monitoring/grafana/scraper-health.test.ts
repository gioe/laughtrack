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
