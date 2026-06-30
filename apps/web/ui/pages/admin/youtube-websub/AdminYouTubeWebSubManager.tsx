"use client";

import { useState } from "react";
import type {
    YouTubeWebSubComedianRow,
    YouTubeWebSubEventDetail,
    YouTubeWebSubEventRow,
    YouTubeWebSubSettingsView,
} from "@/lib/admin/youtubeWebSub";

type SettingsFlag = keyof YouTubeWebSubSettingsView;
type ComedianFlag =
    | "youtubeLiveFeedEnabled"
    | "youtubeLiveNotificationsEnabled";

type AdminYouTubeWebSubManagerProps = {
    settings: YouTubeWebSubSettingsView;
    comedians: YouTubeWebSubComedianRow[];
    events: YouTubeWebSubEventRow[];
};

function formatDateTime(value: string | null): string {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function AdminYouTubeWebSubManager({
    settings,
    comedians,
    events,
}: AdminYouTubeWebSubManagerProps) {
    return (
        <div className="space-y-8">
            <GlobalSettingsCard settings={settings} />
            <ComedianFlagsTable comedians={comedians} />
            <EventViewer events={events} />
        </div>
    );
}

function GlobalSettingsCard({
    settings,
}: {
    settings: YouTubeWebSubSettingsView;
}) {
    const [values, setValues] =
        useState<YouTubeWebSubSettingsView>(settings);
    const [savingFlag, setSavingFlag] = useState<SettingsFlag | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function saveFlag(flag: SettingsFlag, value: boolean) {
        setSavingFlag(flag);
        setError(null);
        try {
            const response = await fetch("/api/admin/youtube-websub", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [flag]: value }),
            });
            const body = await response.json().catch(() => ({}));
            if (!response.ok) {
                setError(
                    typeof body.error === "string" ? body.error : "Save failed",
                );
                return;
            }
            setValues((prev) => ({ ...prev, [flag]: value }));
        } catch {
            setError("Save failed");
        } finally {
            setSavingFlag(null);
        }
    }

    return (
        <section className="rounded-md border border-copper/20 bg-white p-5">
            <h2 className="font-urbanist-bold text-h3 text-cedar">
                Global rollout
            </h2>
            <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                Master switches. Feed ingestion gates all subscriptions and
                received events; notification delivery gates push sends.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <CheckboxField
                    label="Feed ingestion enabled"
                    checked={values.feedIngestionEnabled}
                    saving={savingFlag === "feedIngestionEnabled"}
                    onChange={(checked) =>
                        saveFlag("feedIngestionEnabled", checked)
                    }
                />
                <CheckboxField
                    label="Push delivery enabled"
                    checked={values.pushDeliveryEnabled}
                    saving={savingFlag === "pushDeliveryEnabled"}
                    onChange={(checked) =>
                        saveFlag("pushDeliveryEnabled", checked)
                    }
                />
            </div>
            {error ? (
                <p className="mt-3 font-dmSans text-caption text-red-700">
                    {error}
                </p>
            ) : null}
        </section>
    );
}

function ComedianFlagsTable({
    comedians,
}: {
    comedians: YouTubeWebSubComedianRow[];
}) {
    const [overrides, setOverrides] = useState<
        Record<string, Partial<Record<ComedianFlag, boolean>>>
    >({});
    const [savingKey, setSavingKey] = useState<string | null>(null);
    const [error, setError] = useState<{ uuid: string; message: string } | null>(
        null,
    );

    async function saveFlag(
        comedian: YouTubeWebSubComedianRow,
        flag: ComedianFlag,
        value: boolean,
    ) {
        const key = `${comedian.uuid}:${flag}`;
        setSavingKey(key);
        setError(null);
        try {
            const response = await fetch(
                `/api/admin/youtube-websub/comedians/${encodeURIComponent(comedian.uuid)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ [flag]: value }),
                },
            );
            const body = await response.json().catch(() => ({}));
            if (!response.ok) {
                setError({
                    uuid: comedian.uuid,
                    message:
                        typeof body.error === "string"
                            ? body.error
                            : "Save failed",
                });
                return;
            }
            setOverrides((prev) => ({
                ...prev,
                [comedian.uuid]: { ...prev[comedian.uuid], [flag]: value },
            }));
        } catch {
            setError({ uuid: comedian.uuid, message: "Save failed" });
        } finally {
            setSavingKey(null);
        }
    }

    return (
        <section className="rounded-md border border-copper/20 bg-white p-5">
            <h2 className="font-urbanist-bold text-h3 text-cedar">
                Comedian feeds
            </h2>
            <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                Per-comedian live-feed and notification flags, with current
                subscription and most recent event status.
            </p>
            {comedians.length === 0 ? (
                <p className="mt-4 font-dmSans text-body text-soft-charcoal">
                    No comedians have a YouTube channel ID yet.
                </p>
            ) : (
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full border-collapse font-dmSans text-body">
                        <thead>
                            <tr className="border-b border-copper/15 text-left text-caption uppercase text-soft-charcoal">
                                <th className="px-2 py-2">Comedian</th>
                                <th className="px-2 py-2">Live feed</th>
                                <th className="px-2 py-2">Notifications</th>
                                <th className="px-2 py-2">Subscription</th>
                                <th className="px-2 py-2">Recent event</th>
                            </tr>
                        </thead>
                        <tbody>
                            {comedians.map((comedian) => {
                                const liveFeed =
                                    overrides[comedian.uuid]
                                        ?.youtubeLiveFeedEnabled ??
                                    comedian.youtubeLiveFeedEnabled;
                                const notifications =
                                    overrides[comedian.uuid]
                                        ?.youtubeLiveNotificationsEnabled ??
                                    comedian.youtubeLiveNotificationsEnabled;
                                return (
                                    <tr
                                        key={comedian.uuid}
                                        className="border-b border-copper/10 align-top"
                                    >
                                        <td className="px-2 py-3">
                                            <div className="font-semibold text-cedar">
                                                {comedian.name}
                                            </div>
                                            <div className="font-mono text-caption text-soft-charcoal">
                                                {comedian.youtubeChannelId ??
                                                    "no channel id"}
                                            </div>
                                        </td>
                                        <td className="px-2 py-3">
                                            <CheckboxField
                                                label={`Live feed for ${comedian.name}`}
                                                hideLabel
                                                checked={liveFeed}
                                                saving={
                                                    savingKey ===
                                                    `${comedian.uuid}:youtubeLiveFeedEnabled`
                                                }
                                                onChange={(checked) =>
                                                    saveFlag(
                                                        comedian,
                                                        "youtubeLiveFeedEnabled",
                                                        checked,
                                                    )
                                                }
                                            />
                                        </td>
                                        <td className="px-2 py-3">
                                            <CheckboxField
                                                label={`Notifications for ${comedian.name}`}
                                                hideLabel
                                                checked={notifications}
                                                saving={
                                                    savingKey ===
                                                    `${comedian.uuid}:youtubeLiveNotificationsEnabled`
                                                }
                                                onChange={(checked) =>
                                                    saveFlag(
                                                        comedian,
                                                        "youtubeLiveNotificationsEnabled",
                                                        checked,
                                                    )
                                                }
                                            />
                                        </td>
                                        <td className="px-2 py-3">
                                            <div className="text-cedar">
                                                {comedian.subscriptionStatus ??
                                                    "none"}
                                            </div>
                                            {comedian.lastSubscribeError ? (
                                                <div className="text-caption text-red-700">
                                                    {comedian.lastSubscribeError}
                                                </div>
                                            ) : null}
                                        </td>
                                        <td className="px-2 py-3">
                                            <div className="text-cedar">
                                                {comedian.recentEventStatus ??
                                                    "—"}
                                            </div>
                                            <div className="text-caption text-soft-charcoal">
                                                {formatDateTime(
                                                    comedian.recentEventAt,
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
            {error ? (
                <p className="mt-3 font-dmSans text-caption text-red-700">
                    {error.message}
                </p>
            ) : null}
        </section>
    );
}

function EventViewer({ events }: { events: YouTubeWebSubEventRow[] }) {
    const [selected, setSelected] =
        useState<YouTubeWebSubEventDetail | null>(null);
    const [loadingId, setLoadingId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function openEvent(id: number) {
        setLoadingId(id);
        setError(null);
        try {
            const response = await fetch(
                `/api/admin/youtube-websub?eventId=${id}`,
            );
            const body = await response.json().catch(() => ({}));
            if (!response.ok || !body.event) {
                setError(
                    typeof body.error === "string"
                        ? body.error
                        : "Failed to load event",
                );
                return;
            }
            setSelected(body.event as YouTubeWebSubEventDetail);
        } catch {
            setError("Failed to load event");
        } finally {
            setLoadingId(null);
        }
    }

    return (
        <section className="rounded-md border border-copper/20 bg-white p-5">
            <h2 className="font-urbanist-bold text-h3 text-cedar">
                Received events
            </h2>
            <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                Most recent WebSub notifications. Open one to inspect its raw
                payload, parsed IDs, verification result, and suppression
                reason.
            </p>
            {events.length === 0 ? (
                <p className="mt-4 font-dmSans text-body text-soft-charcoal">
                    No events received yet.
                </p>
            ) : (
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full border-collapse font-dmSans text-body">
                        <thead>
                            <tr className="border-b border-copper/15 text-left text-caption uppercase text-soft-charcoal">
                                <th className="px-2 py-2">Received</th>
                                <th className="px-2 py-2">Comedian</th>
                                <th className="px-2 py-2">Video</th>
                                <th className="px-2 py-2">Status</th>
                                <th className="px-2 py-2">Verification</th>
                                <th className="px-2 py-2">Suppression</th>
                                <th className="px-2 py-2" />
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((event) => (
                                <tr
                                    key={event.id}
                                    className="border-b border-copper/10 align-top"
                                >
                                    <td className="px-2 py-3 text-caption text-soft-charcoal">
                                        {formatDateTime(event.receivedAt)}
                                    </td>
                                    <td className="px-2 py-3">
                                        <div className="text-cedar">
                                            {event.comedianName ?? "—"}
                                        </div>
                                        <div className="font-mono text-caption text-soft-charcoal">
                                            {event.youtubeChannelId ?? "—"}
                                        </div>
                                    </td>
                                    <td className="px-2 py-3">
                                        <div className="text-cedar">
                                            {event.videoTitle ?? "—"}
                                        </div>
                                        <div className="font-mono text-caption text-soft-charcoal">
                                            {event.youtubeVideoId ?? "—"}
                                        </div>
                                    </td>
                                    <td className="px-2 py-3 text-cedar">
                                        {event.eventStatus}
                                    </td>
                                    <td className="px-2 py-3 text-cedar">
                                        {event.verificationStatus ?? "—"}
                                    </td>
                                    <td className="px-2 py-3 text-cedar">
                                        {event.suppressionReason ?? "—"}
                                    </td>
                                    <td className="px-2 py-3">
                                        <button
                                            type="button"
                                            onClick={() => openEvent(event.id)}
                                            disabled={loadingId === event.id}
                                            className="rounded-md border border-copper/35 bg-white px-3 py-1 font-dmSans text-caption font-semibold text-cedar hover:bg-copper/10 disabled:opacity-60"
                                        >
                                            {loadingId === event.id
                                                ? "Loading…"
                                                : "View payload"}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            {error ? (
                <p className="mt-3 font-dmSans text-caption text-red-700">
                    {error}
                </p>
            ) : null}
            {selected ? (
                <EventDetailPanel
                    event={selected}
                    onClose={() => setSelected(null)}
                />
            ) : null}
        </section>
    );
}

function EventDetailPanel({
    event,
    onClose,
}: {
    event: YouTubeWebSubEventDetail;
    onClose: () => void;
}) {
    return (
        <div className="mt-5 rounded-md border border-copper/25 bg-coconut-cream/40 p-4">
            <div className="flex items-center justify-between">
                <h3 className="font-urbanist-bold text-body text-cedar">
                    Event #{event.id} payload
                </h3>
                <button
                    type="button"
                    onClick={onClose}
                    className="font-dmSans text-caption font-semibold text-copper-dark hover:underline"
                >
                    Close
                </button>
            </div>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2 font-dmSans text-caption">
                <DetailItem label="Channel ID" value={event.youtubeChannelId} />
                <DetailItem label="Video ID" value={event.youtubeVideoId} />
                <DetailItem
                    label="Verification result"
                    value={event.verificationStatus}
                />
                <DetailItem
                    label="Suppression reason"
                    value={event.suppressionReason}
                />
                <DetailItem
                    label="Failure reason"
                    value={event.failureReason}
                />
                <DetailItem
                    label="Live broadcast"
                    value={event.liveBroadcastContent}
                />
            </dl>
            <div className="mt-3">
                <p className="font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                    Raw payload (XML)
                </p>
                <pre
                    data-testid="event-payload-xml"
                    className="mt-1 max-h-72 overflow-auto rounded bg-cedar/95 p-3 font-mono text-caption text-coconut-cream"
                >
                    {event.payloadXml}
                </pre>
            </div>
        </div>
    );
}

function DetailItem({
    label,
    value,
}: {
    label: string;
    value: string | null;
}) {
    return (
        <div>
            <dt className="font-semibold uppercase text-soft-charcoal">
                {label}
            </dt>
            <dd className="font-mono text-cedar">{value ?? "—"}</dd>
        </div>
    );
}

function CheckboxField({
    label,
    hideLabel,
    checked,
    saving,
    onChange,
}: {
    label: string;
    hideLabel?: boolean;
    checked: boolean;
    saving: boolean;
    onChange: (checked: boolean) => void;
}) {
    return (
        <label className="flex items-center gap-2 font-dmSans text-body text-cedar">
            <input
                type="checkbox"
                aria-label={label}
                checked={checked}
                disabled={saving}
                onChange={(event) => onChange(event.target.checked)}
                className="h-4 w-4 rounded border-soft-charcoal/40 text-copper-dark focus:ring-copper/30"
            />
            {hideLabel ? null : (
                <span className="font-semibold">{label}</span>
            )}
            {saving ? (
                <span className="text-caption text-soft-charcoal">Saving…</span>
            ) : null}
        </label>
    );
}
