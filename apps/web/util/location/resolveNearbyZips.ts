import "server-only";
import zipcodes from "zipcodes";

export const NEARBY_ZIP_CAP = 500;

export function resolveNearbyZips(zipCode: string, radius?: number): string[] {
    const input = zipCode.trim();
    if (!/^\d{5}(-\d{4})?$/.test(input)) return [];
    const origin = input.slice(0, 5);
    if (zipcodes.lookup(origin)?.country !== "US") return [];

    if (!radius || radius < 1 || radius > 500) return [origin];

    try {
        const results = zipcodes.radius(origin, radius) ?? [];
        // The library can omit the origin when its self-distance is NaN.
        // Reserve its place before truncating, including in dense ZIP pools.
        return [
            ...new Set([
                origin,
                ...results.map((zip: string | zipcodes.ZipCode) =>
                    typeof zip === "string" ? zip : zip.zip,
                ),
            ]),
        ].slice(0, NEARBY_ZIP_CAP);
    } catch {
        return [origin];
    }
}
