"use server";

import { resolveLocationInput } from "@/util/location/resolveLocation";

export type LocationActionResult = { ok: true } | { ok: false; error: string };

/**
 * Validates a user-entered location string (city name or zip code) server-side.
 * Used by the location input component to show inline errors without a full
 * page reload.
 */
export async function resolveLocationAction(
    input: string,
): Promise<LocationActionResult> {
    const trimmed = input.trim();
    if (!trimmed) return { ok: true };

    const resolution = resolveLocationInput(trimmed);
    if (!resolution.found) {
        return { ok: false, error: "City not found — try a zip code" };
    }
    return { ok: true };
}
