/**
 * @vitest-environment happy-dom
 */
import React from "react";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DiscoveryImpressionTracker from "./DiscoveryImpressionTracker";
import { resetDiscoveryEventQueuesForTest } from "@/lib/discovery/clientEvents";

type ObserverCallback = IntersectionObserverCallback;
let observerCallbacks: ObserverCallback[] = [];
let uuidCounter = 0;

class MockIntersectionObserver implements IntersectionObserver {
    readonly root = null;
    readonly rootMargin = "0px";
    readonly thresholds = [0.5];

    constructor(callback: ObserverCallback) {
        observerCallbacks.push(callback);
    }

    disconnect = vi.fn();
    observe = vi.fn();
    takeRecords = vi.fn(() => []);
    unobserve = vi.fn();
}

const presentation = {
    surface: "near_you" as const,
    policyVersion: "near-you-control-v1",
    experimentVariant: "control" as const,
};

function setVisibility(observerIndex: number, ratio: number) {
    act(() => {
        observerCallbacks[observerIndex](
            [
                {
                    isIntersecting: ratio > 0,
                    intersectionRatio: ratio,
                } as IntersectionObserverEntry,
            ],
            {} as IntersectionObserver,
        );
    });
}

function renderTracker(showId = 42, rank = 3) {
    return render(
        <DiscoveryImpressionTracker
            showId={showId}
            rank={rank}
            {...presentation}
        >
            {({ impressionId, onShowDetail }) => (
                <>
                    <span data-testid={`impression-${showId}`}>
                        {impressionId ?? "unqualified"}
                    </span>
                    <button type="button" onClick={onShowDetail}>
                        View show {showId}
                    </button>
                </>
            )}
        </DiscoveryImpressionTracker>,
    );
}

beforeEach(() => {
    vi.useFakeTimers();
    observerCallbacks = [];
    uuidCounter = 0;
    resetDiscoveryEventQueuesForTest();
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(
        () =>
            `00000000-0000-4000-8000-${String(++uuidCounter).padStart(12, "0")}`,
    );
    vi.stubGlobal(
        "fetch",
        vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ accepted: 1, inserted: 1 })),
            ),
        ),
    );
});

afterEach(() => {
    resetDiscoveryEventQueuesForTest();
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe("DiscoveryImpressionTracker", () => {
    it("records only after the item is at least half visible for one second", async () => {
        renderTracker();

        setVisibility(0, 0.49);
        await act(() => vi.advanceTimersByTimeAsync(2000));
        expect(fetch).not.toHaveBeenCalled();

        setVisibility(0, 0.5);
        await act(() => vi.advanceTimersByTimeAsync(999));
        expect(fetch).not.toHaveBeenCalled();

        await act(() => vi.advanceTimersByTimeAsync(51));
        expect(fetch).toHaveBeenCalledTimes(1);
        const [, request] = vi.mocked(fetch).mock.calls[0];
        const body = JSON.parse(String(request?.body));
        expect(body.events).toEqual([
            expect.objectContaining({
                entityType: "show",
                entityId: 42,
                surface: "near_you",
                policyVersion: "near-you-control-v1",
                experimentVariant: "control",
                rank: 3,
            }),
        ]);
        expect(body.events[0]).not.toHaveProperty("profileId");
        expect(body.events[0]).not.toHaveProperty("anonymousVisitorId");
    });

    it("cancels partial dwell, then qualifies when horizontal scrolling presents the item", async () => {
        renderTracker();

        setVisibility(0, 0.75);
        await act(() => vi.advanceTimersByTimeAsync(500));
        setVisibility(0, 0);
        await act(() => vi.advanceTimersByTimeAsync(1000));
        expect(fetch).not.toHaveBeenCalled();

        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));
        expect(fetch).toHaveBeenCalledTimes(1);
    });

    it("records once across rerenders and repeated observer callbacks", async () => {
        const { rerender } = renderTracker();
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));

        rerender(
            <DiscoveryImpressionTracker showId={42} rank={3} {...presentation}>
                {({ impressionId }) => <span>{impressionId}</span>}
            </DiscoveryImpressionTracker>,
        );
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(2000));

        expect(fetch).toHaveBeenCalledTimes(1);
    });

    it("batches multiple qualified cards into one request", async () => {
        renderTracker(42, 1);
        renderTracker(43, 2);

        setVisibility(0, 1);
        setVisibility(1, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));

        expect(fetch).toHaveBeenCalledTimes(1);
        const body = JSON.parse(
            String(vi.mocked(fetch).mock.calls[0][1]?.body),
        );
        expect(
            body.events.map((event: { entityId: number }) => event.entityId),
        ).toEqual([42, 43]);
    });

    it("correlates detail engagement with the qualified impression without blocking the click", async () => {
        renderTracker();
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));

        const impressionId = screen.getByTestId("impression-42").textContent;
        fireEvent.click(screen.getByRole("button", { name: "View show 42" }));
        await act(() => vi.runAllTimersAsync());

        expect(fetch).toHaveBeenCalledTimes(2);
        const engagement = JSON.parse(
            String(vi.mocked(fetch).mock.calls[1][1]?.body),
        );
        expect(engagement.events[0]).toEqual(
            expect.objectContaining({
                impressionEventId: impressionId,
                engagementType: "show_detail",
            }),
        );
    });

    it("starts engagement delivery even while impression persistence is in flight", async () => {
        let resolveImpression: (() => void) | undefined;
        vi.mocked(fetch).mockImplementationOnce(
            () =>
                new Promise<Response>((resolve) => {
                    resolveImpression = () => resolve(new Response("{}"));
                }),
        );
        renderTracker();
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));

        fireEvent.click(screen.getByRole("button", { name: "View show 42" }));

        expect(fetch).toHaveBeenCalledTimes(2);
        expect(vi.mocked(fetch).mock.calls[1][0]).toBe(
            "/api/v1/discovery/engagements",
        );
        resolveImpression?.();
        await act(async () => {});
    });

    it("starts impression delivery synchronously before direct ticket intent", async () => {
        render(
            <DiscoveryImpressionTracker showId={42} rank={3} {...presentation}>
                {({ onTicketIntent }) => (
                    <button type="button" onClick={onTicketIntent}>
                        Buy tickets
                    </button>
                )}
            </DiscoveryImpressionTracker>,
        );
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1000));

        fireEvent.click(screen.getByRole("button", { name: "Buy tickets" }));

        expect(fetch).toHaveBeenCalledTimes(1);
        expect(vi.mocked(fetch).mock.calls[0][0]).toBe(
            "/api/v1/discovery/impressions",
        );
    });

    it("creates a fresh presentation when rank or experiment metadata changes", async () => {
        const { rerender } = render(
            <DiscoveryImpressionTracker
                key="42:1:control"
                showId={42}
                rank={1}
                {...presentation}
            >
                {({ impressionId }) => <span>{impressionId}</span>}
            </DiscoveryImpressionTracker>,
        );
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));
        const firstBody = JSON.parse(
            String(vi.mocked(fetch).mock.calls[0][1]?.body),
        );

        rerender(
            <DiscoveryImpressionTracker
                key="42:2:candidate"
                showId={42}
                rank={2}
                {...presentation}
                experimentVariant="candidate"
            >
                {({ impressionId }) => <span>{impressionId}</span>}
            </DiscoveryImpressionTracker>,
        );
        setVisibility(1, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));
        const secondBody = JSON.parse(
            String(vi.mocked(fetch).mock.calls[1][1]?.body),
        );

        expect(secondBody.events[0]).toEqual(
            expect.objectContaining({
                rank: 2,
                experimentVariant: "candidate",
            }),
        );
        expect(secondBody.events[0].eventId).not.toBe(
            firstBody.events[0].eventId,
        );
    });

    it("swallows measurement failures so user actions remain safe", async () => {
        vi.mocked(fetch).mockRejectedValue(new Error("offline"));
        renderTracker();
        setVisibility(0, 1);
        await act(() => vi.advanceTimersByTimeAsync(1050));

        expect(() =>
            fireEvent.click(
                screen.getByRole("button", { name: "View show 42" }),
            ),
        ).not.toThrow();
        await act(() => vi.runAllTimersAsync());
    });
});
