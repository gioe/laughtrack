import type { useMotionProps } from "@/hooks/useMotionProps";

/**
 * Shared stand-in for useMotionProps (hooks/useMotionProps.ts) so component
 * tests don't each carry their own copy of the springs mock block — when the
 * hook's surface grows, tsc flags this one helper (via the ReturnType
 * annotation below) instead of leaving nine inline mocks silently stale
 * (TASK-2779's failure mode, extracted in TASK-2801).
 *
 * Deliberate shape, preserved from the inline mocks it replaces:
 * - springs resolve to { duration: 0 } so animated components settle
 *   instantly under test
 * - mv/mp/mt are identity passthroughs (NOT the real reduce-motion
 *   transforms — those are covered by hooks/useMotionProps.test.ts) so
 *   animation props stay inspectable in assertions
 * - prefersReducedMotion is true so pulse/entrance class toggles take the
 *   deterministic branch
 *
 * vi.mock factories are hoisted above imports, so reference this via an
 * await import inside the factory:
 *
 *     vi.mock("@/hooks", async () => {
 *         const { mockUseMotionProps } = await import("@/test/motionProps");
 *         return { useMotionProps: mockUseMotionProps };
 *     });
 *
 * Files mocking the whole "@/hooks" barrel must still provide any other
 * barrel exports their component tree consumes (e.g. useDialogKeyboard) as
 * sibling keys in the returned object.
 */
// Hoisted to module scope so every mock call hands back the same references,
// matching the real hook's useCallback/useMemo contract — components that
// list these helpers in effect dependency arrays must not re-run effects on
// every render under test.
const identity = <T,>(value: T) => value;
const springs = {
    tapFeedback: { duration: 0 },
    contentEntrance: { duration: 0 },
    emphasis: { duration: 0 },
} as const;

export const mockUseMotionProps = (): ReturnType<typeof useMotionProps> => ({
    springs,
    mv: identity,
    mp: identity,
    mt: identity,
    prefersReducedMotion: true,
});
