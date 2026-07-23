"use client";

export type DiscoveryExperimentVariant = "control" | "candidate";

export interface DiscoveryImpressionEvent {
    eventId: string;
    entityType: "show";
    entityId: number;
    surface: "near_you";
    policyVersion: string;
    experimentVariant: DiscoveryExperimentVariant;
    rank: number;
    impressedAt: string;
}

interface DiscoveryEngagementEvent {
    eventId: string;
    impressionEventId: string;
    engagementType: "show_detail";
    engagedAt: string;
}

const BATCH_DELAY_MS = 50;
const MAX_BATCH_SIZE = 50;

let impressionQueue: DiscoveryImpressionEvent[] = [];
let impressionTimer: ReturnType<typeof setTimeout> | null = null;

async function postBatch(path: string, events: unknown[]): Promise<void> {
    if (events.length === 0) return;
    try {
        await fetch(path, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ events }),
            keepalive: true,
        });
    } catch {
        // Discovery measurement must never interfere with product navigation.
    }
}

export function flushDiscoveryImpressions(): Promise<void> {
    if (impressionTimer) {
        clearTimeout(impressionTimer);
        impressionTimer = null;
    }
    const events = impressionQueue.splice(0, MAX_BATCH_SIZE);
    const request = postBatch("/api/v1/discovery/impressions", events);
    if (impressionQueue.length > 0) {
        impressionTimer = setTimeout(() => {
            void flushDiscoveryImpressions();
        }, BATCH_DELAY_MS);
    }
    return request;
}

export function queueDiscoveryImpression(
    event: DiscoveryImpressionEvent,
): void {
    impressionQueue.push(event);
    if (impressionQueue.length >= MAX_BATCH_SIZE) {
        void flushDiscoveryImpressions();
    } else if (!impressionTimer) {
        impressionTimer = setTimeout(() => {
            void flushDiscoveryImpressions();
        }, BATCH_DELAY_MS);
    }
}

export function trackDiscoveryShowDetail(impressionEventId: string): void {
    const event: DiscoveryEngagementEvent = {
        eventId: crypto.randomUUID(),
        impressionEventId,
        engagementType: "show_detail",
        engagedAt: new Date().toISOString(),
    };

    // Start both keepalive requests synchronously in the click handler so
    // navigation cannot tear down a deferred promise/timer callback. The
    // engagement endpoint briefly retries while the impression is persisted.
    void flushDiscoveryImpressions();
    void postBatch("/api/v1/discovery/engagements", [event]);
}

export function resetDiscoveryEventQueuesForTest(): void {
    if (impressionTimer) clearTimeout(impressionTimer);
    impressionTimer = null;
    impressionQueue = [];
}
