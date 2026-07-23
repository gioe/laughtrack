"use client";

import React, {
    useCallback,
    useEffect,
    useRef,
    useState,
    type ReactNode,
} from "react";
import {
    queueDiscoveryImpression,
    trackDiscoveryShowDetail,
    type DiscoveryExperimentVariant,
} from "@/lib/discovery/clientEvents";

const QUALIFIED_VISIBILITY_RATIO = 0.5;
const QUALIFIED_DWELL_MS = 1000;

export interface DiscoveryPresentation {
    surface: "near_you";
    policyVersion: string;
    experimentVariant: DiscoveryExperimentVariant;
}

interface DiscoveryAttribution {
    impressionId?: string;
    onShowDetail: () => void;
}

interface DiscoveryImpressionTrackerProps extends DiscoveryPresentation {
    showId: number;
    rank: number;
    className?: string;
    children: (attribution: DiscoveryAttribution) => ReactNode;
}

export default function DiscoveryImpressionTracker({
    showId,
    rank,
    surface,
    policyVersion,
    experimentVariant,
    className,
    children,
}: DiscoveryImpressionTrackerProps) {
    const elementRef = useRef<HTMLDivElement | null>(null);
    const qualifiedRef = useRef(false);
    const dwellTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [impressionId] = useState(() => crypto.randomUUID());
    const [qualifiedImpressionId, setQualifiedImpressionId] = useState<
        string | undefined
    >();

    useEffect(() => {
        const element = elementRef.current;
        if (!element || typeof IntersectionObserver === "undefined") return;
        let active = true;

        const cancelDwell = () => {
            if (dwellTimerRef.current) {
                clearTimeout(dwellTimerRef.current);
                dwellTimerRef.current = null;
            }
        };
        const observer = new IntersectionObserver(
            (entries) => {
                const entry = entries[0];
                const qualifies =
                    entry?.isIntersecting &&
                    entry.intersectionRatio >= QUALIFIED_VISIBILITY_RATIO;
                if (!qualifies) {
                    cancelDwell();
                    return;
                }
                if (qualifiedRef.current || dwellTimerRef.current) return;

                dwellTimerRef.current = setTimeout(() => {
                    dwellTimerRef.current = null;
                    if (qualifiedRef.current) return;
                    qualifiedRef.current = true;
                    void queueDiscoveryImpression({
                        eventId: impressionId,
                        entityType: "show",
                        entityId: showId,
                        surface,
                        policyVersion,
                        experimentVariant,
                        rank,
                        impressedAt: new Date().toISOString(),
                    }).then((persisted) => {
                        if (active && persisted) {
                            setQualifiedImpressionId(impressionId);
                        }
                    });
                }, QUALIFIED_DWELL_MS);
            },
            { threshold: QUALIFIED_VISIBILITY_RATIO },
        );
        observer.observe(element);
        return () => {
            active = false;
            cancelDwell();
            observer.disconnect();
        };
    }, [experimentVariant, impressionId, policyVersion, rank, showId, surface]);

    const onShowDetail = useCallback(() => {
        if (qualifiedImpressionId) {
            trackDiscoveryShowDetail(qualifiedImpressionId);
        }
    }, [qualifiedImpressionId]);

    return (
        <div
            ref={elementRef}
            className={className}
            data-discovery-show-id={showId}
        >
            {children({
                impressionId: qualifiedImpressionId,
                onShowDetail,
            })}
        </div>
    );
}
