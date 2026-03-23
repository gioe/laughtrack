import "server-only";
import zipcodes from "zipcodes";

const EARTH_RADIUS_MILES = 3958.8;

function toRad(deg: number): number {
    return (deg * Math.PI) / 180;
}

/** Haversine distance between two lat/lng points, in miles. */
function haversine(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number,
): number {
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return EARTH_RADIUS_MILES * 2 * Math.asin(Math.sqrt(a));
}

/**
 * Compute distance in miles between two US zip codes.
 * Returns null if either zip is missing, not 5 digits, or not found in the dataset.
 */
export function computeDistanceMiles(
    zip1: string | null | undefined,
    zip2: string | null | undefined,
): number | null {
    if (!zip1 || !zip2) return null;
    if (!/^\d{5}$/.test(zip1) || !/^\d{5}$/.test(zip2)) return null;

    const loc1 = zipcodes.lookup(zip1);
    const loc2 = zipcodes.lookup(zip2);
    if (!loc1 || !loc2) return null;

    return haversine(
        loc1.latitude,
        loc1.longitude,
        loc2.latitude,
        loc2.longitude,
    );
}

/**
 * Format a distance in miles as a human-readable string.
 * Returns null if distanceMiles is null/undefined.
 */
export function formatDistance(
    distanceMiles: number | null | undefined,
): string | null {
    if (distanceMiles == null) return null;
    if (distanceMiles < 1) return "< 1 mile away";
    return `${Math.round(distanceMiles)} miles away`;
}
