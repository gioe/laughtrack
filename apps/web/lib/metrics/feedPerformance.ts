import type { NextRequest } from "next/server";
import { scheduleMetricWrite } from "./withRequestMetrics";

/** This allowlist is shared with the iOS Server-Timing parser. Never use request data as labels. */
export const FEED_PROVIDERS = [
    "auth",
    "policy",
    "hero",
    "trending_comedians",
    "clubs",
    "comedians_near_you",
    "shows_tonight",
    "shows_near_zip",
    "trending_this_week",
    "podcast_episodes",
    "trending_podcasts",
    "followed_shows",
    "touring",
    "fresh",
    "affinity",
] as const;
export type FeedProvider = (typeof FEED_PROVIDERS)[number];
export type FeedProviderOutcome = "success" | "error" | "timeout" | "skipped";
type Account = "anonymous" | "authenticated" | "unknown";
type Platform = "web" | "ios" | "android" | "unknown";
interface Timing {
    duration_ms: number;
    outcome: FeedProviderOutcome;
}
export interface FeedPerformanceReport {
    event: "discover_feed_performance";
    version: 1;
    platform: Platform;
    account: Account;
    status_class: "2xx" | "3xx" | "4xx" | "5xx";
    total_ms: number;
    providers: Record<FeedProvider, Timing>;
}
const boundedDuration = (value: number) =>
    Number.isFinite(value)
        ? Math.round(Math.min(120_000, Math.max(0, value)) * 10) / 10
        : 0;

export function createFeedPerformance(
    clock: () => number = () => performance.now(),
) {
    const start = clock();
    let closed = false;
    let platform: Platform = "unknown";
    let account: Account = "unknown";
    const providers = Object.fromEntries(
        FEED_PROVIDERS.map((name) => [
            name,
            { duration_ms: 0, outcome: "skipped" },
        ]),
    ) as Record<FeedProvider, Timing>;
    const observe = (name: FeedProvider) => {
        const began = clock();
        let reported = false;
        return (outcome: FeedProviderOutcome) => {
            if (closed || reported) return;
            reported = true;
            providers[name] = {
                duration_ms: boundedDuration(clock() - began),
                outcome,
            };
        };
    };
    return {
        setContext(next: { platform?: Platform; account?: Account }) {
            platform = next.platform ?? platform;
            account = next.account ?? account;
        },
        observe,
        async measure<T>(
            name: FeedProvider,
            load: () => Promise<T>,
        ): Promise<T> {
            const report = observe(name);
            try {
                const value = await load();
                report("success");
                return value;
            } catch (error) {
                report("error");
                throw error;
            }
        },
        finish(status: number): {
            report: FeedPerformanceReport;
            header: string;
        } {
            closed = true;
            const total = boundedDuration(clock() - start);
            const report: FeedPerformanceReport = {
                event: "discover_feed_performance",
                version: 1,
                platform,
                account,
                status_class:
                    status >= 200 && status < 500
                        ? (`${Math.floor(status / 100)}xx` as
                              | "2xx"
                              | "3xx"
                              | "4xx")
                        : "5xx",
                total_ms: total,
                providers: { ...providers },
            };
            const header = [
                `feed_total;dur=${total};desc="${status >= 400 ? "error" : "success"}"`,
                ...FEED_PROVIDERS.map(
                    (name) =>
                        `${name};dur=${providers[name].duration_ms};desc="${providers[name].outcome}"`,
                ),
            ].join(", ");
            return { report, header };
        },
    };
}
export type FeedPerformance = ReturnType<typeof createFeedPerformance>;

/** One bounded log off the response path; headers correlate the same response with iOS rendering. */
export function withFeedPerformance(
    handler: (
        request: NextRequest,
        measurement: FeedPerformance,
    ) => Promise<Response>,
    report: (measurement: FeedPerformanceReport) => unknown = (measurement) =>
        console.info("[discover-performance]", JSON.stringify(measurement)),
): (request: NextRequest) => Promise<Response> {
    return async (request) => {
        const measurement = createFeedPerformance();
        let response: Response | undefined;
        try {
            response = await handler(request, measurement);
            return response;
        } finally {
            // Reporting and header injection are best effort, including failures in the sink.
            try {
                const result = measurement.finish(response?.status ?? 500);
                if (response)
                    response.headers.set("Server-Timing", result.header);
                scheduleMetricWrite(() =>
                    Promise.resolve().then(() => report(result.report)),
                );
            } catch {
                /* Never mask the handler's response or original error. */
            }
        }
    };
}
