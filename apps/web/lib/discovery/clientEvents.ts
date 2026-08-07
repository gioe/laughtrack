"use client";

import type {
    DiscoveryAssignmentReason,
    DiscoveryAvailabilityAtImpression,
} from "./telemetry";
import type { DiscoveryRailKey } from "./railPolicy";

export type DiscoveryExperimentVariant = "control" | "candidate";

interface DiscoveryImpressionEventBase {
    eventId: string;
    entityType: "show";
    entityId: number;
    policyVersion: string;
    rank: number;
    impressedAt: string;
}

export interface NearYouDiscoveryImpressionEvent
    extends DiscoveryImpressionEventBase {
    surface: "near_you";
    experimentVariant: DiscoveryExperimentVariant;
    assignmentEligible: boolean;
    assignmentReason: DiscoveryAssignmentReason;
    explorationSelected: boolean;
    distanceMiles: number | null;
    maxDistanceMiles: number;
    availabilityAtImpression: DiscoveryAvailabilityAtImpression;
    featureVersion: string | null;
}

export interface ServerDirectedDiscoveryImpressionEvent
    extends DiscoveryImpressionEventBase {
    surface: DiscoveryRailKey;
    experimentVariant: "server_directed";
}

export type DiscoveryImpressionEvent =
    | NearYouDiscoveryImpressionEvent
    | ServerDirectedDiscoveryImpressionEvent;

interface DiscoveryEngagementEvent {
    eventId: string;
    impressionEventId: string;
    engagementType: "show_detail";
    engagedAt: string;
}

const BATCH_DELAY_MS = 50;
const MAX_BATCH_SIZE = 50;

interface QueuedImpression {
    event: DiscoveryImpressionEvent;
    resolve: (persisted: boolean) => void;
}

let impressionQueue: QueuedImpression[] = [];
let impressionTimer: ReturnType<typeof setTimeout> | null = null;

async function postBatch(path: string, events: unknown[]): Promise<boolean> {
    if (events.length === 0) return true;
    try {
        const response = await fetch(path, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ events }),
            keepalive: true,
        });
        return response.ok;
    } catch {
        // Discovery measurement must never interfere with product navigation.
        return false;
    }
}

function flushDiscoveryImpressions(): Promise<void> {
    if (impressionTimer) {
        clearTimeout(impressionTimer);
        impressionTimer = null;
    }
    const queued = impressionQueue.splice(0, MAX_BATCH_SIZE);
    const request = postBatch(
        "/api/v1/discovery/impressions",
        queued.map(({ event }) => event),
    ).then((persisted) => {
        queued.forEach(({ resolve }) => resolve(persisted));
    });
    if (impressionQueue.length > 0) {
        impressionTimer = setTimeout(() => {
            void flushDiscoveryImpressions();
        }, BATCH_DELAY_MS);
    }
    return request;
}

export function queueDiscoveryImpression(
    event: DiscoveryImpressionEvent,
): Promise<boolean> {
    return new Promise((resolve) => {
        impressionQueue.push({ event, resolve });
        if (impressionQueue.length >= MAX_BATCH_SIZE) {
            void flushDiscoveryImpressions();
        } else if (!impressionTimer) {
            impressionTimer = setTimeout(() => {
                void flushDiscoveryImpressions();
            }, BATCH_DELAY_MS);
        }
    });
}

export function trackDiscoveryShowDetail(impressionEventId: string): void {
    const event: DiscoveryEngagementEvent = {
        eventId: crypto.randomUUID(),
        impressionEventId,
        engagementType: "show_detail",
        engagedAt: new Date().toISOString(),
    };

    // The tracker exposes this callback only after the impression response
    // confirms persistence, so correlation never depends on request ordering.
    void postBatch("/api/v1/discovery/engagements", [event]);
}

export function resetDiscoveryEventQueuesForTest(): void {
    if (impressionTimer) clearTimeout(impressionTimer);
    impressionQueue.forEach(({ resolve }) => resolve(false));
    impressionTimer = null;
    impressionQueue = [];
}
