import { NextRequest, NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";

export async function GET(req: NextRequest) {
    const searchParams = req.nextUrl.searchParams;

    const zip = searchParams.get("zip");
    const from = searchParams.get("from");
    const to = searchParams.get("to");
    const page = searchParams.get("page");
    const size = searchParams.get("size");
    const comedian = searchParams.get("comedian");
    const filters = searchParams.get("filters");
    const distance = searchParams.get("distance");

    if (!zip || !/^\d{5}$/.test(zip)) {
        return NextResponse.json(
            { error: "zip is required and must be a 5-digit US zip code" },
            { status: 400 }
        );
    }

    const params = new URLSearchParams();
    params.set("zip", zip);
    if (from) params.set("fromDate", from);
    if (to) params.set("toDate", to);
    if (page !== null) params.set("page", page);
    if (size !== null) params.set("size", size);
    if (comedian) params.set("comedian", comedian);
    if (filters) params.set("filters", filters);
    if (distance) params.set("distance", distance);

    const timezone = req.headers.get("X-Timezone") ?? "UTC";

    try {
        const result = await getSearchedShows({
            params: params.toString(),
            timezone,
        });

        return NextResponse.json({
            total: result.total,
            data: result.data,
            filters: result.filters,
        });
    } catch (error) {
        console.error("GET /api/v1/shows error:", error);
        return NextResponse.json({ error: "Failed to fetch shows" }, { status: 500 });
    }
}
