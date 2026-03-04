import { NextResponse } from "next/server";
import { getPopularClubs } from "@/lib/data/home/getPopularClubs";

export async function GET() {
    try {
        const clubs = await getPopularClubs();
        return NextResponse.json({ data: clubs });
    } catch (error) {
        console.error("GET /api/v1/clubs error:", error);
        return NextResponse.json({ error: "Failed to fetch clubs" }, { status: 500 });
    }
}
