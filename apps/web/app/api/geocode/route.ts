import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const GeocodeSchema = z.object({
    lat: z.coerce.number().min(-90).max(90),
    lng: z.coerce.number().min(-180).max(180),
});

export async function GET(request: NextRequest) {
    const rl = await applyPublicReadRateLimit(request, "geocode");
    if (rl instanceof NextResponse) return rl;

    const { searchParams } = request.nextUrl;
    const parsed = GeocodeSchema.safeParse({
        lat: searchParams.get("lat"),
        lng: searchParams.get("lng"),
    });
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const { lat, lng } = parsed.data;
    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            {
                headers: {
                    "Accept-Language": "en",
                    "User-Agent": "LaughTrack/1.0 (https://laughtrack.com)",
                },
            },
        );
        if (!res.ok) {
            return NextResponse.json(
                { error: "Geocoding service unavailable" },
                { status: 502, headers: rateLimitHeaders(rl) },
            );
        }
        const data = await res.json();
        const postcode: string | undefined = data?.address?.postcode;
        const zip = postcode?.split("-")[0];
        if (zip && /^\d{5}$/.test(zip)) {
            return NextResponse.json(
                { zip },
                { headers: rateLimitHeaders(rl) },
            );
        }
        return NextResponse.json(
            { error: "No zip code found for coordinates" },
            { status: 404, headers: rateLimitHeaders(rl) },
        );
    } catch (e) {
        console.error("GET /api/geocode error:", e);
        return NextResponse.json(
            { error: "Failed to reverse geocode coordinates" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
