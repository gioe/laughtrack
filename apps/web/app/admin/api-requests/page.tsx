import { Activity, AlertTriangle, Route, TrendingUp } from "lucide-react";
import Link from "next/link";
import {
    API_REQUEST_RANGES,
    getApiRequestMetrics,
    type BreakdownRow,
    type RouteVolume,
    type TrendPoint,
} from "@/lib/admin/apiRequests";
import AdminPageHeader from "@/ui/pages/admin/shared/AdminPageHeader";

export const dynamic = "force-dynamic";

const numberFormat = new Intl.NumberFormat("en-US");
const percentFormat = new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 2,
});
const hourFormat = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
});

function formatHour(iso: string): string {
    if (!iso) return "—";
    return `${hourFormat.format(new Date(iso))} UTC`;
}

// Semantic colors for HTTP status classes (standard Tailwind palette).
function statusColor(statusClass: string): string {
    if (statusClass.startsWith("2")) return "bg-emerald-500";
    if (statusClass.startsWith("3")) return "bg-sky-500";
    if (statusClass.startsWith("4")) return "bg-amber-500";
    if (statusClass.startsWith("5")) return "bg-rose-500";
    return "bg-soft-charcoal";
}

function SummaryCard({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon: typeof Activity;
}) {
    return (
        <div className="rounded-md border border-copper/20 bg-white p-4">
            <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-copper/10 text-copper-dark">
                    <Icon className="h-5 w-5" />
                </span>
                <div>
                    <p className="font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                        {label}
                    </p>
                    <p className="font-gilroy-bold text-h3 text-cedar">
                        {value}
                    </p>
                </div>
            </div>
        </div>
    );
}

function BreakdownBars({
    title,
    rows,
    colorFor,
}: {
    title: string;
    rows: BreakdownRow[];
    colorFor: (key: string) => string;
}) {
    const total = rows.reduce((sum, row) => sum + row.count, 0);

    return (
        <div className="rounded-md border border-copper/20 bg-white p-4">
            <h2 className="font-gilroy-bold text-h4 text-cedar">{title}</h2>
            {rows.length === 0 ? (
                <p className="mt-3 font-dmSans text-caption text-soft-charcoal">
                    No data in this window.
                </p>
            ) : (
                <ul className="mt-3 space-y-3">
                    {rows.map((row) => {
                        const share = total > 0 ? row.count / total : 0;
                        return (
                            <li key={row.key}>
                                <div className="flex items-baseline justify-between font-dmSans text-caption">
                                    <span className="font-semibold uppercase text-cedar">
                                        {row.key}
                                    </span>
                                    <span className="text-soft-charcoal">
                                        {numberFormat.format(row.count)} ·{" "}
                                        {percentFormat.format(share)}
                                    </span>
                                </div>
                                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-coconut-cream">
                                    <div
                                        className={`h-full rounded-full ${colorFor(row.key)}`}
                                        style={{
                                            width: `${Math.max(share * 100, 1)}%`,
                                        }}
                                    />
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}

function TopRoutesTable({
    routes,
    rangeKey,
    selectedRoute,
}: {
    routes: RouteVolume[];
    rangeKey: string;
    selectedRoute: string | null;
}) {
    const maxCount = routes.reduce(
        (max, route) => Math.max(max, route.count),
        0,
    );

    return (
        <div className="overflow-hidden rounded-md border border-copper/20 bg-white">
            <div className="border-b border-copper/15 px-4 py-3">
                <h2 className="font-gilroy-bold text-h4 text-cedar">
                    Top routes by volume
                </h2>
                <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                    Select a route to see its trend below.
                </p>
            </div>
            {routes.length === 0 ? (
                <p className="px-4 py-6 font-dmSans text-body text-soft-charcoal">
                    No requests recorded in this window.
                </p>
            ) : (
                <table className="w-full border-collapse font-dmSans text-body">
                    <thead>
                        <tr className="bg-coconut-cream/50 text-left font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                            <th className="px-4 py-2">Route</th>
                            <th className="px-4 py-2 text-right">Requests</th>
                            <th className="px-4 py-2 text-right">Errors</th>
                            <th className="w-40 px-4 py-2">Share</th>
                        </tr>
                    </thead>
                    <tbody>
                        {routes.map((route) => {
                            const isSelected =
                                route.routePattern === selectedRoute;
                            const width =
                                maxCount > 0
                                    ? (route.count / maxCount) * 100
                                    : 0;
                            return (
                                <tr
                                    key={route.routePattern}
                                    className={`border-t border-copper/10 ${
                                        isSelected ? "bg-copper/10" : ""
                                    }`}
                                >
                                    <td className="px-4 py-2">
                                        <Link
                                            href={`/admin/api-requests?range=${rangeKey}&route=${encodeURIComponent(
                                                route.routePattern,
                                            )}`}
                                            className="font-mono text-caption text-copper-dark hover:underline"
                                        >
                                            {route.routePattern}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-2 text-right tabular-nums text-cedar">
                                        {numberFormat.format(route.count)}
                                    </td>
                                    <td className="px-4 py-2 text-right tabular-nums text-soft-charcoal">
                                        {route.errorCount > 0
                                            ? numberFormat.format(
                                                  route.errorCount,
                                              )
                                            : "—"}
                                    </td>
                                    <td className="px-4 py-2">
                                        <div className="h-2 w-full overflow-hidden rounded-full bg-coconut-cream">
                                            <div
                                                className="h-full rounded-full bg-copper"
                                                style={{
                                                    width: `${Math.max(width, 1)}%`,
                                                }}
                                            />
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
}

function RouteTrend({
    selectedRoute,
    trend,
}: {
    selectedRoute: string | null;
    trend: TrendPoint[];
}) {
    const maxCount = trend.reduce(
        (max, point) => Math.max(max, point.count),
        0,
    );

    return (
        <div className="rounded-md border border-copper/20 bg-white p-4">
            <h2 className="font-gilroy-bold text-h4 text-cedar">
                Per-route trend
            </h2>
            {selectedRoute ? (
                <p className="mt-1 font-mono text-caption text-copper-dark">
                    {selectedRoute}
                </p>
            ) : null}
            {trend.length === 0 ? (
                <p className="mt-3 font-dmSans text-body text-soft-charcoal">
                    No trend data for this route in this window.
                </p>
            ) : (
                <div className="mt-4 flex h-48 items-end gap-px overflow-x-auto">
                    {trend.map((point) => {
                        const height =
                            maxCount > 0
                                ? (point.count / maxCount) * 100
                                : 0;
                        const errorShare =
                            point.count > 0
                                ? point.errorCount / point.count
                                : 0;
                        return (
                            <div
                                key={point.hourBucket}
                                className="group relative flex h-full min-w-[6px] flex-1 items-end"
                                title={`${formatHour(point.hourBucket)} · ${numberFormat.format(
                                    point.count,
                                )} req${
                                    point.errorCount > 0
                                        ? ` · ${numberFormat.format(point.errorCount)} err`
                                        : ""
                                }`}
                            >
                                {/* Single stacked bar: copper volume with the
                                    error portion nested at the top in rose. */}
                                <div
                                    className="flex w-full flex-col overflow-hidden rounded-t-sm bg-copper/70"
                                    style={{ height: `${Math.max(height, 1)}%` }}
                                >
                                    <div
                                        className="w-full bg-rose-500"
                                        style={{ height: `${errorShare * 100}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
            {trend.length > 0 ? (
                <div className="mt-2 flex justify-between font-dmSans text-caption text-soft-charcoal">
                    <span>{formatHour(trend[0].hourBucket)}</span>
                    <span>{formatHour(trend[trend.length - 1].hourBucket)}</span>
                </div>
            ) : null}
        </div>
    );
}

export default async function AdminApiRequestsPage({
    searchParams,
}: {
    searchParams: Promise<{ range?: string; route?: string }>;
}) {
    const params = await searchParams;
    const data = await getApiRequestMetrics({
        rangeParam: params.range,
        routeParam: params.route,
    });

    const { range, totals, topRoutes, statusBreakdown, methodBreakdown } = data;

    return (
        <div className="space-y-6">
            <AdminPageHeader
                eyebrow="Admin · API Requests"
                title="API request metrics"
                description="Per-route request volume recorded by the withRequestMetrics wrapper into api_request_metrics. Same data as the Grafana Cloud dashboard, viewable in-app."
                summary={
                    totals.lastBucket
                        ? `Data ${
                              totals.firstBucket
                                  ? `${formatHour(totals.firstBucket)} – `
                                  : "through "
                          }${formatHour(totals.lastBucket)}`
                        : undefined
                }
            />

            <div className="flex flex-wrap items-center gap-2">
                {API_REQUEST_RANGES.map((option) => {
                    const isActive = option.key === range.key;
                    const href = `/admin/api-requests?range=${option.key}${
                        params.route
                            ? `&route=${encodeURIComponent(params.route)}`
                            : ""
                    }`;
                    return (
                        <Link
                            key={option.key}
                            href={href}
                            className={`rounded-md border px-3 py-1.5 font-dmSans text-caption font-semibold transition-colors ${
                                isActive
                                    ? "border-copper bg-copper text-white"
                                    : "border-copper/35 bg-white text-cedar hover:bg-copper/10"
                            }`}
                        >
                            {option.label}
                        </Link>
                    );
                })}
            </div>

            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard
                    label="Total requests"
                    value={numberFormat.format(totals.totalRequests)}
                    icon={Activity}
                />
                <SummaryCard
                    label="Errors (4xx/5xx)"
                    value={numberFormat.format(totals.errorRequests)}
                    icon={AlertTriangle}
                />
                <SummaryCard
                    label="Error rate"
                    value={percentFormat.format(totals.errorRate)}
                    icon={TrendingUp}
                />
                <SummaryCard
                    label="Distinct routes"
                    value={numberFormat.format(totals.distinctRoutes)}
                    icon={Route}
                />
            </section>

            <section className="grid gap-3 md:grid-cols-2">
                <BreakdownBars
                    title="By status class"
                    rows={statusBreakdown}
                    colorFor={statusColor}
                />
                <BreakdownBars
                    title="By method"
                    rows={methodBreakdown}
                    colorFor={() => "bg-copper"}
                />
            </section>

            <TopRoutesTable
                routes={topRoutes}
                rangeKey={range.key}
                selectedRoute={data.selectedRoute}
            />

            <RouteTrend
                selectedRoute={data.selectedRoute}
                trend={data.routeTrend}
            />
        </div>
    );
}
