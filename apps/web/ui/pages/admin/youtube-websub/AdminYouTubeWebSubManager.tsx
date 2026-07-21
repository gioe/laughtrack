"use client";

import { useState } from "react";
import type {
    YouTubeWebSubEventDetail,
    YouTubeWebSubEventRow,
} from "@/lib/admin/youtubeWebSub";

type AdminYouTubeWebSubManagerProps = {
    events: YouTubeWebSubEventRow[];
};

function formatDateTime(value: string | null): string {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function AdminYouTubeWebSubManager({
    events,
}: AdminYouTubeWebSubManagerProps) {
    return (
        <div className="space-y-8">
            <EventViewer events={events} />
        </div>
    );
}

function EventViewer({ events }: { events: YouTubeWebSubEventRow[] }) {
    const [selected, setSelected] = useState<YouTubeWebSubEventDetail | null>(
        null,
    );
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
        <section className="rounded-md border border-copper/20 bg-surface-elevated p-5">
            <h2 className="font-urbanist-bold text-h3 text-foreground">
                Received events
            </h2>
            <p className="mt-1 font-dmSans text-caption text-muted-foreground">
                Most recent WebSub notifications. Open one to inspect its raw
                payload, parsed IDs, verification result, and suppression
                reason.
            </p>
            {events.length === 0 ? (
                <p className="mt-4 font-dmSans text-body text-muted-foreground">
                    No events received yet.
                </p>
            ) : (
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full border-collapse font-dmSans text-body">
                        <thead>
                            <tr className="border-b border-copper/15 text-left text-caption uppercase text-muted-foreground">
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
                                    <td className="px-2 py-3 text-caption text-muted-foreground">
                                        {formatDateTime(event.receivedAt)}
                                    </td>
                                    <td className="px-2 py-3">
                                        <div className="text-foreground">
                                            {event.comedianName ?? "—"}
                                        </div>
                                        <div className="font-mono text-caption text-muted-foreground">
                                            {event.youtubeChannelId ?? "—"}
                                        </div>
                                    </td>
                                    <td className="px-2 py-3">
                                        <div className="text-foreground">
                                            {event.videoTitle ?? "—"}
                                        </div>
                                        <div className="font-mono text-caption text-muted-foreground">
                                            {event.youtubeVideoId ?? "—"}
                                        </div>
                                    </td>
                                    <td className="px-2 py-3 text-foreground">
                                        {event.eventStatus}
                                    </td>
                                    <td className="px-2 py-3 text-foreground">
                                        {event.verificationStatus ?? "—"}
                                    </td>
                                    <td className="px-2 py-3 text-foreground">
                                        {event.suppressionReason ?? "—"}
                                    </td>
                                    <td className="px-2 py-3">
                                        <button
                                            type="button"
                                            onClick={() => openEvent(event.id)}
                                            disabled={loadingId === event.id}
                                            className="rounded-md border border-copper/35 bg-surface-elevated px-3 py-1 font-dmSans text-caption font-semibold text-foreground hover:bg-copper/10 disabled:opacity-60"
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
        <div className="mt-5 rounded-md border border-copper/25 bg-surface-muted/40 p-4">
            <div className="flex items-center justify-between">
                <h3 className="font-urbanist-bold text-body text-foreground">
                    Event #{event.id} payload
                </h3>
                <button
                    type="button"
                    onClick={onClose}
                    className="font-dmSans text-caption font-semibold text-copper hover:underline"
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
                <p className="font-dmSans text-caption font-semibold uppercase text-muted-foreground">
                    Raw payload (XML)
                </p>
                <pre
                    data-testid="event-payload-xml"
                    className="mt-1 max-h-72 overflow-auto rounded bg-cedar/95 p-3 font-mono text-caption text-foreground"
                >
                    {event.payloadXml}
                </pre>
            </div>
        </div>
    );
}

function DetailItem({ label, value }: { label: string; value: string | null }) {
    return (
        <div>
            <dt className="font-semibold uppercase text-muted-foreground">
                {label}
            </dt>
            <dd className="font-mono text-foreground">{value ?? "—"}</dd>
        </div>
    );
}
