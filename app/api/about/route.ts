import { getStats } from "@/lib/data/stats/getStats";
import { StatsDTO } from "@/app/api/about/interface";
import { NextResponse } from "next/server";

export async function GET() {
    return getStats()
        .then((stats: StatsDTO) => NextResponse.json({ stats }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
