"use client";

import { useCallback, useMemo } from "react";
import { useReducedMotion } from "framer-motion";
import type { Transition } from "framer-motion";

/**
 * Shared motion curves mirroring the iOS semantic motion tokens in
 * ios/Sources/LaughTrackBridge/LaughTrackTheme.swift, so animation feel
 * matches across both clients. Stiffness/damping are derived from SwiftUI's
 * spring(response:dampingFraction:) model with mass 1:
 *   stiffness = (2π / response)²
 *   damping   = 4π · dampingFraction / response
 *
 * iOS pairs tapFeedback with a 0.95 pressed scale — use MOTION_TAP_SCALE
 * for whileTap props.
 */
export const MOTION_SPRINGS = {
    // .spring(response: 0.28, dampingFraction: 0.82) — taps, hover lifts
    tapFeedback: { type: "spring", stiffness: 503.6, damping: 36.8, mass: 1 },
    // .spring(response: 0.46, dampingFraction: 0.86) — content entrances
    contentEntrance: {
        type: "spring",
        stiffness: 186.6,
        damping: 23.5,
        mass: 1,
    },
    // .spring(response: 0.62, dampingFraction: 0.74) — hero/emphasis moments
    emphasis: { type: "spring", stiffness: 102.7, damping: 15, mass: 1 },
} as const satisfies Record<string, Transition>;

export const MOTION_TAP_SCALE = 0.95;

/**
 * Centralizes reduce-motion ternary logic across animated components.
 *
 * Helpers:
 *   mv(normal, reduced?)  — returns `reduced` (default 0) when prefersReducedMotion, else `normal`
 *   mp(props)             — returns `undefined` when prefersReducedMotion, else `props`
 *   mt(transition)        — returns `{ duration: 0 }` when prefersReducedMotion, else `transition`
 *   springs               — reduce-motion-aware MOTION_SPRINGS variants; spread extra
 *                           fields onto them (e.g. { ...springs.contentEntrance, delay: mv(0.1) })
 *   prefersReducedMotion  — raw boolean for edge cases (class strings, scroll behavior, etc.)
 */
export function useMotionProps() {
    const prefersReducedMotion = useReducedMotion() ?? false;

    // Wrapped in useCallback so callers can safely include these helpers in
    // useEffect/useCallback/useMemo dependency arrays without causing infinite loops.
    const mv = useCallback(
        (normal: number, reduced = 0): number =>
            prefersReducedMotion ? reduced : normal,
        [prefersReducedMotion],
    );

    const mp = useCallback(
        <T>(props: T): T | undefined =>
            prefersReducedMotion ? undefined : props,
        [prefersReducedMotion],
    );

    const mt = useCallback(
        <T extends object>(transition: T): T | { duration: 0 } =>
            prefersReducedMotion ? { duration: 0 as const } : transition,
        [prefersReducedMotion],
    );

    const springs = useMemo(
        () =>
            ({
                tapFeedback: prefersReducedMotion
                    ? { duration: 0 }
                    : MOTION_SPRINGS.tapFeedback,
                contentEntrance: prefersReducedMotion
                    ? { duration: 0 }
                    : MOTION_SPRINGS.contentEntrance,
                emphasis: prefersReducedMotion
                    ? { duration: 0 }
                    : MOTION_SPRINGS.emphasis,
            }) satisfies Record<keyof typeof MOTION_SPRINGS, Transition>,
        [prefersReducedMotion],
    );

    return { prefersReducedMotion, mv, mp, mt, springs };
}
