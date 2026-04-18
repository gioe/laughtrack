import "server-only";
import { headers } from "next/headers";
import zipcodes from "zipcodes";

export interface HeroContext {
    zipCode: string | null;
    city: string | null;
    state: string | null;
}

function decodeHeader(value: string | null | undefined): string | null {
    if (!value) return null;
    try {
        return decodeURIComponent(value);
    } catch {
        return value;
    }
}

function lookupCityState(zipCode: string): {
    city: string | null;
    state: string | null;
} {
    try {
        const loc = zipcodes.lookup(zipCode);
        if (!loc) return { city: null, state: null };
        return { city: loc.city ?? null, state: loc.state ?? null };
    } catch {
        return { city: null, state: null };
    }
}

export async function getHeroContext(
    sessionZipCode: string | null,
): Promise<HeroContext> {
    const preferredZip =
        sessionZipCode && /^\d{5}(-\d{4})?$/.test(sessionZipCode)
            ? sessionZipCode.slice(0, 5)
            : null;

    // Vercel geo-IP headers are only populated on Vercel deployments.
    // In dev/non-Vercel environments they'll be absent and we fall back.
    // Only trust US headers — the zipcodes dataset is US-only and non-US
    // 5-digit postal codes (e.g., Germany) would produce misleading zip links.
    let geoZip: string | null = null;
    let geoCity: string | null = null;
    let geoState: string | null = null;
    try {
        const h = await headers();
        const country = decodeHeader(
            h.get("x-vercel-ip-country"),
        )?.toUpperCase();
        if (country === "US") {
            const postal = decodeHeader(h.get("x-vercel-ip-postal-code"));
            if (postal && /^\d{5}$/.test(postal)) geoZip = postal;
            geoCity = decodeHeader(h.get("x-vercel-ip-city"));
            const region = decodeHeader(
                h.get("x-vercel-ip-country-region"),
            )?.toUpperCase();
            if (region && /^[A-Z]{2}$/.test(region)) geoState = region;
        }
    } catch {
        // headers() may throw outside a request context (e.g., during cache warmup)
    }

    const zipCode = preferredZip ?? geoZip;

    if (zipCode) {
        const { city, state } = lookupCityState(zipCode);
        return {
            zipCode,
            city: city ?? geoCity,
            state: state ?? geoState,
        };
    }

    return {
        zipCode: null,
        city: geoCity,
        state: geoState,
    };
}
