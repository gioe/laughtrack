import zipcodes from "zipcodes";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

function resolveZipCodes(zipCode: string, radius?: number): string[] {
    if (!radius || radius < 1 || radius > 500) return [zipCode];
    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];
        return results.map((z: string | zipcodes.ZipCode) =>
            typeof z === "string" ? z : z.zip,
        );
    } catch {
        return [zipCode];
    }
}

export async function getShowsNearZip(
    zipCode: string,
    radius?: number,
): Promise<ShowDTO[]> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const now = new Date();
    const nearbyZips = resolveZipCodes(zipCode, radius);

    return findShowsForHome(
        {
            date: { gte: now },
            club: { visible: true, zipCode: { in: nearbyZips } },
        },
        { date: "asc" },
    );
}
