"use client";

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

    function mv(normal: number, reduced = 0): number {
        return prefersReducedMotion ? reduced : normal;
    }

    function mp<T>(props: T): T | undefined {
        return prefersReducedMotion ? undefined : props;
    }

    function mt<T extends object>(transition: T): T | { duration: 0 } {
        return prefersReducedMotion ? { duration: 0 as const } : transition;
    }

    return { prefersReducedMotion, mv, mp, mt };
}
