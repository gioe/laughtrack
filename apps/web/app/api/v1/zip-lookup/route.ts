import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";
import zipcodes from "zipcodes";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const ZipLookupSchema = z.object({
    zip: z.string().regex(/^\d{5}$/, "ZIP must be a 5-digit US postal code"),
});

export async function GET(request: NextRequest) {
    const rl = await applyPublicReadRateLimit(request, "zip-lookup");
    if (rl instanceof NextResponse) return rl;

    const { searchParams } = request.nextUrl;
    const parsed = ZipLookupSchema.safeParse({ zip: searchParams.get("zip") });
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const lookup = zipcodes.lookup(parsed.data.zip);
    if (!lookup || !lookup.city || !lookup.state) {
        return NextResponse.json(
            { error: "Unknown ZIP code" },
            { status: 404, headers: rateLimitHeaders(rl) },
        );
    }

    return NextResponse.json(
        { city: lookup.city, state: lookup.state },
        { headers: rateLimitHeaders(rl) },
    );
}
