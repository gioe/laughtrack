/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";

const { useReducedMotionMock } = vi.hoisted(() => ({
    useReducedMotionMock: vi.fn(),
}));

vi.mock("framer-motion", () => ({
    useReducedMotion: useReducedMotionMock,
}));

import {
    useMotionProps,
    MOTION_SPRINGS,
    MOTION_TAP_SCALE,
} from "./useMotionProps";

afterEach(() => {
    useReducedMotionMock.mockReset();
});

describe("MOTION_SPRINGS", () => {
    // Each spring must encode the iOS LaughTrackTheme.swift token it mirrors:
    // stiffness = (2π / response)², damping = 4π · dampingFraction / response.
    it.each([
        ["tapFeedback", 0.28, 0.82],
        ["contentEntrance", 0.46, 0.86],
        ["emphasis", 0.62, 0.74],
    ] as const)(
        "%s matches iOS spring(response: %f, dampingFraction: %f)",
        (name, response, dampingFraction) => {
            const spring = MOTION_SPRINGS[name];
            expect(spring.type).toBe("spring");
            expect(spring.mass).toBe(1);
            expect(spring.stiffness).toBeCloseTo(
                ((2 * Math.PI) / response) ** 2,
                0,
            );
            expect(spring.damping).toBeCloseTo(
                (4 * Math.PI * dampingFraction) / response,
                0,
            );
        },
    );

    it("MOTION_TAP_SCALE matches the iOS pressed scale", () => {
        expect(MOTION_TAP_SCALE).toBe(0.95);
    });
});

describe("useMotionProps springs", () => {
    it("returns the shared spring variants when motion is allowed", () => {
        useReducedMotionMock.mockReturnValue(false);
        const { result } = renderHook(() => useMotionProps());

        expect(result.current.springs.tapFeedback).toBe(
            MOTION_SPRINGS.tapFeedback,
        );
        expect(result.current.springs.contentEntrance).toBe(
            MOTION_SPRINGS.contentEntrance,
        );
        expect(result.current.springs.emphasis).toBe(MOTION_SPRINGS.emphasis);
    });

    it("collapses every variant to duration 0 under reduced motion", () => {
        useReducedMotionMock.mockReturnValue(true);
        const { result } = renderHook(() => useMotionProps());

        expect(result.current.springs.tapFeedback).toEqual({ duration: 0 });
        expect(result.current.springs.contentEntrance).toEqual({
            duration: 0,
        });
        expect(result.current.springs.emphasis).toEqual({ duration: 0 });
    });

    it("keeps the springs object referentially stable across re-renders", () => {
        useReducedMotionMock.mockReturnValue(false);
        const { result, rerender } = renderHook(() => useMotionProps());
        const first = result.current.springs;
        rerender();
        expect(result.current.springs).toBe(first);
    });
});
