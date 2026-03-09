"use client";

import { useCallback } from "react";
import { useReducedMotion } from "framer-motion";

/**
 * Centralizes reduce-motion ternary logic across animated components.
 *
 * Helpers:
 *   mv(normal, reduced?)  — returns `reduced` (default 0) when prefersReducedMotion, else `normal`
 *   mp(props)             — returns `undefined` when prefersReducedMotion, else `props`
 *   mt(transition)        — returns `{ duration: 0 }` when prefersReducedMotion, else `transition`
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

    return { prefersReducedMotion, mv, mp, mt };
}
