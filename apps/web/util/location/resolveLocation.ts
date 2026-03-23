import "server-only";
import zipcodes from "zipcodes";

export type LocationResolution =
    | { found: true; startingZips: string[] }
    | { found: false };

/**
 * Resolves a user-entered location string (zip code or city name) to one or
 * more representative zip codes.
 *
 * - "10001"           → zip code, returned as-is
 * - "Chicago, IL"     → looks up via zipcodes.lookupByName
 * - "Chicago"         → searches all zip codes by city name (cross-state)
 * - "Portland"        → returns one representative zip per state (OR, ME, …)
 *
 * Returns `{ found: false }` when the input cannot be resolved.
 */
export function resolveLocationInput(input: string): LocationResolution {
    if (!input) return { found: false };

    const trimmed = input.trim();
    if (!trimmed) return { found: false };

    // 5-digit zip code — pass through directly
    if (/^\d{5}$/.test(trimmed)) {
        return { found: true, startingZips: [trimmed] };
    }

    // Parse "City, ST" or plain "City"
    let cityName: string;
    let stateName: string | undefined;
    const commaMatch = trimmed.match(/^(.+),\s*([A-Za-z]{2})$/);
    if (commaMatch) {
        cityName = commaMatch[1].trim();
        stateName = commaMatch[2].toUpperCase();
    } else {
        cityName = trimmed;
    }

    let results: zipcodes.ZipCode[];

    if (stateName) {
        try {
            results = zipcodes.lookupByName(cityName, stateName);
        } catch {
            results = [];
        }
    } else {
        // Search all zip codes for the city name (case-insensitive)
        const lowerCity = cityName.toLowerCase();
        results = Object.values(zipcodes.codes).filter(
            (c) => c.city.toLowerCase() === lowerCity,
        );
    }

    if (!results || results.length === 0) {
        return { found: false };
    }

    // Pick one representative zip per state so that ambiguous city names
    // (e.g. "Portland" in OR, ME, TN, …) each get a radius search origin.
    const byState = new Map<string, string>();
    results.forEach((r) => {
        if (!byState.has(r.state)) byState.set(r.state, r.zip);
    });

    return { found: true, startingZips: Array.from(byState.values()) };
}
