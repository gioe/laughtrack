import { SearchParams } from "@/objects/interface";

/**
 * Normalizes Next.js App Router searchParams (which may contain string[] for repeated
 * query parameters) into a plain SearchParams object with string-only values.
 * When a key appears multiple times in the URL, only the first value is used.
 */
export function toSearchParams(
    raw: Record<string, string | string[] | undefined>,
): SearchParams {
    const pick = (key: string): string | undefined => {
        const v = raw[key];
        return Array.isArray(v) ? v[0] : v;
    };
    return {
        fromDate: pick("fromDate"),
        toDate: pick("toDate"),
        filters: pick("filters"),
        zip: pick("zip"),
        distance: pick("distance"),
        comedian: pick("comedian"),
        club: pick("club"),
        sort: pick("sort"),
        page: pick("page"),
        size: pick("size"),
        includeEmpty: pick("includeEmpty"),
    };
}
