import "server-only";
import zipcodes from "zipcodes";

export const NEARBY_ZIP_CAP = 500;

export function resolveNearbyZips(zipCode: string, radius?: number): string[] {
    if (!radius || radius < 1 || radius > 500) return [zipCode];

    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];

        return results
            .map((zip: string | zipcodes.ZipCode) =>
                typeof zip === "string" ? zip : zip.zip,
            )
            .slice(0, NEARBY_ZIP_CAP);
    } catch {
        return [zipCode];
    }
}
